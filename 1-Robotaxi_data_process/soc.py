# -*- coding: utf-8 -*-
"""
Created on Tue Mar 18 16:57:07 2025

@author: TLab
"""

import pandas as pd

# 读取数据
file = "v3-districts.csv"
df = pd.read_csv(file)

# 筛选所需列
selected_cols = ['订单号', '呼单起点', '呼单终点', '订单起点性质', '订单终点性质']
filtered_df = df[selected_cols]

# 保存为新的CSV文件
output_file = "tag_v0.csv"
filtered_df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"筛选后的数据已保存为 {output_file}")


# import pandas as pd

# 读取数据
# v4_file = 'v5-charged.csv'#'v4-districts-with-price.csv'
# charge_file = 'charge.csv'

# # 读取订单数据和充电数据
# v4_df = pd.read_csv(v4_file)
# charge_df = pd.read_csv(charge_file)

# # 将时间字段转换为 datetime 格式，便于排序和计算
# v4_df['接单时间'] = pd.to_datetime(v4_df['接单时间'])
# charge_df['充电开始时间'] = pd.to_datetime(charge_df['充电开始时间'])
# charge_df['充电结束时间'] = pd.to_datetime(charge_df['充电结束时间'])

# # 增加电量列
# v4_df['开始电量'] = -1.0
# v4_df['结束电量'] = -1.0

# print(0)

# # 将充电电量信息映射到订单数据
# for _, row in charge_df.iterrows():
#     vehicle_id = row['车辆ID']
#     start_order_id = row['开始订单id']
#     end_order_id = row['结束订单id']
#     start_charge = row['充点前电量']
#     end_charge = row['充点后电量']
    
#     # 匹配订单表中的充电订单
#     # 定义匹配条件
#     mask = v4_df['订单号'] == start_order_id
    
#     # 检查是否存在匹配订单
#     if not mask.any():
#         print(f"警告：未匹配到订单号 {start_order_id}，请检查数据完整性")
#     else:
#         # 存在匹配时处理结束电量逻辑
#         if pd.isna(end_charge):  # 检查是否为NaN（空值）
#             print(f"订单 {start_order_id} 结束电量为空，自动同步开始电量值")
#             end_charge = start_charge  # 用开始电量填充结束电量
        
#         # 更新匹配行的电量数据
#         v4_df.loc[mask, ['开始电量', '结束电量']] = [start_charge, end_charge]

#     print(_)

# print(1)

# 将取消订单的电量设置为 -1
# v4_df.loc[v4_df['订单状态'] == '取消', ['开始电量', '结束电量']] = -2

# # output_file = 'v5-charged.csv'
# # v4_df.to_csv(output_file, index=False, encoding='utf-8-sig')

# # 重新按车辆进行电量插值，仅对非取消订单处理
# def interpolate_battery_exclude_canceled(group):
#     # 先按时间排序，保证顺序正确
#     group = group.sort_values('接单时间').reset_index(drop=True)
#     print(group['车辆id'])
#     # 分离取消订单
#     canceled_orders = group[group['订单状态'] == '取消']
#     valid_orders = group[group['订单状态'] != '取消'].copy()

#     # 重置索引以避免索引不连续的问题
#     original_index = valid_orders.index
#     valid_orders = valid_orders.reset_index(drop=True)

#     # 插值处理
#     known_battery = valid_orders[(valid_orders['开始电量'] != -1) | (valid_orders['结束电量'] != -1)]

#     if len(known_battery) >= 2:
#         for i in range(len(known_battery) - 1):
#             start_idx = known_battery.index[i]
#             end_idx = known_battery.index[i + 1]

#             start_battery = valid_orders.loc[start_idx, '结束电量']
#             end_battery = valid_orders.loc[end_idx, '开始电量']

#             if pd.notna(start_battery) and pd.notna(end_battery) and start_battery != -1 and end_battery != -1:
#                 # 线性插值计算
#                 total_distance = valid_orders.loc[start_idx:end_idx, '行程里程'].sum() + \
#                                  valid_orders.loc[start_idx:end_idx, '接驾里程'].sum()

#                 if total_distance > 0:
#                     pre_battery = start_battery
#                     for j in range(start_idx + 1, end_idx):
#                         current_distance = valid_orders.loc[start_idx:j, '行程里程'].sum() + \
#                                            valid_orders.loc[start_idx:j, '接驾里程'].sum()

#                         battery = start_battery + (end_battery - start_battery) * (current_distance / total_distance)
#                         valid_orders.at[j, '开始电量'] = pre_battery
#                         valid_orders.at[j, '结束电量'] = battery
#                         pre_battery = battery

#     # 将插值结果映射回原索引
#     valid_orders.index = original_index

#     # 合并取消订单和插值订单
#     result = pd.concat([valid_orders, canceled_orders]).sort_index()
#     return result

# # 重新按车辆分组插值
# v4_df = v4_df.groupby('车辆id', group_keys=False).apply(interpolate_battery_exclude_canceled)

# # 保存结果
# output_file = 'v6-districts-with-price-charged.csv'
# # v4_df.to_csv(output_file, index=False, encoding='utf-8-sig')

# import pandas as pd
# import matplotlib.pyplot as plt
# import seaborn as sns
# import matplotlib.font_manager as fm

# # 设置黑体字体
# plt.rcParams['font.sans-serif'] = ['SimHei']
# plt.rcParams['axes.unicode_minus'] = False

# # 读取数据
# file = "v6-districts-with-price-charged.csv"
# df = pd.read_csv(file)

# # 过滤掉状态为取消的订单
# df = df[df['订单状态'] != '取消']

# # 转换电量为数值型
# df['开始电量'] = pd.to_numeric(df['开始电量'], errors='coerce')
# df['结束电量'] = pd.to_numeric(df['结束电量'], errors='coerce')

# # ==========================
# # Part 1: 开始电量与结束电量分布
# # ==========================
# fig, ax = plt.subplots(1, 2, figsize=(14, 6))

# sns.histplot(df['开始电量'], bins=20, kde=True, color='blue', ax=ax[0])
# ax[0].set_title('开始电量分布')
# ax[0].set_xlabel('电量(%)')
# ax[0].set_ylabel('订单数量')

# sns.histplot(df['结束电量'], bins=20, kde=True, color='green', ax=ax[1])
# ax[1].set_title('结束电量分布')
# ax[1].set_xlabel('电量(%)')
# ax[1].set_ylabel('订单数量')

# plt.tight_layout()
# plt.show()

# # ==========================
# # Part 2: 按订单类型绘制开始电量范围折线图
# # ==========================
# # 定义订单类型
# charge_orders = df[df['订单来源'] == '充电单']
# dispatch_orders = df[df['订单来源'] == '调度单']
# passenger_orders = df[~df['订单来源'].isin(['充电单', '调度单'])]

# # 电量分区（按10%区间）
# def group_by_range(data, col='开始电量'):
#     bins = list(range(0, 110, 10))
#     labels = [f"{i}-{i+10}%" for i in bins[:-1]]
#     data['电量区间'] = pd.cut(data[col], bins=bins, labels=labels, right=False)
#     return data.groupby('电量区间').size()

# # 统计数据
# charge_counts = group_by_range(charge_orders)
# dispatch_counts = group_by_range(dispatch_orders)
# passenger_counts = group_by_range(passenger_orders)

# # 绘图
# fig, ax = plt.subplots(figsize=(12, 6))

# ax.plot(charge_counts.index, charge_counts.values, marker='o', label='充电单', color='blue')
# ax.plot(dispatch_counts.index, dispatch_counts.values, marker='o', label='调度单', color='orange')
# ax.plot(passenger_counts.index, passenger_counts.values, marker='o', label='乘客单', color='green')

# ax.set_title('不同订单类型的开始电量分布')
# ax.set_xlabel('电量区间')
# ax.set_ylabel('订单数量')
# ax.legend()

# plt.xticks(rotation=45)
# plt.grid(True)
# plt.tight_layout()
# plt.show()


