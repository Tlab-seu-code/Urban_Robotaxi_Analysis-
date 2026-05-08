# -*- coding: utf-8 -*-
import pandas as pd
import lightgbm as lgb
import shap
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Arial'  # 全局强制 Arial
plt.rcParams['axes.unicode_minus'] = False  # 负号正常显示
from matplotlib.patches import Patch
from sklearn.preprocessing import LabelEncoder
import numpy as np
from datetime import datetime

# ---------- 1. 全局配色 / 分组 ---------- #
PALETTE = {
    'Order Attributes':           '#6B6B6B',   # 冷灰
    'Environmental Factors':      '#5A7D9A',   # 雾蓝
    'Real-time Operational Metrics': '#9A7D5A'  # 燕麦棕
}

# 特征 → 组（列名已统一为下划线风格）
GROUP_MAP = {
    'Order Attributes': [
        'resource', 'trip_distance', 'weekday', 'time_period', 'dest_type',
        'starting_district', 'destination_district', 'across_the_river'
    ],
    'Environmental Factors': [
        'temperature', 'weather', 'visibility'
    ],
    'Real-time Operational Metrics': [
        'avg_pickup_wait_30min', 'success_rate_30min'
    ]
}
FEAT2GROUP = {f: g for g, cols in GROUP_MAP.items() for f in cols}

# ---------- 2. 读数据 + 基础清洗 ---------- #
df = pd.read_csv('wuhan1.csv', nrows=80_000)

rename_map = {
    '路径距离': 'trip_distance',
    '星期几': 'weekday',
    '时间段': 'time_period',
    '终点类型': 'dest_type',
    '起点所属区': 'starting_district',
    '终点所属区': 'destination_district',
    '温度': 'temperature',
    '状态': 'weather',
    '订单前半小时平均等待': 'avg_pickup_wait_30min',
    '订单状态': 'order_status'
}
df = df.rename(columns=rename_map)

# 构造 y：order_status 转为 0/1
df['order_status'] = df['order_status'].map(
    lambda x: 1 if str(x).lower() in ('完成', 'success', '1') else 0
)
y = df['order_status'].values

# ---------- 3. 特征列表 + LabelEncoder ---------- #
FEATURES = [
    'trip_distance', 'weekday', 'time_period', 'dest_type',
    'starting_district', 'destination_district',
    'temperature', 'weather',
    'avg_pickup_wait_30min'
]

# 缺失 visibility 就补 0（示例）
if 'visibility' not in df.columns:
    df['visibility'] = 0

X = df[FEATURES].copy()

# 把所有 object 列做 LabelEncoder
for col in X.select_dtypes(include='object').columns:
    X[col] = LabelEncoder().fit_transform(X[col].astype(str))

# ---------- 4. 训练 LightGBM ---------- #
dtrain = lgb.Dataset(X, label=y)
model = lgb.train(
    params={'objective': 'binary', 'metric': 'binary_logloss',
            'verbosity': -1, 'seed': 42},
    train_set=dtrain,
    num_boost_round=300
)

# ---------- 5. SHAP ---------- #
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)   # 二分类返回 (n_sample, n_feat)

# ---------- 6. 画图封装 ---------- #
ts = datetime.now().strftime('%m%d%H%M')

def plot_beeswarm():
    """ beeswarm 全特征，按组染色 + 按重要性降序排列 """
    # 1. 计算平均 |SHAP|
    imp = np.abs(shap_values).mean(axis=0)
    # 2. 排序索引（降序）
    order = np.argsort(imp)[::-1]
    # 3. 重排特征名、SHAP 值、数据矩阵
    shap_obj = shap.Explanation(
        values=shap_values[:, order],
        data=X.values[:, order],
        feature_names=[X.columns[i] for i in order]
    )
    plt.figure(figsize=(8, 6))
    shap.plots.beeswarm(shap_obj, show=False, color_bar=True)
    ax = plt.gca()

    # ======================
    # 去掉所有灰色虚线参考线
    # ======================
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)
    ax.grid(False)  # 关闭网格线（你说的灰色虚线）
    ax.yaxis.grid(False)
    ax.xaxis.grid(False)

    # 4. 给 y 轴 tick 染色
    for label in ax.get_yticklabels():
        feat = label.get_text()
        label.set_color(PALETTE[FEAT2GROUP.get(feat, 'Order Attributes')])
    
    plt.title('SHAP Summary – All Features (Updated Groups)', fontsize=14)
    plt.tight_layout()
    fname = f'shap_all_updated_groups_{ts}.pdf'
    plt.savefig(fname, dpi=3000, bbox_inches='tight')
    plt.close()
    print('saved:', fname)

def plot_importance_bar():
    """ 平均 |SHAP| 柱状图 """
    imp_df = (
        pd.DataFrame({
            'feature': X.columns,
            'importance': np.abs(shap_values).mean(axis=0),
            'group': [FEAT2GROUP[f] for f in X.columns]
        })
        .sort_values('importance')
    )
    plt.figure(figsize=(7, 8))
    bars = plt.barh(
        imp_df['feature'],
        imp_df['importance'],
        color=[PALETTE[g] for g in imp_df['group']]
    )
    # 图例
    handles = [Patch(facecolor=PALETTE[g], label=g) for g in PALETTE]
    plt.legend(handles=handles, loc='lower right')
    plt.xlabel('Mean |SHAP| value')
    plt.title('Feature Importance Ranking (Updated)', fontsize=14)
    plt.tight_layout()
    fname = f'shap_importance_ranking_updated_{ts}.svg'
    plt.savefig(fname, dpi=3000, bbox_inches='tight')
    plt.close()
    print('saved:', fname)

# ---------- 7. 执行 ---------- #
if __name__ == '__main__':
    plot_beeswarm()
    plot_importance_bar()