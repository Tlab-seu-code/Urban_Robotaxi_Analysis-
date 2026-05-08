# # -*- coding: utf-8 -*-
# """
# Created on Fri Feb 14 16:19:42 2025

# @author: WuxiTlab
# """
# import os
# import pandas as pd
# import math

# # def calculate_distance_wuhan(start_lon, start_lat, end_lon, end_lat):
# #     """
# #     计算武汉地区两点间的直线距离（平面近似法）
    
# #     参数:
# #     start_lon (float): 起点经度
# #     start_lat (float): 起点纬度
# #     end_lon (float): 终点经度
# #     end_lat (float): 终点纬度
    
# #     返回:
# #     float: 距离（米）
# #     """
# #     meters_per_degree_lat = 111195
# #     meters_per_degree_lon = 95729.96198684213
    
# #     delta_lat = end_lat - start_lat
# #     delta_lon = end_lon - start_lon
    
# #     distance_lat = delta_lat * meters_per_degree_lat
# #     distance_lon = delta_lon * meters_per_degree_lon
    
# #     return round(math.hypot(distance_lon, distance_lat),2)

# # def add_distance_to_tracks(track_csv_path, output_csv_path):
# #     # 读取轨迹CSV
# #     tracks_df = pd.read_csv(track_csv_path)
    
# #     # 将轨迹数据转化为NumPy数组（加速后续操作）
# #     tracks_array = tracks_df.to_numpy()

# #     # 创建一个新的列表来存储每辆车的距离
# #     result_data = []

# #     # 初始化当前车辆ID和上一个轨迹点的位置
# #     current_vehicle_id = None
# #     last_lon = None
# #     last_lat = None
# #     count = 0

# #     # 遍历轨迹数据
# #     for row in tracks_array:
# #         vehicle_id = row[0]
# #         lon = row[2]
# #         lat = row[3]

# #         if vehicle_id != current_vehicle_id:
# #             count += 1
# #             if count % 100 == 0:
# #                 print(f"{count}: {vehicle_id}")
# #             current_vehicle_id = vehicle_id
# #             last_lon = lon
# #             last_lat = lat
# #             distance = 0  # 第一个轨迹点的距离为0
# #         else:
# #             distance = calculate_distance_wuhan(last_lon, last_lat, lon, lat)
# #             last_lon = lon
# #             last_lat = lat

# #         row_with_distance = list(row) + [distance]  # 添加距离列
# #         result_data.append(row_with_distance)

# #     # 创建新的DataFrame并保存到CSV
# #     columns = tracks_df.columns.tolist() + ['distance']
# #     result_df = pd.DataFrame(result_data, columns=columns)
# #     result_df.to_csv(output_csv_path, index=False)

# #     print(f"处理完成，结果已保存到 {output_csv_path}")

# # def process_all_files(input_folder, output_folder):
# #     # 遍历input文件夹下的所有CSV文件
# #     for file_name in os.listdir(input_folder):
# #         if file_name.endswith(".csv"):
# #             input_csv_path = os.path.join(input_folder, file_name)
# #             output_csv_path = os.path.join(output_folder, f"distance_{file_name}")
            
# #             print(f"正在处理文件: {file_name}")
# #             add_distance_to_tracks(input_csv_path, output_csv_path)
# #             print(f"{file_name} 处理完毕，已保存到 {output_csv_path}")

# # # 设置输入输出文件夹路径
# # input_folder = 'input'
# # output_folder = 'output_distance'

# # # 确保输出文件夹存在
# # os.makedirs(output_folder, exist_ok=True)

# # # 批量处理文件
# # process_all_files(input_folder, output_folder)

# import pandas as pd
# import numpy as np
# from datetime import datetime
# import os

# def process_orders(orders_file, trajectories_file, output_file):
#     # 读取订单数据并转换时间格式
#     orders = pd.read_csv(
#         orders_file,
#         parse_dates=['start_time', 'end_time'],
#         date_format='%Y-%m-%d %H:%M:%S'
#     )
    
#     # 预处理轨迹数据（使用chunksize处理大文件）
#     traj_cache = {}
#     for chunk in pd.read_csv(
#         trajectories_file,
#         chunksize=100000,
#         parse_dates=['time'],
#         date_format='%H:%M:%S'
#     ):
#         # 转换时间为秒数
#         chunk['time_seconds'] = chunk['time'].dt.hour * 3600 + \
#                                chunk['time'].dt.minute * 60 + \
#                                chunk['time'].dt.second
        
#         # 按车辆ID分组处理
#         for vehicle_id, group in chunk.groupby('id'):
#             group = group.sort_values('time_seconds')
#             if vehicle_id not in traj_cache:
#                 traj_cache[vehicle_id] = {
#                     'times': group['time_seconds'].to_numpy(),
#                     'distances': group['distance'].to_numpy()
#                 }
#             else:
#                 traj_cache[vehicle_id]['times'] = np.concatenate([
#                     traj_cache[vehicle_id]['times'],
#                     group['time_seconds'].to_numpy()
#                 ])
#                 traj_cache[vehicle_id]['distances'] = np.concatenate([
#                     traj_cache[vehicle_id]['distances'],
#                     group['distance'].to_numpy()
#                 ])

#     # 按车辆ID分组处理订单
#     all_dfs = []
#     total_vehicles = orders['vehicle_id'].nunique()
#     processed = 0

#     for vehicle_id, group in orders.groupby('vehicle_id'):
#         processed += 1
#         # 获取对应轨迹数据
#         if vehicle_id in traj_cache:
#             times = traj_cache[vehicle_id]['times']
#             distances = traj_cache[vehicle_id]['distances']
#         else:
#             times = np.array([])
#             distances = np.array([])

#         # 处理每个订单
#         travel_lengths = []
#         for _, row in group.iterrows():
#             start = row['start_time']
#             end = row['end_time']
            
#             # 计算时间秒数
#             start_sec = start.hour * 3600 + start.minute * 60 + start.second
#             end_sec = end.hour * 3600 + end.minute * 60 + end.second

#             # 使用二分查找加速
#             if len(times) > 0:
#                 left = np.searchsorted(times, start_sec, side='left')
#                 right = np.searchsorted(times, end_sec, side='right')
#                 travel_length = distances[left:right].sum()
#             else:
#                 travel_length = 0.0

#             travel_lengths.append(travel_length)

#         # 添加新字段
#         group = group.copy()
#         group['travel_length'] = travel_lengths
#         all_dfs.append(group)

#         # 打印进度
#         print(f"已处理车辆 {vehicle_id} ({processed}/{total_vehicles})")

#     # 合并结果并保存
#     final_df = pd.concat(all_dfs)
#     final_df.to_csv(output_file, index=False)
#     print(f"处理完成，结果已保存至 {os.path.abspath(output_file)}")

# # 使用示例
# process_orders('orders.csv', 'trajectories.csv', 'output_orders.csv')

import os
import pandas as pd
import numpy as np
from datetime import datetime

def process_orders(orders_file, trajectories_file, output_file):
    # 读取订单数据
    orders = pd.read_csv(orders_file)
    
    # 手动解析日期列
    orders['start_time'] = pd.to_datetime(orders['start_time'], format='%Y-%m-%d %H:%M:%S')
    orders['end_time'] = pd.to_datetime(orders['end_time'], format='%Y-%m-%d %H:%M:%S')
    
    # 预处理轨迹数据（使用chunksize处理大文件）
    traj_cache = {}
    for chunk in pd.read_csv(trajectories_file, chunksize=100000):
        # 手动解析时间列
        chunk['time'] = pd.to_datetime(chunk['time'], format='%H:%M:%S')
        
        # 转换时间为秒数
        chunk['time_seconds'] = chunk['time'].dt.hour * 3600 + \
                               chunk['time'].dt.minute * 60 + \
                               chunk['time'].dt.second
        
        # 按车辆ID分组处理
        for vehicle_id, group in chunk.groupby('id'):
            group = group.sort_values('time_seconds')
            if vehicle_id not in traj_cache:
                traj_cache[vehicle_id] = {
                    'times': group['time_seconds'].to_numpy(),
                    'distances': group['distance'].to_numpy()
                }
            else:
                traj_cache[vehicle_id]['times'] = np.concatenate([
                    traj_cache[vehicle_id]['times'],
                    group['time_seconds'].to_numpy()
                ])
                traj_cache[vehicle_id]['distances'] = np.concatenate([
                    traj_cache[vehicle_id]['distances'],
                    group['distance'].to_numpy()
                ])

    # 按车辆ID分组处理订单
    all_dfs = []
    total_vehicles = orders['vehicle_id'].nunique()
    processed = 0

    for vehicle_id, group in orders.groupby('vehicle_id'):
        processed += 1
        # 获取对应轨迹数据
        if vehicle_id in traj_cache:
            times = traj_cache[vehicle_id]['times']
            distances = traj_cache[vehicle_id]['distances']
        else:
            times = np.array([])
            distances = np.array([])

        # 处理每个订单
        travel_lengths = []
        for _, row in group.iterrows():
            start = row['start_time']
            end = row['end_time']
            
            # 计算时间秒数
            start_sec = start.hour * 3600 + start.minute * 60 + start.second
            end_sec = end.hour * 3600 + end.minute * 60 + end.second

            # 使用二分查找加速
            if len(times) > 0:
                left = np.searchsorted(times, start_sec, side='left')
                right = np.searchsorted(times, end_sec, side='right')
                travel_length = distances[left:right].sum()
            else:
                travel_length = 0.0

            travel_lengths.append(travel_length)

        # 添加新字段
        group = group.copy()
        group['travel_length'] = travel_lengths
        all_dfs.append(group)

        # 打印进度
        print(f"已处理车辆 {vehicle_id} ({processed}/{total_vehicles})")

    # 合并结果并保存
    final_df = pd.concat(all_dfs)
    final_df.to_csv(output_file, index=False)
    print(f"处理完成，结果已保存至 {os.path.abspath(output_file)}")


def batch_process_orders(order_folder, trajectory_folder, output_folder):
    # 确保输出文件夹存在
    os.makedirs(output_folder, exist_ok=True)
    
    # 遍历order文件夹中的所有文件
    for order_file in os.listdir(order_folder):
        if order_file.endswith('.csv'):
            # 解析文件名中的日期
            try:
                date_str = order_file.split('-')[0]  # 假设文件名格式为20240708-orders_info.csv
                order_date = datetime.strptime(date_str, '%Y%m%d').date()
            except ValueError:
                print(f"文件名格式错误，跳过文件: {order_file}")
                continue
            
            # 构建轨迹文件路径
            trajectory_file = os.path.join(
                trajectory_folder,
                f'distance_{order_date.strftime("%Y%m%d")}.csv'
            )
            
            # 检查轨迹文件是否存在
            if not os.path.exists(trajectory_file):
                print(f"未找到对应的轨迹文件: {trajectory_file}")
                continue
            
            # 构建输出文件路径
            output_file = os.path.join(
                output_folder,
                f'{order_date.strftime("%Y%m%d")}_orders_with_length.csv'
            )
            
            # 处理单个订单文件
            print(f"开始处理订单文件: {order_file}")
            process_orders(
                os.path.join(order_folder, order_file),
                trajectory_file,
                output_file
            )
            print(f"完成处理订单文件: {order_file}")

# 使用示例
batch_process_orders(
    order_folder='order_output',
    trajectory_folder='output_distance',
    output_folder='length_output'
)