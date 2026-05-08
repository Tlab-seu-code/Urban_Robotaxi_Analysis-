
# import pandas as pd
# import matplotlib.pyplot as plt

# # ======================
# # 1. 读取与预处理
# # ======================
# df = pd.read_csv("vehicle_stats_detail_av.csv")

# # "-" 转为0
# df["Fuel(g)"] = df["Fuel(g)"].replace("-", 0).astype(float)
# df["Electricity(kWh)"] = df["Electricity(kWh)"].astype(float)
# df["CO2(g)"] = df["CO2(g)"].astype(float)

# # ---- 单位转换：g → ton ----
# df["CO2(ton)"] = df["CO2(g)"] / 1e6


# # ======================
# # 2. 定义时间段
# # ======================
# def get_period(t):
#     if 7*3600 <= t < 9*3600:
#         return "morning_peak"   # 7:00–9:00
#     elif 9*3600 <= t < 17*3600:
#         return "midday"         # 9:00–17:00
#     elif 17*3600 <= t < 20*3600:
#         return "evening_peak"   # 17:00–20:00
#     else:
#         return "night"          # 20:00–7:00

# df["Period"] = df["Timestamp(s)"].apply(get_period)


# # ======================
# # 3. 时间段排放统计（ton）
# # ======================
# period_stats = df.groupby("Period")["CO2(ton)"].agg(
#     avg_CO2="mean",
#     total_CO2="sum",
#     count="count"
# ).reset_index()

# print("\n=== 时间段 CO2 排放统计（ton） ===")
# print(period_stats)


# # ======================
# # 4. 各车辆在时间段的排放特征（ton）
# # ======================
# vehicle_period_stats = df.groupby(["VehicleID", "Period"])["CO2(ton)"].agg(
#     avg_CO2="mean",
#     total_CO2="sum",
#     count="count"
# ).reset_index()

# print("\n=== 各车辆在不同时间段的排放特征（前10行，ton） ===")
# print(vehicle_period_stats.head(10))


# # ======================
# # 5. 时间段贡献比例
# # ======================
# total_CO2 = df["CO2(ton)"].sum()
# period_stats["CO2_ratio"] = period_stats["total_CO2"] / total_CO2

# print("\n=== 各时间段 CO2 占全天比例 ===")
# print(period_stats[["Period", "total_CO2", "CO2_ratio"]])


# # ======================
# # 6. 小时聚合（ton）
# # ======================
# df["hour"] = df["Timestamp(s)"] // 3600
# hourly = df.groupby("hour")["CO2(ton)"].sum().reset_index()


# # ======================
# # Nature-style plotting
# # ======================
# plt.rcParams.update({
#     "font.family": "serif",
#     "font.serif": ["Arial"],
#     "font.size": 10,
#     "axes.linewidth": 1.0,
#     "axes.labelsize": 10,
#     "axes.titlesize": 11,
#     "xtick.direction": "in",
#     "ytick.direction": "in",
#     "xtick.major.size": 4,
#     "ytick.major.size": 4,
#     "xtick.major.width": 1,
#     "ytick.major.width": 1,
# })

# fig, ax = plt.subplots(figsize=(4, 2.8))

# # ---- 时间段背景 ----
# ax.axvspan(7, 9,  color="#c6dbef", alpha=0.45)
# ax.axvspan(9, 17, color="#e5f5e0", alpha=0.45)
# ax.axvspan(17, 20, color="#fdd0a2", alpha=0.45)
# ax.axvspan(0, 7,  color="#f5f5f5", alpha=0.8)
# ax.axvspan(20, 24, color="#f5f5f5", alpha=0.8)

# # ---- 主线 + 隐式点（ton）----
# ax.plot(
#     hourly["hour"],
#     hourly["CO2(ton)"],
#     color="#2b4c7e",
#     linewidth=1.6,
#     zorder=3
# )

# ax.scatter(
#     hourly["hour"],
#     hourly["CO2(ton)"],
#     s=15,
#     color="#1f3b5c",
#     alpha=0.4,
#     zorder=4
# )

# # ======================
# # Axes & labels
# # ======================
# ax.set_xlim(0, 23)
# ax.set_xticks(range(0, 24, 3))
# ax.set_xlabel("Hour of day")
# ax.set_ylabel("CO$_2$ emissions (ton)")
# ax.set_title("Hourly CO$_2$ emissions")

# ax.spines["top"].set_visible(False)
# ax.spines["right"].set_visible(False)

# plt.tight_layout()

# # ======================
# # Save as PDF
# # ======================
# plt.savefig("hourly_CO2_distribution.pdf", format="pdf")
# plt.show()

import pandas as pd
import matplotlib.pyplot as plt

# ======================
# 1. 读取与预处理
# ======================
df = pd.read_csv("vehicle_stats_detail_av.csv")

df["Fuel(g)"] = df["Fuel(g)"].replace("-", 0).astype(float)
df["Electricity(kWh)"] = df["Electricity(kWh)"].astype(float)
df["CO2(g)"] = df["CO2(g)"].astype(float)

# hour
df["hour"] = df["Timestamp(s)"] // 3600
# 将 hour >= 24 的值置为 0
df.loc[df["hour"] >= 24, "hour"] = 0
# 总量：g → ton（仅用于右轴）
df["CO2(ton)"] = df["CO2(g)"] / 1e6



# ======================
# 2. Order-level statistics
# ======================
# VehicleID is treated as OrderID
order_hour = (
    df.groupby(["hour", "VehicleID"])["CO2(g)"]
      .mean()
      .reset_index(name="order_avg_CO2")
)

hourly_order_stats = (
    order_hour.groupby("hour")["order_avg_CO2"]
    .agg(
        mean_CO2="mean",
        std_CO2="std"
    )
    .reset_index()
)

# Total emissions (ton)
hourly_total = (
    df.groupby("hour")["CO2(ton)"]
    .sum()
    .reset_index(name="total_CO2_ton")
)


# ======================
# 3. Plot style
# ======================
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Arial"],
    "font.size": 10,
    "axes.linewidth": 0.9,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.size": 3.5,
    "ytick.major.size": 3.5,
})

fig, ax1 = plt.subplots(figsize=(5.2, 3))


# ======================
# 4. Background emphasis
# ======================
ax1.axvspan(7, 9, color="#eef3f7", zorder=0)
ax1.axvspan(17, 20, color="#f7efe6", zorder=0)

for h in [7, 9, 17, 20]:
    ax1.axvline(h, color="0.75", linestyle="--", linewidth=0.7, zorder=1)


# ======================
# 5. Left axis: order-average + variance
# ======================
main_color = "#355f73"

# Mean line
line1, = ax1.plot(
    hourly_order_stats["hour"],
    hourly_order_stats["mean_CO2"],
    color=main_color,
    linewidth=1.5,
    zorder=4
)

# Mean markers
ax1.scatter(
    hourly_order_stats["hour"],
    hourly_order_stats["mean_CO2"],
    s=16,
    color=main_color,
    alpha=0.6,
    zorder=5
)

# Variance (±1 std) as subtle vertical ranges
ax1.vlines(
    hourly_order_stats["hour"],
    hourly_order_stats["mean_CO2"] - hourly_order_stats["std_CO2"],
    hourly_order_stats["mean_CO2"] + hourly_order_stats["std_CO2"],
    color=main_color,
    alpha=0.25,
    linewidth=1.0,
    zorder=3
)

ax1.set_xlabel("Hour of day")
ax1.set_ylabel("Mean CO$_2$ per order (g)")
ax1.set_xlim(0, 23)
ax1.set_xticks(range(0, 24, 3))


# ======================
# 6. Right axis: total emissions
# ======================
ax2 = ax1.twinx()

line2, = ax2.plot(
    hourly_total["hour"],
    hourly_total["total_CO2_ton"],
    color="#9a9a9a",
    linewidth=1.2,
    alpha=0.9,
    zorder=2
)

ax2.set_ylabel("Total CO$_2$ emissions (ton)")


# ======================
# 7. Final polish
# ======================
ax1.spines["top"].set_visible(False)
ax2.spines["top"].set_visible(False)

fig.legend(
    [line1, line2],
    ["Order-average CO$_2$ (±1 std)", "Total CO$_2$"],
    loc="upper center",
    ncol=2,
    frameon=False,
    bbox_to_anchor=(0.5, 1.02),
    fontsize=8
)
ax1.set_ylim(bottom=0)
plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig("hourly_order_avg_and_total_CO2.pdf", format="pdf")
plt.show()

