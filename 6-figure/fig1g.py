import pandas as pd
import matplotlib.pyplot as plt

# ======================
# 1. 读取与预处理
# ======================
df = pd.read_csv("vehicle_stats_detail_av-1.csv")

df["Fuel(g)"] = df["Fuel(g)"].replace("-", 0).astype(float)
df["Electricity(kWh)"] = df["Electricity(kWh)"].astype(float)
df["CO2(g)"] = df["CO2(g)"].astype(float)

# 时间处理
df["hour"] = df["Timestamp(s)"] // 3600
df.loc[df["hour"] >= 24, "hour"] = 0

# ======================
# 2. 统计计算
# ======================
# 左轴：每个订单(VehicleID)的总排放分布
order_sums = (
    df.groupby(["hour", "VehicleID"])["CO2(g)"]
    .sum()
    .reset_index(name="order_total_CO2")
)

# 准备箱线图数据：按小时将订单总量存入列表
box_data = [order_sums[order_sums["hour"] == h]["order_total_CO2"] for h in range(24)]

# 右轴：该小时内所有订单的排放总合 (ton)
hourly_total = (
    df.groupby("hour")["CO2(g)"]
    .sum()
    .reset_index(name="total_CO2_ton")
)
hourly_total["total_CO2_ton"] /= 1e6 # 转化为吨

# ======================
# 3. 绘图样式
# ======================
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Arial"],
    "font.size": 10,
    "axes.linewidth": 0.9,
    "xtick.direction": "in",
    "ytick.direction": "in",
})

fig, ax1 = plt.subplots(figsize=(6, 4))
main_color = "#355f73"
second_color = "#d95f02" # 使用对比色区分总量

# 背景峰值区域
ax1.axvspan(7, 9, color="#eef3f7", zorder=0)
ax1.axvspan(17, 19, color="#f7efe6", zorder=0)

# --- 左轴：箱线图 ---
# patch_artist=True 允许填充颜色，showfliers=False 可以隐藏异常值让图表更整洁（如果异常值太多的话）
bplot = ax1.boxplot(
    box_data,
    positions=range(24),
    widths=0.6,
    patch_artist=True,
    showfliers=False, # 专家通常建议隐藏极端离群点以观察主体分布
    medianprops=dict(color="white", linewidth=1),
    boxprops=dict(facecolor=main_color, color=main_color, alpha=0.7),
    whiskerprops=dict(color=main_color),
    capprops=dict(color=main_color)
)

ax1.set_xlabel("Hour of day")
ax1.set_ylabel("CO$_2$ emissions per order (g)", color=main_color)
ax1.tick_params(axis='y', labelcolor=main_color)
ax1.set_xticks(range(0, 24, 3))
ax1.set_xlim(-1, 24)

# --- 右轴：总排放折线 ---
ax2 = ax1.twinx()
line2, = ax2.plot(
    hourly_total["hour"],
    hourly_total["total_CO2_ton"],
    color=second_color,
    marker='o',
    markersize=3,
    linewidth=1.2,
    label="Total Hourly Emissions"
)

ax2.set_ylabel("Total CO$_2$ emissions (ton)", color=second_color)
ax2.tick_params(axis='y', labelcolor=second_color)
ax2.set_ylim(bottom=0)

# --- 细节优化 ---
ax1.spines["top"].set_visible(False)
ax2.spines["top"].set_visible(False)

# 自定义图例
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], color=main_color, lw=4, label='Order Distribution (g)', alpha=0.7),
    Line2D([0], [0], color=second_color, lw=1.2, marker='o', label='Total Emissions (ton)')
]
ax1.legend(handles=legend_elements, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.15), fontsize=9)

plt.tight_layout()

# 保存1200dpi的SVG文件
plt.savefig("hourly_CO2_distribution.svg", format="svg", dpi=1200)

plt.show()