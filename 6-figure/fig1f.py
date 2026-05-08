import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta
import numpy as np

plt.rcParams['font.family'] = 'Arial'

# 读取数据
df = pd.read_csv("charge.csv")

# 时间解析
df["充电开始时间"] = pd.to_datetime(df["充电开始时间"])
df["充电结束时间"] = pd.to_datetime(df["充电结束时间"])
df["date"] = df["充电开始时间"].dt.date

BATTERY_KWH = 93.6

# 计算充电量与线性功率
df["charge_kwh"] = (df["充点后电量"] - df["充点前电量"]) / 100 * BATTERY_KWH
df["duration_sec"] = (df["充电结束时间"] - df["充电开始时间"]).dt.total_seconds()
df["power_kw"] = df["charge_kwh"] / (df["duration_sec"] / 3600)

records = []

# 拆分到每个小时
for _, r in df.iterrows():
    t0, t1 = r["充电开始时间"], r["充电结束时间"]
    cur = t0
    while cur < t1:
        hour_start = cur.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)

        seg_start = max(cur, hour_start)
        seg_end = min(t1, hour_end)

        seg_hours = (seg_end - seg_start).total_seconds() / 3600
        seg_kwh = seg_hours * r["power_kw"]

        records.append({
            "date": r["date"],
            "hour": hour_start.hour,
            "charge_kwh": seg_kwh
        })

        cur = hour_end

hourly_df = pd.DataFrame(records)

# 每天、每小时汇总
daily_hour_sum = (
    hourly_df
    .groupby(["date", "hour"], as_index=False)["charge_kwh"]
    .sum()
)

# 构造箱线图数据
box_data = [
    daily_hour_sum.loc[daily_hour_sum["hour"] == h, "charge_kwh"]
    for h in range(24)
]

# Viridis 渐变色
cmap = plt.cm.viridis
colors = cmap(np.linspace(0.1, 0.9, 24))

# 绘图
fig, ax = plt.subplots(figsize=(6.5, 3))
bp = ax.boxplot(
    box_data,
    positions=range(24),
    widths=0.65,
    patch_artist=True,
    showfliers=False
)

# 样式设置（Nature 风格）
for patch, color in zip(bp["boxes"], colors):
    patch.set_facecolor(color)
    patch.set_edgecolor("black")
    patch.set_linewidth(0.8)

for element in ["whiskers", "caps", "medians"]:
    for item in bp[element]:
        item.set_color("black")
        item.set_linewidth(1.2 if element == "medians" else 0.8)

ax.set_xlabel("Hour of day", fontsize=14)
ax.set_xticks(range(24))

# 隐藏原Y轴标签
ax.set_yticklabels([])
ax.set_ylabel("")

# 手动添加Y轴标签 - 旋转90度并调整垂直位置
ax.text(-0.08, -0.15, "Daily total charging energy (kWh)", 
        transform=ax.transAxes, fontsize=14, rotation=90, 
        va='bottom', ha='center', fontfamily='Arial')

# 背景虚线格子
ax.grid(True, axis="both", linestyle="--", linewidth=0.6, alpha=0.5)

plt.tight_layout()
plt.savefig("hourly_charging_boxplot.svg")
plt.close()