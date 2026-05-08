# 天气+等待时间
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load data
df = pd.read_csv("v8-av.csv", 
                parse_dates=["到达起点时间", "接单时间"])

# Data processing
df = df[df["订单状态"] != "取消"]
df["处理时间"] = (df["到达起点时间"] - df["接单时间"]).dt.total_seconds() / 60
weather_translation = {"晴": "Clear", "雨": "Rain", "阴": "Cloudy", "雾": "Fog"}
df["天气状态"] = df["天气状态"].map(weather_translation).fillna("Unknown")

weather_palette = {
    "Clear": "#FFD700",  # 阳光金
    "Cloudy": "#C0C0C0", # 银灰
    "Rain": "#006994"    # 海洋蓝
}

# Configure Nature style
plt.rcParams.update({
    'font.size': 7,
    'font.sans-serif': 'Arial',
    'axes.labelsize': 8,
    'axes.titlesize': 9,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'axes.linewidth': 0.6,
    'xtick.major.width': 0.6,
    'ytick.major.width': 0.6
})

# Create horizontal boxplot
fig, ax = plt.subplots(figsize=(3.5, 1.5))  # 5x2 inch size

# Nature color palette (muted blue, steel blue, slate gray)
palette = ["#4575b4", "#74add1", "#636363"]

# Enhanced boxplot styling
boxprops = dict(linewidth=0.6, color='#2b8cbe', facecolor=palette[0])
whiskerprops = dict(linewidth=0.6, color='#969696', linestyle='-')
medianprops = dict(linewidth=0.8, color='#d73027')

# 在箱线图中应用新配色
sns.boxplot(
    y="天气状态",
    x="处理时间",
    data=df[df["天气状态"].isin(["Clear", "Cloudy", "Rain"])],
    order=["Clear", "Cloudy", "Rain"],
    palette=[weather_palette[w] for w in ["Clear", "Cloudy", "Rain"]],
    width=0.5,
    linewidth=0.6,
    showfliers=False,
    orient='h',
    whiskerprops=dict(
        linewidth=0.6,
        color='#333333'       # 须线颜色
    ),
    medianprops=dict(
        linewidth=0.8,
        color='#333333'       # 中位线颜色
    ),
    capprops=dict(            # 新增须线端帽样式
        linewidth=0.6,
        color='#333333'
    )
)


# Axis labels
ax.set_xlabel("Waiting Time (minutes)", labelpad=1)
ax.set_ylabel("Weather Condition", labelpad=1)

# Nature-style grid
ax.xaxis.grid(True, linestyle='--', alpha=0.3, linewidth=0.5)
# ax.spines[['top', 'right']].set_visible(False)

# Adjust tick parameters
ax.tick_params(axis='both', which='major', pad=1)

# Set axis limits
ax.set_xlim(left=0)

plt.tight_layout(pad=0.5)
plt.savefig("weather_boxplot_horizontal.svg", dpi=600, bbox_inches="tight")