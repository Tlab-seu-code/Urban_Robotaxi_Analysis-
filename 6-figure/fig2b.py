# -*- coding: utf-8 -*-
"""
AV–maxHV散点图（带因果滞后h）
图例布局调整：仅保留Frequency和拟合曲线，单列排版，字号放大2倍
其他修改：1. 按日期顺序匹配 2. 修复NaT日期异常 3. 空值校验 4. 点大小缩放 5. 点稀疏化 6. 统一红色最大点 7. 修复频率条边框
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from scipy.optimize import curve_fit
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Patch
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from matplotlib.lines import Line2D

# --------------------------------------------------
# 0. 参数 & 路径（更新为新数据路径）
# --------------------------------------------------
AV_FILE = r"F:\Research_Group\City_Grading\0927data\v4-av.csv"  # 新AV数据路径
HV_FILE = r"F:\Research_Group\City_Grading\0927data\v10-hdv.csv"  # 新HV数据路径
CCI_FILE = r"F:\Research_Group\City_Grading\1108data\cci_grid_linear_grid.xlsx"
HOUR_BIN = 1  # 1 h
LOG_EPS = 1e-3  # 防 log(0)
H_SHIFT = 0  # 因果滞后（小时）

# 点稀疏化参数
SCALE_FACTOR = 0.45  # 点大小缩放比例（原大小的60%）
AV0_RETENTION = 0.001  # AV=0点的保留比例（0.1%）
# 定义分段保留规则：(AV上限, HV上限, 保留比例)
RETENTION_RULES = [
    (10, 50, 0.01),  # (10,50)以内保留1%
    (15, 100, 0.05),  # (10,50)以外且(15,100)以内保留5%
    (20, 150, 0.05),  # (15,100)以外且(20,150)以内保留5%
    (25, 200, 0.15),  # (20,150)以外且(25,200)以内保留15%
    (30, 250, 0.25),  # (25,200)以外且(30,250)以内保留25%
    (35, 300, 0.4),  # (30,250)以外且(35,300)以内保留40%
    (40, 350, 0.6)  # (35,300)以外且(40,350)以内保留60%
]
FINAL_RETENTION = 1.0  # 其余区域全保留

# 指定经纬度边界和步长
LON_MIN, LON_MAX = 113.942617, 114.629031
LAT_MIN, LAT_MAX = 30.255898, 30.742468
dx = 0.0103997242944  # 经度方向1km步长
dy = 0.0089831117499  # 纬度方向1km步长

# 字号放大系数
FONT_SCALE = 1.25  # 所有文字数字字号放大1.5倍
# 图例放大系数
LEGEND_SCALE = 1.25  # 图例整体大小放大1.5倍

# --------------------------------------------------
# 1. 读数据 & 清洗 & 网格（适配新数据格式，增加空值校验）
# --------------------------------------------------
# 读取CCI数据
cci_df = pd.read_excel(CCI_FILE)
# 确保grid_x和grid_y为整数
cci_df['grid_x'] = cci_df['grid_x'].astype(int)
cci_df['grid_y'] = cci_df['grid_y'].astype(int)
# 创建(grid_x, grid_y)到cci的映射
cci_map = {(row['grid_x'], row['grid_y']): row['cci_max']
           for _, row in cci_df.iterrows()}
# 获取所有网格坐标
all_grids = set(cci_map.keys())

# AV数据读取与初步清洗（适配v4-av.csv格式）
av = pd.read_csv(AV_FILE, parse_dates=['呼单时间'])
av = av.drop_duplicates(subset=['订单号'], keep='first')  # 订单去重
# 空间裁剪（使用指定的经纬度边界，字段：起点经度、起点纬度）
av = av[(av['起点经度'] >= LON_MIN) & (av['起点经度'] <= LON_MAX) &
        (av['起点纬度'] >= LAT_MIN) & (av['起点纬度'] <= LAT_MAX)]
# 校验AV数据是否为空
if av.empty:
    raise SystemExit(f">>> AV数据空间裁剪后为空！请检查：1. 经纬度边界是否正确 2. AV数据是否包含有效经纬度")

# HV数据读取与初步清洗（适配v10-hdv.csv格式）
hv = pd.read_csv(HV_FILE, encoding='utf-8', header=0)
# 新HV数据字段映射：确认核心字段存在
required_hv_fields = ['vehicle_id', 'order_id', 'start_time', 'start_lon', 'start_lat', 'date']
missing_fields = [f for f in required_hv_fields if f not in hv.columns]
if missing_fields:
    raise SystemExit(f">>> HV数据缺少必要字段：{missing_fields}，请检查v10-hdv.csv格式")

# 时间解析（新HV数据start_time为直接的日期时间格式）
hv['start_time'] = pd.to_datetime(hv['start_time'], errors='coerce')
hv = hv.dropna(subset=['start_time'])  # 移除时间解析失败的行
# 空间裁剪（新HV数据字段：start_lon、start_lat，对应订单起点）
hv = hv[(hv['start_lon'] >= LON_MIN) & (hv['start_lon'] <= LON_MAX) &
        (hv['start_lat'] >= LAT_MIN) & (hv['start_lat'] <= LAT_MAX)]
# 校验HV数据是否为空
if hv.empty:
    raise SystemExit(f">>> HV数据清洗后为空！请检查：1. 经纬度边界 2. start_time字段格式是否为有效日期时间")


# 网格编号函数（基于经纬度步长）
def grid_id(lon, lat):
    gx = np.floor((lon - LON_MIN) / dx).astype(int)
    gy = np.floor((lat - LAT_MIN) / dy).astype(int)
    # 过滤超出范围的网格
    gx = np.clip(gx, 0, int(np.ceil((LON_MAX - LON_MIN) / dx)))
    gy = np.clip(gy, 0, int(np.ceil((LAT_MAX - LAT_MIN) / dy)))
    return gx, gy


# 计算网格ID（适配新数据字段）
av['gx'], av['gy'] = grid_id(av['起点经度'], av['起点纬度'])  # AV：起点经度、起点纬度
hv['gx'], hv['gy'] = grid_id(hv['start_lon'], hv['start_lat'])  # HV：start_lon、start_lat

# --------------------------------------------------
# 2. 因果平移与日历对齐（按日期顺序匹配）
# --------------------------------------------------
hv['start_time'] += pd.Timedelta(hours=H_SHIFT)

# 提取并排序唯一日期
av_unique_dates = sorted(av['呼单时间'].dt.date.unique())
hv_unique_dates = sorted(hv['start_time'].dt.date.unique())

# 确定共同日期数量（取两者中较小的天数）
common_days_count = min(len(av_unique_dates), len(hv_unique_dates))
print(f"=== 数据日期统计 ===")
print(f"AV数据：{len(av)}条记录，覆盖{len(av_unique_dates)}天")
print(f"HV数据：{len(hv)}条记录，覆盖{len(hv_unique_dates)}天")
print(f"按顺序匹配的共同日期：{common_days_count}天")

# 校验共同日期是否为空
if common_days_count == 0:
    raise SystemExit(">>> 无可用的共同日期进行匹配！")

# 创建日期映射：AV的第n天对应HV的第n天
date_mapping = {
    av_date: hv_date
    for av_date, hv_date in zip(
        av_unique_dates[:common_days_count],
        hv_unique_dates[:common_days_count]
    )
}


# 转换HV日期以匹配AV日期（按顺序）
def map_hv_dates(row):
    hv_date = row['start_time'].date()
    # 找到HV日期在其唯一列表中的索引
    try:
        idx = hv_unique_dates.index(hv_date)
        # 如果索引在共同日期范围内，返回对应的AV日期
        if idx < common_days_count:
            return pd.Timestamp(av_unique_dates[idx]) + (row['start_time'] - pd.Timestamp(hv_date))
        else:
            return pd.NaT  # 超出共同日期范围
    except ValueError:
        return pd.NaT  # 不在HV日期列表中


# 应用日期映射
hv['mapped_start_time'] = hv.apply(map_hv_dates, axis=1)
# 移除无法映射的记录
hv = hv.dropna(subset=['mapped_start_time'])
# 用映射后的日期替换原始日期进行后续处理
hv['start_time'] = hv['mapped_start_time']
hv = hv.drop(columns=['mapped_start_time'])

# --------------------------------------------------
# 3. 时间分箱
# --------------------------------------------------
av['hour_bin'] = av['呼单时间'].dt.floor(f'{HOUR_BIN}H')
hv['hour_bin'] = hv['start_time'].dt.floor(f'{HOUR_BIN}H')

# --------------------------------------------------
# 4. 分块计数与maxHV拟合（使用全部格子数据）
# --------------------------------------------------
# 获取所有可能的hour_bin
all_hour_bins = pd.concat([av['hour_bin'], hv['hour_bin']]).unique()

# 生成所有网格和时间组合
grid_hour_combinations = []
for grid in all_grids:
    gx, gy = grid
    for hour_bin in all_hour_bins:
        grid_hour_combinations.append((gx, gy, hour_bin))

# 创建包含所有组合的DataFrame
full_df = pd.DataFrame(grid_hour_combinations, columns=['gx', 'gy', 'hour_bin'])

# 计算AV计数（AV数据用订单号计数）
av_count = av.groupby(['gx', 'gy', 'hour_bin'])['订单号'].count().reset_index(name='AV')
# 合并到全量数据，无数据的AV视为0
full_df = full_df.merge(av_count, on=['gx', 'gy', 'hour_bin'], how='left').fillna({'AV': 0})

# 计算HV计数（HV数据用order_id计数，替代原有的id字段）
hv_count = hv.groupby(['gx', 'gy', 'hour_bin'])['order_id'].count().reset_index(name='HV')
# 合并到全量数据，无数据的HV视为0
full_df = full_df.merge(hv_count, on=['gx', 'gy', 'hour_bin'], how='left').fillna({'HV': 0})

# 按AV分组取最大HV
fit_df = full_df.groupby('AV')['HV'].max().reset_index(name='maxHV')
# 获取每个maxHV对应的网格信息
max_hv_grids = full_df.loc[full_df.groupby('AV')['HV'].idxmax(), ['AV', 'gx', 'gy']]
fit_df = fit_df.merge(max_hv_grids, on=['AV'], how='left')

if fit_df.empty:
    raise SystemExit('>>> 无AV与HV的交集网格-时间单元！请检查网格划分或数据时间分箱')

# 添加cci值（仅保留数据，不用于颜色映射）
fit_df['cci'] = fit_df.apply(lambda row: cci_map.get((row['gx'], row['gy']), 0), axis=1)

# --------------------------------------------------
# 新增：对蓝色点进行基于位置的稀疏化（按坐标范围分段）
# --------------------------------------------------
# 初始化保留概率为最终保留比例
full_df['keep_prob'] = FINAL_RETENTION

# 非AV=0点的稀疏化规则
non_av0_mask = (full_df['AV'] != 0)

# 规则1：(10,50)以内保留1%
rule1_mask = non_av0_mask & (full_df['AV'] <= RETENTION_RULES[0][0]) & (full_df['HV'] <= RETENTION_RULES[0][1])
full_df.loc[rule1_mask, 'keep_prob'] = RETENTION_RULES[0][2]

# 规则2：(10,50)以外且(15,100)以内保留5%
rule2_mask = non_av0_mask & (~rule1_mask) & (full_df['AV'] <= RETENTION_RULES[1][0]) & (
            full_df['HV'] <= RETENTION_RULES[1][1])
full_df.loc[rule2_mask, 'keep_prob'] = RETENTION_RULES[1][2]

# 规则3：(15,100)以外且(20,150)以内保留5%
rule3_mask = non_av0_mask & (~rule1_mask) & (~rule2_mask) & (full_df['AV'] <= RETENTION_RULES[2][0]) & (
            full_df['HV'] <= RETENTION_RULES[2][1])
full_df.loc[rule3_mask, 'keep_prob'] = RETENTION_RULES[2][2]

# 规则4：(20,150)以外且(25,200)以内保留15%
rule4_mask = non_av0_mask & (~rule1_mask) & (~rule2_mask) & (~rule3_mask) & (full_df['AV'] <= RETENTION_RULES[3][0]) & (
            full_df['HV'] <= RETENTION_RULES[3][1])
full_df.loc[rule4_mask, 'keep_prob'] = RETENTION_RULES[3][2]

# 规则5：(25,200)以外且(30,250)以内保留25%
rule5_mask = non_av0_mask & (~rule1_mask) & (~rule2_mask) & (~rule3_mask) & (~rule4_mask) & (
            full_df['AV'] <= RETENTION_RULES[4][0]) & (full_df['HV'] <= RETENTION_RULES[4][1])
full_df.loc[rule5_mask, 'keep_prob'] = RETENTION_RULES[4][2]

# 规则6：(30,250)以外且(35,300)以内保留40%
rule6_mask = non_av0_mask & (~rule1_mask) & (~rule2_mask) & (~rule3_mask) & (~rule4_mask) & (~rule5_mask) & (
            full_df['AV'] <= RETENTION_RULES[5][0]) & (full_df['HV'] <= RETENTION_RULES[5][1])
full_df.loc[rule6_mask, 'keep_prob'] = RETENTION_RULES[5][2]

# 规则7：(35,300)以外且(40,350)以内保留60%
rule7_mask = non_av0_mask & (~rule1_mask) & (~rule2_mask) & (~rule3_mask) & (~rule4_mask) & (~rule5_mask) & (
    ~rule6_mask) & (full_df['AV'] <= RETENTION_RULES[6][0]) & (full_df['HV'] <= RETENTION_RULES[6][1])
full_df.loc[rule7_mask, 'keep_prob'] = RETENTION_RULES[6][2]

# 对AV=0的点进行分层抽样（按HV值均匀保留）
av0_mask = (full_df['AV'] == 0)
if full_df[av0_mask].shape[0] > 0:
    # 计算需要保留的数量
    av0_keep_count = max(1, int(AV0_RETENTION * full_df[av0_mask].shape[0]))

    # 按HV值排序并分成10个区间
    av0_df = full_df[av0_mask].sort_values('HV').copy()
    av0_df['hv_bin'] = pd.qcut(av0_df['HV'], q=10, duplicates='drop')

    # 每个区间按比例保留
    av0_kept = []
    total_bins = av0_df['hv_bin'].nunique()
    per_bin_keep = max(1, av0_keep_count // total_bins)

    for _, bin_df in av0_df.groupby('hv_bin'):
        if len(bin_df) <= per_bin_keep:
            av0_kept.append(bin_df)
        else:
            # 每个区间随机保留指定数量
            av0_kept.append(bin_df.sample(per_bin_keep, random_state=42))

    # 合并保留的AV=0点
    av0_kept_df = pd.concat(av0_kept)
    full_df.loc[:, 'keep'] = False
    full_df.loc[av0_kept_df.index, 'keep'] = True
else:
    full_df['keep'] = False

# 对非AV=0的点根据概率随机筛选
np.random.seed(42)  # 设置随机种子确保结果可复现
full_df.loc[non_av0_mask, 'keep'] = np.random.rand(sum(non_av0_mask)) < full_df.loc[non_av0_mask, 'keep_prob']

filtered_full = full_df[full_df['keep']]

# 输出详细稀疏统计，方便调试
print(f"=== 点稀疏化结果 ===")
print(f"原始蓝色点数量：{len(full_df)}")
print(f"筛选后蓝色点数量：{len(filtered_full)}")
print(f"整体保留比例：{len(filtered_full) / len(full_df):.2%}")
print(f"AV=0点保留情况：{full_df[av0_mask]['keep'].mean():.2%} (目标：{AV0_RETENTION:.2%})")
print(f"非AV=0点保留情况：")
print(f"  (10,50)以内：{full_df[rule1_mask]['keep'].mean():.2%} (目标：{RETENTION_RULES[0][2]:.2%})")
print(f"  (10,50)~(15,100)：{full_df[rule2_mask]['keep'].mean():.2%} (目标：{RETENTION_RULES[1][2]:.2%})")
print(f"  (15,100)~(20,150)：{full_df[rule3_mask]['keep'].mean():.2%} (目标：{RETENTION_RULES[2][2]:.2%})")
print(f"  (20,150)~(25,200)：{full_df[rule4_mask]['keep'].mean():.2%} (目标：{RETENTION_RULES[3][2]:.2%})")
print(f"  (25,200)~(30,250)：{full_df[rule5_mask]['keep'].mean():.2%} (目标：{RETENTION_RULES[4][2]:.2%})")
print(f"  (30,250)~(35,300)：{full_df[rule6_mask]['keep'].mean():.2%} (目标：{RETENTION_RULES[5][2]:.2%})")
print(f"  (35,300)~(40,350)：{full_df[rule7_mask]['keep'].mean():.2%} (目标：{RETENTION_RULES[6][2]:.2%})")
print(
    f"  (40,350)以外：{full_df[non_av0_mask & ~(rule1_mask | rule2_mask | rule3_mask | rule4_mask | rule5_mask | rule6_mask | rule7_mask)]['keep'].mean():.2%} (目标：{FINAL_RETENTION:.2%})")

# --------------------------------------------------
# 5. 指数模型拟合 (f(x) = a * e^(b*x + c) + d)
# --------------------------------------------------
# 过滤AV=0的数据，避免拟合问题
valid_fit_df = fit_df[fit_df['AV'] > 0].copy()
if valid_fit_df.empty:
    raise SystemExit(">>> 无有效的AV>0数据用于模型拟合！")


# 定义指数函数
def exponential_func(x, a, b, c, d):
    return a * np.exp(b * x + c) + d


# 初始参数猜测
initial_guess = [1, 0.01, 0, 0]

# 拟合数据
X_fit = valid_fit_df['AV'].values
y_fit = valid_fit_df['maxHV'].values

try:
    popt, pcov = curve_fit(exponential_func, X_fit, y_fit, p0=initial_guess, maxfev=10000)
    a, b, c, d = popt  # 拟合参数

    # 计算R²值
    y_pred = exponential_func(X_fit, *popt)
    ss_total = np.sum((y_fit - np.mean(y_fit)) ** 2)
    ss_residual = np.sum((y_fit - y_pred) ** 2)
    r2 = 1 - (ss_residual / ss_total)

    print(f"\n=== 模型拟合结果 ===")
    print(f"指数模型：f(x) = {a:.0f}·e^({b:.1f}·x + {c:.1f}) + {d:.0f}")
    print(f"决定系数 R² = {r2:.2f}")
except RuntimeError as e:
    raise SystemExit(f">>> 模型拟合失败：{e}")

# --------------------------------------------------
# 6. 主图绘制
# --------------------------------------------------
# 全局字体设置：强制所有文字使用Calibri
plt.rcParams['font.family'] = 'Calibri'
plt.rcParams['font.sans-serif'] = ['Calibri']  # 确保回退字体也是Calibri
plt.rcParams['mathtext.fontset'] = 'custom'  # 自定义数学公式字体
plt.rcParams['mathtext.rm'] = 'Calibri'     # 数学公式中的常规字体
plt.rcParams['mathtext.it'] = 'Calibri:italic'  # 数学公式中的斜体
plt.rcParams['mathtext.bf'] = 'Calibri:bold'    # 数学公式中的粗体

# 设置全局字体大小基准
plt.rcParams['font.size'] = 10 * FONT_SCALE  # 基础字号放大1.5倍

# 布局设置
fig = plt.figure(figsize=(6, 5))
gs = GridSpec(4, 4, figure=fig,
              hspace=0.0, wspace=0.0,
              left=0.15, right=0.95, bottom=0.12, top=0.95)

ax_main = fig.add_subplot(gs[1:, :-1])  # 主散点图
ax_top = fig.add_subplot(gs[0, :-1], sharex=ax_main)  # 上侧AV频率条
ax_right = fig.add_subplot(gs[1:, -1], sharey=ax_main)  # 右侧HV频率条

# 1. 筛选后的HV数据散点（原大小的60%）
ax_main.scatter(filtered_full['AV'], filtered_full['HV'],
                s=15 * SCALE_FACTOR, alpha=0.4, color='tab:blue')  # 移除label，不显示Actual

# 2. 各AV对应的maxHV点（使用统一红色，原大小的60%）
ax_main.scatter(fit_df['AV'], fit_df['maxHV'],
                s=25 * SCALE_FACTOR, color='red',  # 移除label，不显示Maximum
                zorder=4)

# 3. 指数拟合曲线（仅使用AV>0的数据）
x_dense = np.linspace(0, 80, 300)  # 横坐标范围调整为0~80
y_dense = exponential_func(x_dense, *popt)
# 移除曲线的label参数，不在图例中显示
ax_main.plot(x_dense, y_dense, color='black', lw=2)

# 在R²标注上方显示拟合表达式（调整位置：x=20, y=125）
# 格式化拟合表达式，保留3位小数
fit_expression = f'$f(x) = {a:.0f} \\cdot e^{{{b:.1f}x + {c:.1f}}} + {d:.0f}$'
# 调整表达式位置到x=20, y=125（上移10个单位，横坐标从40改为20）
ax_main.text(30, 125, fit_expression,
             fontsize=10.5 * FONT_SCALE,
             fontfamily='Calibri',
             fontname='Calibri',
             color='black',
             ha='left', va='center')

# 在固定位置(x=40, y=95)添加R²文本标注
# 强制使用Calibri字体，字号与图例完全一致
ax_main.text(40, 95, f'$R^2$ = {r2:.2f}',
             fontsize=10.5 * FONT_SCALE,  # 与图例字号一致
             fontfamily='Calibri',        # 强制指定Calibri字体
             fontname='Calibri',          # 双重保障指定字体
             color='black',
             ha='left', va='center')

# 主图样式 - 调整坐标范围和刻度
ax_main.set_xlabel('Robotaxi Order Count', fontsize=10 * FONT_SCALE)  # 字号放大1.5倍
ax_main.set_ylabel('HV Order Count', fontsize=10 * FONT_SCALE)  # 字号放大1.5倍
ax_main.set_xlim(0, 80)  # 横坐标范围0~80
ax_main.set_ylim(0, 360)  # 纵坐标范围0~360
ax_main.set_xticks(np.arange(0, 81, 20))  # 横坐标每20标一个刻度
ax_main.set_yticks(np.arange(0, 361, 90))  # 纵坐标每90标一个刻度

# 调整刻度标签字号
ax_main.tick_params(axis='both', labelsize=8 * FONT_SCALE)  # 刻度数字字号放大1.5倍
# 移除网格线
# ax_main.grid(True, lw=0.3, alpha=0.15, color='grey')

# 上侧边际条（AV频率）- 修复最右侧边框问题
av_bins = np.arange(0, 82, 2)  # 扩展bins到82，确保80在范围内
counts_av, _ = np.histogram(full_df['AV'], bins=av_bins)
# 绘制频率条，调整宽度和对齐方式
ax_top.bar(av_bins[:-1], np.log10(1 + counts_av), width=2, align='center',  # 改为center对齐
           color='#E8ADA0', alpha=1, edgecolor='black', linewidth=0.6)

# 修复：扩展坐标轴范围，确保最右侧边框可见
ax_top.set_xlim(-1, 81)  # 向左扩展1，向右扩展1
ax_top.spines[['top', 'left', 'right']].set_visible(False)
ax_top.spines['bottom'].set_linewidth(0.6)  # 保留底部spine并设置线宽
ax_top.tick_params(left=False, labelleft=False, bottom=False, labelbottom=False)

# 额外添加最右侧边框线（兜底方案）
if len(counts_av) > 0:
    from matplotlib.patches import Rectangle
    # 找到最右侧有值的柱子位置
    last_non_zero_idx = np.max(np.where(counts_av > 0)[0]) if np.any(counts_av > 0) else len(counts_av)-1
    last_bin_center = av_bins[:-1][last_non_zero_idx] + 1  # center对齐的柱子中心+1=右边缘
    # 绘制右侧边框线
    rect = Rectangle((last_bin_center, 0),
                     width=0,  # 宽度为0，仅显示竖线
                     height=np.log10(1 + counts_av[last_non_zero_idx]),
                     fill=False,
                     edgecolor='black',
                     linewidth=0.6,
                     clip_on=False)
    ax_top.add_patch(rect)

# 右侧边际条（HV频率）
hv_bins = np.arange(0, 361, 10)  # 调整频率条范围匹配新纵坐标
counts_hv, _ = np.histogram(full_df['HV'], bins=hv_bins)
# 绘制右侧频率条，增加线宽并确保底部边框可见
ax_right.barh(hv_bins[:-1], np.log10(1 + counts_hv), height=10, align='edge',
              color='#66C2F6', alpha=1, edgecolor='black', linewidth=0.8)  # 线宽从0.6增加到0.8

# 特别处理最底部的柱形，确保下边框可见
if len(counts_hv) > 0 and counts_hv[0] > 0:
    from matplotlib.patches import Rectangle
    # 添加一个额外的矩形来强化底部边框
    bottom_bin = hv_bins[0]
    rect = Rectangle((0, bottom_bin),
                     width=np.log10(1 + counts_hv[0]),
                     height=10,
                     fill=False,
                     edgecolor='black',
                     linewidth=0.8,
                     clip_on=False)
    ax_right.add_patch(rect)

# 修复：先扩展坐标轴范围，再隐藏spines
ax_right.set_ylim(0, 360)  # 匹配主图新纵坐标范围
ax_right.spines[['top', 'right', 'bottom']].set_visible(False)
ax_right.spines['left'].set_linewidth(0.6)  # 保留左侧spine并设置线宽
ax_right.tick_params(bottom=False, labelbottom=False, left=False, labelleft=False)

# --------------------------------------------------
# 核心修改：重新组织图例元素和排版（移除红色点图例）
# --------------------------------------------------
# 1. 创建图例元素（仅保留Frequency和拟合曲线）
legend_elements = [
    Patch(facecolor='#E8ADA0', edgecolor='black', linewidth=0.6 * LEGEND_SCALE, label='Robotaxi Frequency'),
    Patch(facecolor='#66C2F6', edgecolor='black', linewidth=0.6 * LEGEND_SCALE, label='Human-driven Frequency'),
    Line2D([0], [0], color='black', linewidth=2 * LEGEND_SCALE, label='Maximum service curve')
]

# 2. 设置图例：单列排版，字号和整体大小放大1.5倍
legend = ax_main.legend(
    legend_elements,
    [elem.get_label() for elem in legend_elements],
    loc='upper right',
    bbox_to_anchor=(0.98, 0.98),
    ncol=1,  # 单列排版
    handletextpad=0.3 * LEGEND_SCALE,
    fontsize=10.5 * FONT_SCALE,  # 字号放大1.5倍
    frameon=True,
    fancybox=False,
    edgecolor=(0.7, 0.7, 0.7),
    facecolor='white',
    labelspacing=0.4 * LEGEND_SCALE,
    columnspacing=0.6 * LEGEND_SCALE,
    borderaxespad=0.1 * LEGEND_SCALE,
    # 调整图例框大小
    handlelength=2 * LEGEND_SCALE,
    borderpad=0.5 * LEGEND_SCALE
)

# 调整图例框的线宽
legend.get_frame().set_linewidth(0.8 * LEGEND_SCALE)

# --------------------------------------------------
# 7. 保存与显示
# --------------------------------------------------
out_png = f'robotaxi_humandriven_scatter_{H_SHIFT:+d}h_legend_layout_fixed_new_format.png'
fig.savefig(out_png, dpi=300, bbox_inches='tight')
print(f"\n图像已保存为: {out_png}")
plt.show()
