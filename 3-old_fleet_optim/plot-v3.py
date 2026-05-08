# -*- coding: utf-8 -*-
"""
Created on Fri Dec  6 21:33:49 2024

@author: TLab
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 配置中文字体为黑体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 或者 'SimHei' 根据安装的字体来选择
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 读取处理后的CSV文件
df = pd.read_csv("v3-districts.csv")

# 分析完成单

data = df[(df['用户id'] != 'virtual-schedule') 
          & (df['订单状态'] == '完成')
          & (df['订单来源'] != '调度单')
          & (df['订单来源'] != '充电单')            
          ]

# data = df[df['index'] == 0]

data['接单时间'] = pd.to_datetime(data['接单时间'])
data = data[data['接单时间'].dt.weekday == 6]  # 周一到周五对应的 weekday 值是 0 到 4


# 确保数据中没有缺失值，替换缺失值为"未知"
# data['起点所属区'] = data['起点所属区'].fillna("未知")
# data['终点所属区'] = data['终点所属区'].fillna("未知")

## (1) 起点/终点所属区域订单数量的柱状图
def plot_order_distribution(data):
    # 统计起点和终点订单数量
    start_counts = data['起点所属区'].value_counts()
    end_counts = data['终点所属区'].value_counts()

    # 合并为一个 DataFrame
    counts = pd.DataFrame({
        '起点订单数量': start_counts,
        '终点订单数量': end_counts
    }).fillna(0).astype(int)

    # 绘制柱状图
    counts.plot(kind='bar', figsize=(12, 6))
    plt.title("各区域起点/终点订单数量分布", fontsize=16)
    plt.xlabel("区域", fontsize=14)
    plt.ylabel("订单数量", fontsize=14)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

## (2) 区内通勤和跨区通勤分布
def plot_commute_distribution(data):
    # 判断通勤类型
    data['通勤类型'] = data.apply(
        lambda row: "区内通勤" if row['起点所属区'] == row['终点所属区'] else "跨区通勤",
        axis=1
    )
    # 统计通勤类型数量
    commute_counts = data['通勤类型'].value_counts()

    # 绘制饼图
    commute_counts.plot(kind='pie', autopct='%1.1f%%', figsize=(8, 8), colors=['skyblue', 'lightcoral'])
    plt.title("区内通勤 vs 跨区通勤分布", fontsize=16)
    plt.ylabel("")
    plt.show()
    
from matplotlib.colors import LinearSegmentedColormap, PowerNorm
## (3) 区-区 OD 从高到低排名
def plot_od_ranking(data):
    # 统计 OD 区-区订单量
    od_counts = data.groupby(['起点所属区', '终点所属区']).size().reset_index(name='订单数量')

    # 按订单数量降序排序
    od_counts = od_counts.sort_values(by='订单数量', ascending=False)

    # 绘制热力图
    od_pivot = od_counts.pivot("起点所属区", "终点所属区", "订单数量")
    plt.figure(figsize=(12, 10))
    sns.heatmap(od_pivot, annot=True, fmt=".0f", cmap="YlGnBu", norm=PowerNorm(gamma=0.2), cbar_kws={'label': '订单数量'})
    plt.title("区-区 OD 订单分布热力图", fontsize=16)
    plt.xlabel("终点所属区", fontsize=14)
    plt.ylabel("起点所属区", fontsize=14)
    plt.tight_layout()
    plt.show()

import pandas as pd
import matplotlib.pyplot as plt

def plot_order_property_heatmap(data, start_column, end_column):
    """
    绘制订单起点和终点性质的热力图，并将数据标准化，使得最大值为 1。

    :param data: 包含订单数据的 DataFrame
    :param start_column: 起点性质列的名称
    :param end_column: 终点性质列的名称
    """
    # 统计每对起点和终点性质的订单数量
    pivot_table = pd.crosstab(data[start_column], data[end_column])

    # 标准化数据，将最大值调整为 1
    max_value = pivot_table.max().max()  # 获取整个数据表中的最大值
    pivot_table_normalized = pivot_table / max_value  # 所有数据除以最大值

    # 使用 seaborn 绘制热力图
    plt.figure(figsize=(10, 8))  # 设置图形的大小
    sns.heatmap(pivot_table_normalized, annot=True, cmap='seismic', fmt='.2f', linewidths=0.5)

    # 设置标题和标签
    plt.title(f'{start_column} 与 {end_column} 性质分布热力图 (标准化)', fontsize=16)
    plt.xlabel(end_column, fontsize=12)
    plt.ylabel(start_column, fontsize=12)

    # 显示图形
    plt.show()

# 调用函数绘制热力图（假设data为DataFrame）
# plot_order_property_heatmap(data, '订单起点性质', '订单终点性质'

def plot_order_property_heatmaps(data, start_column, end_column):
    """
    绘制不同时间段的订单起点和终点性质的热力图，展示早高峰、午间、晚高峰、夜间四个时间段。
    
    :param data: 包含订单数据的 DataFrame
    :param start_column: 起点性质列的名称
    :param end_column: 终点性质列的名称
    """
    # 确保接单时间字段是 datetime 类型
    data['接单时间'] = pd.to_datetime(data['接单时间'])

    # 提取小时字段
    data['hour'] = data['接单时间'].dt.hour

    # 筛选不同时间段的数据
    morning_rush = data[(data['hour'] >= 7) & (data['hour'] < 9)]  # 早高峰：7:00 - 9:00
    noon = data[(data['hour'] >= 11) & (data['hour'] < 13)]  # 午间：11:30 - 13:30
    evening_rush = data[(data['hour'] >= 17) & (data['hour'] < 19)]  # 晚高峰：17:00 - 19:00
    night = data[(data['hour'] >= 21) | (data['hour'] < 6)]  # 夜间：21:00 - 23:59 或 00:00 - 06:00

    # 设置 2x2 的子图布局
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))

    # 早高峰热力图
    ax1 = axes[0, 0]
    pivot_morning = pd.crosstab(morning_rush[start_column], morning_rush[end_column])
    pivot_morning_normalized = pivot_morning / pivot_morning.max().max()
    sns.heatmap(pivot_morning_normalized, annot=True, cmap='YlGnBu', fmt='.2f', ax=ax1, linewidths=0.5)
    ax1.set_title('早高峰 (7:00 - 9:00)')

    # 午间热力图
    ax2 = axes[0, 1]
    pivot_noon = pd.crosstab(noon[start_column], noon[end_column])
    pivot_noon_normalized = pivot_noon / pivot_noon.max().max()
    sns.heatmap(pivot_noon_normalized, annot=True, cmap='YlGnBu', fmt='.2f', ax=ax2, linewidths=0.5)
    ax2.set_title('午间 (11:30 - 13:30)')

    # 晚高峰热力图
    ax3 = axes[1, 0]
    pivot_evening = pd.crosstab(evening_rush[start_column], evening_rush[end_column])
    pivot_evening_normalized = pivot_evening / pivot_evening.max().max()
    sns.heatmap(pivot_evening_normalized, annot=True, cmap='YlGnBu', fmt='.2f', ax=ax3, linewidths=0.5)
    ax3.set_title('晚高峰 (17:00 - 19:00)')

    # 夜间热力图
    ax4 = axes[1, 1]
    pivot_night = pd.crosstab(night[start_column], night[end_column])
    pivot_night_normalized = pivot_night / pivot_night.max().max()
    sns.heatmap(pivot_night_normalized, annot=True, cmap='YlGnBu', fmt='.2f', ax=ax4, linewidths=0.5)
    ax4.set_title('夜间 (21:00 - 06:00)')

    # 调整图表间距
    plt.tight_layout()

    # 显示图形
    plt.show()

# 使用示例
# 假设 data 为 DataFrame
# plot_order_property_heatmaps(data, '订单起点性质', '订单终点性质')


# 调用函数绘制热力图（假设data为DataFrame）
# plot_order_property_heatmaps(data, '订单起点性质', '订单终点性质')


# 调用可视化函数
# plot_order_distribution(data)  # (1)
# plot_commute_distribution(data)  # (2)
plot_od_ranking(data)  # (3)
