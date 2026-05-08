# -*- coding: utf-8 -*-
"""
第一步：生成静态HTML（超紧凑+调整色块间距版）
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import os
import webbrowser
import warnings

warnings.filterwarnings('ignore')

# ========== 核心配置 ==========
DATA_FILE = r"avdata.csv"
DESIRED_ORDER = ['Work', 'Traffic', 'Leisure', 'Healthcare', 'Education', 'Home']
COLOR_MAP = {
    'Work': '#F39B7F',
    'Traffic': '#8491B4',
    'Leisure': '#E64B35',
    'Healthcare': '#3C5488',
    'Education': '#00A087',
    'Home': '#4DBBD5'
}

# ========== 超紧凑像素定位（核心优化：减小色块间距） ==========
TOTAL_WIDTH = 1800
TOTAL_HEIGHT = 1000  # 保持画布高度不变
SUBPLOT_WIDTH = (TOTAL_WIDTH - 100) / 4
SUBPLOT_HEIGHT = TOTAL_HEIGHT - 80

# 核心修改：降低上下限高度，减小纵向间距
# 原配置：[120, 220, 320, 420, 520, 620] 间距100像素
# 新配置1（间距60像素）：上下限分别降低，间距减小
NODE_Y_PIXELS = [160, 220, 280, 340, 400, 460]  # 相邻节点间距60像素
# 如果你想要更小的间距，可以使用这个配置（间距40像素）：
# NODE_Y_PIXELS = [180, 220, 260, 300, 340, 380]

NODE_X_LEFT = SUBPLOT_WIDTH * 0.05
NODE_X_RIGHT = SUBPLOT_WIDTH * 0.95

# ========== 工具函数 ==========
def classify_time(t):
    if 7 <= t.hour < 9:
        return 'Peak hour (Morning)'
    elif 9 <= t.hour < 17:
        return 'Day'
    elif 17 <= t.hour < 20:
        return 'Peak hour (Evening)'
    else:
        return 'Night'

def hex_to_rgba(hex_color, alpha=0.4):
    h = hex_color.lstrip('#')
    return f'rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})'

def px_to_rel(px, total_px):
    return px / total_px

# ========== 加载数据 ==========
print("🔍 加载全部数据...")
df = pd.read_csv(DATA_FILE)
df['呼单时间'] = pd.to_datetime(df['呼单时间'], errors='coerce')
df = df.dropna(subset=['呼单时间'])
df['时间段'] = df['呼单时间'].apply(lambda x: classify_time(x))

type_mapping = {
    '居住区': 'Home', '商业区': 'Leisure', '交通枢纽': 'Traffic',
    '企业办公/写字楼': 'Work', '工业/产业区': 'Work', '政务/基础服务与社区服务': 'Healthcare',
    '教育科研机构': 'Education', '其他': 'other', '医疗卫生设施': 'Healthcare',
    '文旅文化/展览区': 'Leisure', '通勤支持设施': 'Healthcare', '金融设施': 'Work',
    '体育设施': 'Healthcare'
}
df['source_code'] = df['起点类型'].map(type_mapping).fillna('other')
df['target_code'] = df['终点类型'].map(type_mapping).fillna('other')
df = df[(df['source_code'] != 'other') & (df['target_code'] != 'other')]
print(f"✅ 有效订单量：{len(df)} 条")

# ========== 构建固定节点 ==========
source_nodes = ['S_' + c for c in DESIRED_ORDER]
target_nodes = ['T_' + c for c in DESIRED_ORDER]
all_nodes = source_nodes + target_nodes
node_indices = {node: i for i, node in enumerate(all_nodes)}
labels = [n[2:] for n in all_nodes]
colors = [COLOR_MAP[lab] for lab in labels]

node_y = [px_to_rel(y, SUBPLOT_HEIGHT) for y in NODE_Y_PIXELS] * 2
node_x = [px_to_rel(NODE_X_LEFT, SUBPLOT_WIDTH)] * 6 + [px_to_rel(NODE_X_RIGHT, SUBPLOT_WIDTH)] * 6

# ========== 绘制桑基图（调整色块间距） ==========
print("🎨 生成桑基图HTML...")
fig = make_subplots(
    rows=1, cols=4,
    subplot_titles=['Peak hour (Morning)', 'Day', 'Peak hour (Evening)', 'Night'],
    specs=[[{'type': 'domain'}] * 4],
    horizontal_spacing=0.01,
    vertical_spacing=0,
)

self_loop = (list(range(12)), list(range(12)), [0.001] * 12, ['rgba(0,0,0,0)'] * 12)

time_slots = ['Peak hour (Morning)', 'Day', 'Peak hour (Evening)', 'Night']
for col, slot in enumerate(time_slots, 1):
    sub_df = df[df['时间段'] == slot].copy()

    sub_df['source_node'] = 'S_' + sub_df['source_code']
    sub_df['target_node'] = 'T_' + sub_df['target_code']
    flow_counts = sub_df.groupby(['source_node', 'target_node']).size().reset_index(name='count')

    all_pairs = pd.MultiIndex.from_product([source_nodes, target_nodes],
                                           names=['source_node', 'target_node'])
    flow_counts = flow_counts.set_index(['source_node', 'target_node']).reindex(all_pairs, fill_value=0).reset_index()

    sources = [node_indices[s] for s in flow_counts['source_node']] + self_loop[0]
    targets = [node_indices[t] for t in flow_counts['target_node']] + self_loop[1]
    values = flow_counts['count'].tolist() + self_loop[2]
    link_colors = [hex_to_rgba(COLOR_MAP.get(src.replace('S_', ''), '#BAB0AC'))
                   for src in flow_counts['source_node']] + self_loop[3]

    fig.add_trace(go.Sankey(
        node=dict(
            pad=10,
            thickness=15,
            line=dict(color='black', width=0.8),
            label=labels,
            color=colors,
            x=node_x,
            y=node_y,
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors,
            line=dict(width=0)
        ),
        arrangement="fixed",
        orientation="h",
    ), row=1, col=col)

# ========== 样式配置 ==========
fig.update_layout(
    width=TOTAL_WIDTH,
    height=TOTAL_HEIGHT,
    margin=dict(l=40, r=40, t=40, b=40, pad=0),
    font=dict(family='Arial', size=26),
    paper_bgcolor='white',
    showlegend=False,
    dragmode=False,
    hovermode=False,
    transition={'duration': 0},
    autosize=False,
)

# 强制轴范围统一
for i in range(1, 5):
    fig.update_xaxes(
        row=1, col=i,
        range=[0, 1],
        fixedrange=True,
        showgrid=False,
        zeroline=False,
        showticklabels=False,
    )
    fig.update_yaxes(
        row=1, col=i,
        range=[0, 1],
        fixedrange=True,
        showgrid=False,
        zeroline=False,
        showticklabels=False,
    )

# ========== 生成HTML ==========
html_path = "av_sankey_final.html"
fig.write_html(
    html_path,
    include_plotlyjs='cdn',
    config={
        'staticPlot': True,
        'displayModeBar': True,
        'responsive': False,
    }
)

print(f"✅ HTML文件已生成：{os.path.abspath(html_path)}")
print("🔍 自动打开HTML文件，请等待...")
webbrowser.open_new(os.path.abspath(html_path))
print("🎉 完成！色块纵向间距已减小，整体布局更紧凑")