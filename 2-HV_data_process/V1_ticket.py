# -*- coding: utf-8 -*-
"""
Created on Sun Jan 19 16:18:15 2025

@author: TLab
"""

# import pandas as pd

# # 读取大CSV文件的前100条数据
# file_path = 'tracks_with_distance.csv'  # 替换为你的文件路径
# df = pd.read_csv(file_path, nrows=100)

import pandas as pd

# 读取原始数据
file_path = 'input_v2\\20240709.csv'  # 替换为你的原始文件路径
df = pd.read_csv(file_path, chunksize=100000)

# 确保按车辆（id）排序（如果有需要，可以按时间排序）
df = df.sort_values(by=['id', 'time'])

# 获取前10辆车的ID
vehicle_ids = df['id'].unique()[:10]  # 只取前10辆车

# 筛选出前10辆车的数据
df_filtered = df[df['id'].isin(vehicle_ids)]

# 保存为新的CSV文件
output_file = '20240908_first_10_vehicles.csv'
df_filtered.to_csv(output_file, index=False)

print(f"前10辆车的原始数据已保存到 {output_file}")


# import pandas as pd

# # 读取大CSV文件
# file_path = 'tracks_with_distance.csv'  # 替换为你的文件路径
# df = pd.read_csv(file_path), nrows=1000000

# 过滤出id包含'test'的行
# filtered_df = df[df['id'].str.contains('鄂AXK858', case=False, na=False)]

# # 将过滤后的数据保存到新的CSV文件中
# output_file = 'filtered_test_data.csv'  # 输出文件名
# filtered_df.to_csv(output_file, index=False)

# print(f"包含'test'的id数据已保存到 {output_file}")
# import os
# import pandas as pd

# # 获取当前目录下的所有CSV文件
# input_dir = '.\\input_v3'  # 当前目录
# output_dir = '.\\order_v1'  # 输出文件夹
# if not os.path.exists(output_dir):
#     os.makedirs(output_dir)

# # 遍历目录下所有CSV文件
# for file_name in os.listdir(input_dir):
#     if file_name.endswith('.csv'):
#         file_path = os.path.join(input_dir, file_name)
        
#         # 读取车辆数据
#         print(f"Processing {file_name}...") 

#         # 读取文件
#         df = pd.read_csv(file_path)

#         # 获取日期部分
#         date_part = file_name.split('.')[0]

#         # 处理时间，添加日期部分
#         df['time'] = pd.to_datetime(date_part + ' ' + df['time'].astype(str), format='%Y%m%d %H:%M:%S')

#         # 确保按车辆（id）和时间（time）排序
#         df = df.sort_values(by=['id', 'time'])

#         # 订单列表
#         orders = []

#         # 获取所有车辆ID
#         vehicle_ids = df['id'].unique()

#         # 处理车辆数据并打印进度
#         total_vehicles = len(vehicle_ids)
#         for idx, vehicle_id in enumerate(vehicle_ids, start=1):
#             # 打印处理进度
#             print(f"  Processing vehicle {idx}/{total_vehicles} ({(idx / total_vehicles) * 100:.2f}%)")

#             # 按车辆分组
#             group = df[df['id'] == vehicle_id]

#             order_id = 1  # 订单编号从1开始，每辆车独立编号
#             order_start = None  # 订单起点
#             for i in range(len(group)):
#                 row = group.iloc[i]

#                 if row['state'] == 1:  # 找到订单起点
#                     if order_start is None:
#                         order_start = row  # 记录起点信息
#                         order_start_time = row['time']
#                         order_start_lon = row['lon']
#                         order_start_lat = row['lat']

#                 elif row['state'] == 0 and order_start is not None:  # 找到订单终点
#                     order_end = row
#                     order_end_time = row['time']
#                     order_end_lon = row['lon']
#                     order_end_lat = row['lat']

#                     # 计算持续时间等
#                     duration = (order_end_time - order_start_time).total_seconds()
#                     order_range = group[(group['time'] >= order_start_time) & (group['time'] <= order_end_time)]
#                     average_speed = order_range['speed'].mean()

#                     # 检查异常订单并跳过
#                     if average_speed < 1 or duration < 30:
#                         continue

#                     # 保存订单信息
#                     orders.append({
#                         'vehicle_id': vehicle_id,
#                         'order_id': f"{vehicle_id}_{order_id}",  # 使用车辆ID加上订单ID，确保每辆车订单唯一
#                         'start_time': order_start_time,
#                         'start_lon': order_start_lon,
#                         'start_lat': order_start_lat,
#                         'end_time': order_end_time,
#                         'end_lon': order_end_lon,
#                         'end_lat': order_end_lat,
#                         'average_speed': average_speed,
#                         'duration': duration  # 将持续时间转换为分钟
#                     })
#                     order_start = None  # 重置订单起点
#                     order_id += 1  # 增加订单编号（独立于车辆）

#         # 将所有提取的订单信息转换为DataFrame
#         orders_df = pd.DataFrame(orders)

#         # 保存订单信息到新的CSV文件
#         output_file = os.path.join(output_dir, f"{date_part}-orders_info.csv")
#         orders_df.to_csv(output_file, index=False)

#         print(f"  订单信息已保存到 {output_file}")

# print("所有文件处理完成！")



# import pandas as pd
# from datetime import datetime, timedelta
# # import geopy.distance

# # # 计算两个经纬度之间的距离（单位：米）
# # def calculate_distance(lon1, lat1, lon2, lat2):
# #     return geopy.distance.geodesic((lat1, lon1), (lat2, end_lon)).meters

# # 重新计算合并后的订单信息
# def recalculate_merged_order(order1, order2):
#     # 合并订单的开始时间为第一个订单的开始时间
#     start_time = order1['start_time']
    
#     # 合并订单的结束时间为第二个订单的结束时间
#     end_time = order2['end_time']
    
#     # 合并后的经纬度：简单计算两个订单的起点和终点之间的平均值
#     start_lon = order1['start_lon']
#     start_lat = order1['start_lat']
#     end_lon = order2['end_lon']
#     end_lat = order2['end_lat']
    
#     # 计算距离：起点和终点之间的距离
#     # distance = calculate_distance(start_lon, start_lat, end_lon, end_lat)
    
#     # 计算持续时间
#     duration = (end_time - start_time).total_seconds()
    
#     # 计算每个订单的持续时间
#     duration1 = (order1['end_time'] - order1['start_time']).total_seconds()
#     duration2 = (order2['end_time'] - order2['start_time']).total_seconds()
    
#     # 计算加权平均速度
#     weighted_average_speed = ((order1['average_speed'] * duration1) + (order2['average_speed'] * duration2)) / (duration1 + duration2) if (duration1 + duration2) > 0 else 0
    
#     return {
#         'vehicle_id': order1['vehicle_id'],
#         'order_id': f"{order1['order_id']}",
#         'start_time': start_time,
#         'start_lon': start_lon,
#         'start_lat': start_lat,
#         'end_time': end_time,
#         'end_lon': end_lon,
#         'end_lat': end_lat,
#         'average_speed': weighted_average_speed,
#         'duration': duration
#     }

# # 判断时间是否属于晚上（22:00 - 次日6:00）
# def is_night_time(order_time):
#     return order_time.hour >= 22 or order_time.hour < 6

# # 主处理函数
# def process_orders(input_file, output_file):
#     # 读取订单数据
#     df = pd.read_csv(input_file)
    
#     # 转换时间列为 datetime 类型
#     df['start_time'] = pd.to_datetime(df['start_time'])
#     df['end_time'] = pd.to_datetime(df['end_time'])
    
#     # 按车辆ID和开始时间排序
#     df = df.sort_values(by=['vehicle_id', 'start_time'])
    
#     # 结果列表
#     merged_orders = []
#     count = 0
#     # 用于存储每辆车合并后的订单
#     for vehicle_id, vehicle_orders in df.groupby('vehicle_id'):
#         count += 1
#         index = 0
#         total_orders = len(vehicle_orders)
#         previous_order = vehicle_orders.iloc[index]
#         if count % 1000 == 0:
#             print(count)
            
#         while index < total_orders - 1:
#             current_order = vehicle_orders.iloc[index + 1]
#             # 判断时间差
#             time_diff = (current_order['start_time'] - previous_order['end_time']).total_seconds()
            
#             # 判断是否在夜间时间段
#             if is_night_time(previous_order['end_time']) or is_night_time(current_order['start_time']):
#                 max_time_diff = 180  # 夜间允许的最大时间差
#             else:
#                 max_time_diff = 60  # 白天允许的最大时间差
            
#             # 如果时间差小于最大时间差，继续合并
#             if time_diff < max_time_diff:
#                 merged_order = recalculate_merged_order(previous_order, current_order)
#                 previous_order = pd.Series(merged_order)  # 更新为合并后的订单
#                 index += 1  # 不跳过，继续推进到下一个订单
#             else:
#                 # 否则将上一个合并的订单加入结果
#                 merged_orders.append(previous_order.to_dict())
#                 previous_order = current_order  # 更新为当前订单
#                 index += 1  # 推进到下一个订单
        
#         # 最后将剩余的订单（即未被合并的最后一个订单）加入结果
#         merged_orders.append(previous_order.to_dict())
    
#     # 转换为 DataFrame
#     merged_df = pd.DataFrame(merged_orders)
    
#     # 过滤掉平均速度小于1 m/s的订单
#     merged_df = merged_df[merged_df['average_speed'] >= 1]
    
#     # 保存结果到文件
#     merged_df.to_csv(output_file, index=False)
#     print(f"处理完成！结果已保存到 {output_file}")

# import os
# from glob import glob
# # 文件夹路径
# input_folder = "output"
# output_folder = "order_output"

# # 确保输出文件夹存在
# os.makedirs(output_folder, exist_ok=True)

# # 处理所有 CSV 文件
# csv_files = glob(os.path.join(input_folder, "*.csv"))

# for input_file in csv_files:
#     output_file = os.path.join(output_folder, os.path.basename(input_file))  # 生成输出文件路径
#     process_orders(input_file, output_file)

