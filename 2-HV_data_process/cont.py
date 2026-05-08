# -*- coding: utf-8 -*-
"""
Created on Sun Feb  9 15:00:00 2025

@author: WuxiTlab
"""

# import os
# import pandas as pd
# from glob import glob

# # 设定文件夹路径
# input_folder = "order_output"
# output_file = "merged_output.csv"

# # 获取所有 CSV 文件
# csv_files = glob(os.path.join(input_folder, "*.csv"))

# # 读取并合并所有 CSV 文件
# df_list = []
# for file in csv_files:
#     df = pd.read_csv(file)
#     df_list.append(df)

# # 合并所有数据
# merged_df = pd.concat(df_list, ignore_index=True)

# # 对 order_id 进行重新编号，确保唯一性
# merged_df["order_id"] = merged_df.groupby("vehicle_id").cumcount() + 1
# merged_df["order_id"] = merged_df["vehicle_id"] + "_" + merged_df["order_id"].astype(str)

# # 保存合并后的 CSV 文件
# merged_df.to_csv(output_file, index=False)

# # 返回合并文件的前几行以检查
# merged_df.head()

# import os
# import pandas as pd
# import matplotlib.pyplot as plt

# # 文件路径
# input_folder = 'length_output'
# output_file = 'order_v11.csv'

# # 最大持续时间（秒）
# max_duration = 7200

# # 合并所有CSV文件
# def merge_csv_files(folder):
#     """合并文件夹下所有CSV为一个DataFrame"""
#     all_data = []
    
#     for file_name in os.listdir(folder):
#         if file_name.endswith('.csv'):
#             file_path = os.path.join(folder, file_name)
#             print(f"📄 合并文件：{file_name}")
            
#             # 读取CSV文件
#             df = pd.read_csv(file_path)
            
#             # 收集数据
#             all_data.append(df)
    
#     # 合并为一个DataFrame
#     merged_df = pd.concat(all_data, ignore_index=True)
#     print(f"✅ 合并完成，共 {len(merged_df)} 条记录")
    
#     return merged_df

# # 清洗数据
# def clean_data(df):
#     """清理订单数据，去除持续时间超过2小时的订单"""
    
#     # 筛选duration在2小时内的订单
#     cleaned_df = df[df['duration'] <= max_duration].copy()
#     cleaned_df = cleaned_df[cleaned_df['travel_length'] <= 100_000]
    
#     print(f"🛠️ 清理完成：{len(cleaned_df)} 条记录保留（去除了超过2小时的订单）")
    
#     return cleaned_df

# # 绘制订单分布图（黑体显示）
# def plot_distribution(df):
#     """绘制订单的持续时间和距离分布图（黑体）"""
    
#     plt.rcParams['font.family'] = 'SimHei'  # 设置黑体字体（SimHei适用于Windows）

#     fig, axes = plt.subplots(1, 2, figsize=(14, 6))

#     # 持续时间分布
#     axes[0].hist(df['duration'] / 60, bins=50, color='skyblue', edgecolor='black')
#     axes[0].set_title('订单持续时间分布', fontsize=14, fontweight='bold')
#     axes[0].set_xlabel('持续时间 (分钟)', fontsize=12, fontweight='bold')
#     axes[0].set_ylabel('订单数量', fontsize=12, fontweight='bold')

#     # 距离分布
#     axes[1].hist(df['travel_length'] / 1000, bins=50, color='lightgreen', edgecolor='black')
#     axes[1].set_title('订单距离分布', fontsize=14, fontweight='bold')
#     axes[1].set_xlabel('距离 (公里)', fontsize=12, fontweight='bold')
#     axes[1].set_ylabel('订单数量', fontsize=12, fontweight='bold')

#     plt.tight_layout()
#     plt.show()

# # 主程序
# # 1. 合并所有CSV
# merged_df = merge_csv_files(input_folder)

# # 2. 数据清理
# cleaned_df = clean_data(merged_df)

# # 3. 保存结果
# cleaned_df.to_csv(output_file, index=False, encoding='utf-8-sig')
# print(f"✅ 清理后的数据保存为：{output_file}")

# # 4. 绘制分布图（黑体显示）
# plot_distribution(cleaned_df)
import pandas as pd
import os
from datetime import datetime

# 文件路径
input_folder = './input'
order_folder = './order_output'
output_folder = './input_v2'
os.makedirs(output_folder, exist_ok=True)

# 分块大小
CHUNKSIZE = 100000
DURATION_THRESHOLD = 2 * 3600  # 2小时阈值（秒）

def load_long_orders(order_path):
    """加载订单信息并筛选出大于2小时的订单，返回时间戳范围"""
    orders = pd.read_csv(order_path)

    # 检查字段
    required_cols = {'vehicle_id', 'order_id', 'start_time', 'end_time', 'duration'}
    if not required_cols.issubset(orders.columns):
        print(f"字段缺失，跳过：{order_path}")
        return {}

    # 筛选大于2小时的订单
    long_orders = orders[orders['duration'] > DURATION_THRESHOLD].copy()

    # 将时间字段转为时间戳，方便比对
    long_orders['start_time'] = pd.to_datetime(long_orders['start_time']).dt.time
    long_orders['end_time'] = pd.to_datetime(long_orders['end_time']).dt.time

    # 转换为时间范围集合（字典形式）
    order_ranges = {}
    for _, row in long_orders.iterrows():
        vehicle_id = row['vehicle_id']
        start_time = row['start_time']
        end_time = row['end_time']

        if vehicle_id not in order_ranges:
            order_ranges[vehicle_id] = []
        
        order_ranges[vehicle_id].append((start_time, end_time))

    return order_ranges


def clean_chunk(chunk, long_orders):
    """处理数据块，删除大于2小时订单的时间段"""
    chunk['time'] = pd.to_datetime(chunk['time'], format='%H:%M:%S').dt.time

    original_size = len(chunk)  # 记录原始条数
    cleaned_chunks = []
    
    # 按车辆分组处理
    for vehicle_id, group in chunk.groupby('id'):
        if vehicle_id in long_orders:
            for start_time, end_time in long_orders[vehicle_id]:
                group = group[~((group['time'] >= start_time) & (group['time'] <= end_time))]

        cleaned_chunks.append(group)

    cleaned_chunk = pd.concat(cleaned_chunks, ignore_index=True) if cleaned_chunks else pd.DataFrame()
    cleaned_size = len(cleaned_chunk)

    return cleaned_chunk, original_size, cleaned_size


def process_large_file(traj_path, order_path, output_path):
    """处理大文件，分块读取与清理，并输出条数变化"""
    
    # 加载大于2小时订单
    long_orders = load_long_orders(order_path)
    
    if not long_orders:
        print(f"无大于2小时的订单，直接复制文件：{output_path}")
        pd.read_csv(traj_path).to_csv(output_path, index=False)
        return
    
    # 处理分块
    total_chunks = 0
    total_original = 0
    total_cleaned = 0
    cleaned_chunks = []

    print(f"🚀 开始处理文件：{traj_path}，分块大小：{CHUNKSIZE}")
    
    # 逐块读取和清理
    for idx, chunk in enumerate(pd.read_csv(traj_path, chunksize=CHUNKSIZE), start=1):
        cleaned_chunk, original_size, cleaned_size = clean_chunk(chunk, long_orders)
        
        # 记录统计信息
        total_original += original_size
        total_cleaned += cleaned_size

        print(f"🔹 分块 {idx}：原始 {original_size} 条 → 清理后 {cleaned_size} 条，减少 {original_size - cleaned_size} 条")

        # 将结果保存到临时列表
        cleaned_chunks.append(cleaned_chunk)
        total_chunks += 1

        # 定期写入并清空内存
        if len(cleaned_chunks) >= 10:  # 每处理10个块写入一次
            pd.concat(cleaned_chunks, ignore_index=True).to_csv(output_path, mode='a', index=False, header=not os.path.exists(output_path))
            cleaned_chunks.clear()

    # 写入剩余数据
    if cleaned_chunks:
        pd.concat(cleaned_chunks, ignore_index=True).to_csv(output_path, mode='a', index=False, header=not os.path.exists(output_path))

    # 输出整体统计信息
    print(f"✅ 文件处理完成：{output_path}")
    print(f"📊 总分块数：{total_chunks}")
    print(f"📥 总读取条数：{total_original}")
    print(f"📤 总清理后条数：{total_cleaned}")
    print(f"🔥 总减少条数：{total_original - total_cleaned}\n")


# 批量处理所有CSV文件
for traj_file in os.listdir(input_folder):
    if traj_file.endswith('.csv'):
        date_str = traj_file.split('.')[0]

        # 对应订单文件
        order_file = f"{date_str}-orders_info.csv"
        order_path = os.path.join(order_folder, order_file)

        if os.path.exists(order_path):
            traj_path = os.path.join(input_folder, traj_file)
            output_path = os.path.join(output_folder, traj_file)

            process_large_file(traj_path, order_path, output_path)
        else:
            print(f"⚠️ 未找到对应订单文件：{order_path}")

print("🚀 所有文件处理完成！")
