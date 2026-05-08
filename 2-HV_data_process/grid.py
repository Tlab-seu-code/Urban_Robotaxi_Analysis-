# -*- coding: utf-8 -*-
"""
Created on Tue Mar 18 21:38:53 2025

@author: WuxiTlab
"""


# import os
# import pandas as pd
# from datetime import datetime, timedelta

# # 文件路径
# input_folder = 'input'
# output_folder = 'input_v2'

# # 确保输出文件夹存在
# os.makedirs(output_folder, exist_ok=True)

# # 分块大小
# chunksize = 100000  # 每批读取10万行

# # 最大连续时间限制
# max_duration = timedelta(hours=2)

# # 函数：处理一批数据
# def process_chunk(chunk, prev_tail):
#     """处理每个批次，并处理跨批次连续的state=1"""
#     chunk['time'] = pd.to_datetime(chunk['time'], format='%H:%M:%S')

#     # 合并上一批的尾部数据以防止跨批次连续
#     if prev_tail is not None:
#         chunk = pd.concat([prev_tail, chunk], ignore_index=True)

#     # 剔除state=1连续超过2小时的数据
#     drop_indices = []
#     start_time = None

#     for i in range(len(chunk)):
#         if chunk.at[i, 'state'] == 1:
#             if start_time is None:
#                 start_time = chunk.at[i, 'time']
#             elif chunk.at[i, 'time'] - start_time > max_duration:
#                 drop_indices.extend(range(i, len(chunk)))
#                 break
#         else:
#             start_time = None

#     # 清理数据
#     cleaned_chunk = chunk.drop(drop_indices)

#     # 返回清理后的数据和当前批次的尾部
#     return cleaned_chunk, chunk.tail(1)

# # 批量处理 CSV 文件
# for file_name in os.listdir(input_folder):
#     if file_name.endswith('.csv'):
#         input_file = os.path.join(input_folder, file_name)
#         output_file = os.path.join(output_folder, file_name)

#         print(f"🚀 处理文件：{file_name}")

#         prev_tail = None
#         first_write = True

#         with pd.read_csv(input_file, chunksize=chunksize) as reader:
#             for i, chunk in enumerate(reader):
#                 print(f"🛠️ 处理批次 {i + 1}")

#                 # 处理当前批次并返回尾部数据
#                 cleaned_chunk, prev_tail = process_chunk(chunk, prev_tail)

#                 # 将清理后的数据保存到新文件
#                 mode = 'w' if first_write else 'a'
#                 header = first_write
#                 cleaned_chunk.to_csv(output_file, index=False, encoding='utf-8-sig', mode=mode, header=header)
#                 first_write = False

#         print(f"✅ 清理完成：{output_file}")

# print("🎯 所有文件清理完成！")

# import os
# import pandas as pd
# from datetime import datetime, timedelta

# # 文件路径
# input_folder = 'input'
# output_folder = 'input_v2'

# # 确保输出文件夹存在
# os.makedirs(output_folder, exist_ok=True)

# # 最大连续时间限制
# max_duration = timedelta(hours=2)

# # 函数：处理单个文件
# def process_file(file_path, output_path):
#     """读取整个文件，处理连续state=1超过2小时的数据，标记为-1"""

#     print(f"🚀 正在处理：{file_path}")

#     # 读取数据
#     df = pd.read_csv(file_path)

#     # 将时间转换为时间戳
#     df['time'] = pd.to_datetime(df['time'], format='%H:%M:%S')

#     # 标记超过2小时的state=1为-1
#     start_time = None
#     state_one_indices = []

#     for i in range(len(df)):
#         if df.at[i, 'state'] == 1:
#             if start_time is None:
#                 start_time = df.at[i, 'time']
#                 state_one_indices = [i]
#             else:
#                 duration = df.at[i, 'time'] - start_time
#                 state_one_indices.append(i)

#                 # 如果连续时长超过2小时，标记为-1
#                 if duration > max_duration:
#                     df.loc[state_one_indices, 'state'] = -1
#         else:
#             start_time = None
#             state_one_indices = []

#     # 保存处理后的文件
#     df.to_csv(output_path, index=False, encoding='utf-8-sig')
#     print(f"✅ 处理完成：{output_path}")

# # 批量处理所有文件
# for file_name in os.listdir(input_folder):
#     if file_name.endswith('.csv'):
#         input_file = os.path.join(input_folder, file_name)
#         output_file = os.path.join(output_folder, file_name)

#         process_file(input_file, output_file)

# print("🎯 所有文件处理完成！")


# import os
# import pandas as pd

# # 文件路径
# input_folder = 'input_v3'   # 已清理的轨迹数据
# grid_folder = 'grid'        # 保存网格识别结果

# # 分块大小
# chunksize = 100000  # 每批读取10万行

# # 确保输出文件夹存在
# os.makedirs(grid_folder, exist_ok=True)

# # 网格边界信息和步长
# min_lon = 113.942617
# max_lon = 114.629031
# min_lat = 30.255898
# max_lat = 30.742468

# # 使用更精确的步长
# lon_step = 0.0103997242944
# lat_step = 0.0089831117499

# # 计算总行列数
# num_cols = int(round((max_lon - min_lon) / lon_step))
# num_rows = int(round((max_lat - min_lat) / lat_step))

# def get_grid_xy(lon, lat):
#     """计算经纬度对应的列(x)和行(y)"""

#     if pd.isna(lon) or pd.isna(lat):
#         return (-1, -1)
#     # 检查经纬度有效性
#     if not (min_lon <= lon < max_lon and min_lat <= lat < max_lat):
#         return (-1, -1)
    
#     # 计算列和行
#     x = int((lon - min_lon) / lon_step)
#     y = int((lat - min_lat) / lat_step)
    
#     # 边界检查
#     if x < 0 or x >= num_cols or y < 0 or y >= num_rows:
#         return (-1, -1)
    
#     return x, y

    
# def process_file(file_name):
#     input_file = os.path.join(input_folder, file_name)
#     output_file = os.path.join(grid_folder, file_name)

#     print(f"🚀 处理文件：{file_name}")

#     first_write = True

#     # 预计算有效范围边界
#     lon_valid_left = min_lon
#     lon_valid_right = max_lon - 1e-9  # 避免浮点误差导致越界
#     lat_valid_bottom = min_lat
#     lat_valid_top = max_lat - 1e-9

#     # 分批处理
#     with pd.read_csv(input_file, chunksize=chunksize) as reader:
#         for i, chunk in enumerate(reader):
#             print(f"🛠️ 处理批次 {i + 1}")
            
#             # 筛选有效数据
#             chunk = chunk[chunk['speed'] > 1].copy()
            
#             # 向量化计算
#             x = pd.Series(-1, index=chunk.index, dtype=int)
#             y = pd.Series(-1, index=chunk.index, dtype=int)
            
#             # 创建有效掩码
#             valid_mask = (
#                 (chunk['lon'] >= lon_valid_left) &
#                 (chunk['lon'] < lon_valid_right) &
#                 (chunk['lat'] >= lat_valid_bottom) &
#                 (chunk['lat'] < lat_valid_top)
#             )
            
#             # 向量化计算有效坐标
#             x_valid = ((chunk['lon'][valid_mask] - min_lon) // lon_step).astype(int)
#             y_valid = ((chunk['lat'][valid_mask] - min_lat) // lat_step).astype(int)
            
#             # 边界检查（防止浮点误差）
#             x_valid = x_valid.clip(0, num_cols-1)
#             y_valid = y_valid.clip(0, num_rows-1)
            
#             # 赋值
#             x[valid_mask] = x_valid
#             y[valid_mask] = y_valid
            
#             chunk['x'] = x
#             chunk['y'] = y

#             # 写入文件
#             mode = 'w' if first_write else 'a'
#             header = first_write
#             chunk.to_csv(output_file, index=False, encoding='utf-8-sig', 
#                         mode=mode, header=header)
#             first_write = False

#     print(f"✅ 处理完成：{output_file}")

# # 批量处理所有文件
# for file_name in os.listdir(input_folder):
#     if file_name.endswith('.csv'):
#         process_file(file_name)

# print("🎯 所有文件处理完成！")

import os
import pandas as pd
from datetime import datetime

# 文件路径
grid_folder = "grid"
output_folder = "grid_v4"
os.makedirs(output_folder, exist_ok=True)

def get_hour(time_str):
    """提取时间中的小时"""
    try:
        return datetime.strptime(time_str, "%H:%M:%S").hour*2 + datetime.strptime(time_str, "%H:%M:%S").minute // 30
    except:
        return None

def process_file(file_path):
    output_data = []

    chunk_size = 100000
    for batch_id, chunk in enumerate(pd.read_csv(file_path, chunksize=chunk_size)):
        print(f"🛠️ 处理批次 {batch_id + 1}")

        # 提取小时并过滤无效数据
        chunk["hour"] = chunk["time"].apply(get_hour)
        chunk = chunk[~chunk["hour"].isna()].copy()
        chunk["hour"] = chunk["hour"].astype(int)
        
        # 按坐标和时间分组
        grouped = chunk.groupby(["x", "y", "hour"])
        
        # 统计运行状态
        for (x, y, hour), group in grouped:
            total = len(group)
            running = (group["state"] == 1).sum()
            non_running = total - running
            
            if total > 0:
                ratio = round(non_running / total, 4)
            else:
                ratio = -1
                
            output_data.append({
                "x": x,
                "y": y,
                "hour": hour,
                "running": running,
                "non_running": non_running,
                "total": total,
                "non_run_ratio": ratio
            })

    if not output_data:
        return
    
    print("完成1")

    df = pd.DataFrame(output_data)
    
    print("完成2")
    
    # 合并相同坐标时间的统计数据
    df = df.groupby(["x", "y", "hour"], as_index=False).agg({
        "running": "sum",
        "non_running": "sum",
        "total": "sum"
    })
    
    print("完成3")
    
    # 计算最终比例
    df["non_run_ratio"] = df.apply(
        lambda row: round(row["non_running"] / row["total"], 4) if row["total"] > 0 else -1,
        axis=1
    )
    
    print("完成4")
    
    # 生成完整时空组合
    all_xy = df[["x", "y"]].drop_duplicates()
    # full_index = pd.MultiIndex.from_product(
    #     [all_xy["x"], all_xy["y"], range(24)],
    #     names=["x", "y", "hour"]
    # )
    
    print("完成5")
    
    # 重建索引补全缺失时段
    # df = df.set_index(["x", "y", "hour"])
    # df = df.reindex(full_index, fill_value=0).reset_index()
    
    print("完成6")
    
    # 处理全零记录的异常值
    zero_mask = (df["running"] == 0) & (df["non_running"] == 0)
    df.loc[zero_mask, "non_run_ratio"] = -1
    
    print("完成7")
    
    # 生成输出文件名
    base_name = os.path.basename(file_path)
    output_path = os.path.join(output_folder, f"hourly_{base_name}")
    
    print("完成")
    
    # 保存结果
    df[["x", "y", "hour", "running", "non_running", "total", "non_run_ratio"]].to_csv(
        output_path, index=False, encoding="utf-8-sig"
    )
    print(f"✅ 已生成：{output_path}")

# 处理所有文件
for file_name in os.listdir(grid_folder):
    if file_name.endswith(".csv"):
        process_file(os.path.join(grid_folder, file_name))

print("🎯 全量数据处理完成！")

# import pandas as pd
# import glob
# import os

# # 配置路径
# input_folder = 'grid_v3'
# output_file = 'consolidated_data.csv'

# # 合并所有文件
# all_files = glob.glob(os.path.join(input_folder, "hourly_*.csv"))
# combined_df = pd.concat((pd.read_csv(f) for f in all_files), ignore_index=True)

# # 按时空维度聚合数据
# agg_df = combined_df.groupby(['x', 'y', 'hour'], as_index=False).agg({
#     'running': 'sum',
#     'non_running': 'sum',
#     'total': 'sum'
# })

# # 重新计算非运行比例（保留原始异常标记）
# def calc_ratio(row):
#     if row['total'] > 0:
#         return round(row['non_running'] / row['total'], 4)
#     else:
#         return -1  # 保持原有异常值标记

# agg_df['non_run_ratio'] = agg_df.apply(calc_ratio, axis=1)

# # 按规范排序
# agg_df = agg_df.sort_values(['x', 'y', 'hour'])

# # 保存结果（包含标题）
# agg_df.to_csv(output_file, index=False, encoding='utf-8-sig')

# print(f"数据合并完成：{output_file}")
# print(f"总记录数：{len(agg_df)}")

# import os
# import pandas as pd
# from datetime import datetime

# # 文件路径
# grid_folder = "grid"
# output_folder = "grid_v2"
# os.makedirs(output_folder, exist_ok=True)

# # 时间段阈值
# time_ranges = {
#     "0": (7, 10),
#     "1": (10, 17),
#     "2": (17, 20),
#     "3": (20, 7)  # 跨天处理
# }

# # 将时间戳映射为时间段
# def get_time_period(time_str):
#     """将时间字符串映射到对应的时间段"""
#     time = datetime.strptime(time_str, "%H:%M:%S").time()
#     hour = time.hour

#     for period, (start, end) in time_ranges.items():
#         if start <= end:
#             if start <= hour < end:
#                 return period
#         else:
#             # 夜间跨天处理
#             if hour >= start or hour < end:
#                 return period
#     return None

# # 统计数据
# def process_file(file_path):
#     output_data = []

#     # 分块读取
#     chunk_size = 100000
#     for batch_id, chunk in enumerate(pd.read_csv(file_path, chunksize=chunk_size)):
#         print(f"🛠️ 处理批次 {batch_id + 1}")  # 打印批次编号
#         # 过滤掉时间不在指定范围的数据
#         chunk["time_period"] = chunk["time"].apply(get_time_period)
#         chunk = chunk.dropna(subset=["time_period"])
        
#         # 按网格和时间段分组
#         grouped = chunk.groupby(["grid", "time_period"])

#         # 统计帧数
#         for (grid_id, period), group in grouped:
#             total_frames = len(group)
#             running_frames = len(group[group["state"] == 1])
#             non_running_frames = total_frames - running_frames

#             if total_frames > 0:
#                 non_running_ratio = min(1,float(non_running_frames) / float(total_frames))
#             else:
#                 non_running_ratio = -1

#             output_data.append({
#                 "grid_id": grid_id,
#                 "time": period,
#                 "run": running_frames,
#                 "non_run": non_running_frames,
#                 "total": total_frames,
#                 "percentage": round(non_running_ratio, 4) if non_running_ratio >= 0 else -1
#             })

#     # 转换为DataFrame
#     df = pd.DataFrame(output_data)

#     # ✅ 合并重复组合，确保唯一性
#     df = df.groupby(["grid_id", "time"], as_index=False).sum()

#     # 补全所有时空组合
#     all_grids = pd.Series(df["grid_id"].unique(), name="grid_id")
#     all_periods = pd.Series(time_ranges.keys(), name="time")
#     full_index = pd.MultiIndex.from_product([all_grids, all_periods], names=["grid_id", "time"])

#     # 确保唯一性后再重建索引
#     df = df.set_index(["grid_id", "time"]).reindex(full_index, fill_value=0).reset_index()
    
#     # 将所有帧数均为0的占比设为-1
#     df.loc[(df["run"] == 0) & (df["non_run"] == 0), "percentage"] = -1


#     # 输出文件名
#     base_name = os.path.basename(file_path)
#     output_name = os.path.join(output_folder, f"summary_{base_name}")
    
#     # 保存
#     df.to_csv(output_name, index=False, encoding="utf-8-sig")
#     print(f"✅ 已处理：{output_name}")

# # 遍历所有网格文件
# for file_name in os.listdir(grid_folder):
#     if file_name.endswith(".csv"):
#         file_path = os.path.join(grid_folder, file_name)
#         process_file(file_path)

# print("🎯 所有网格数据处理完成！")




# import pandas as pd
# import os
# import numpy as np
# import matplotlib.pyplot as plt
# import seaborn as sns

# # 文件路径
# grid_folder = "./grid_v2"
# grid_map_file = "./grid_map.csv"
# output_file = "./merged_grid_data_with_latlon.csv"

# # 合并所有网格数据
# def merge_grid_files(folder, output_file):
#     all_files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".csv")]
#     df_list = []

#     for file in all_files:
#         df = pd.read_csv(file)
#         df = df[df['grid_id'] != -1]  # 剔除未识别数据
#         df_list.append(df)

#     merged_df = pd.concat(df_list, ignore_index=True)
#     merged_df.to_csv(output_file, index=False)
#     print(f"合并后的文件保存为：{output_file}")
#     return merged_df

# # 将网格编号映射为经纬度
# def map_grid_to_latlon(df, grid_map_file):
#     grid_map = pd.read_csv(grid_map_file)

#     # 计算中心点经纬度
#     grid_map['lon'] = (grid_map['起始经度'] + grid_map['终止经度']) / 2
#     grid_map['lat'] = (grid_map['起始纬度'] + grid_map['终止纬度']) / 2

#     # 映射经纬度
#     df = df.merge(grid_map[['网格编号', 'lon', 'lat']], left_on='grid_id', right_on='网格编号', how='left')
#     df.drop(columns=['网格编号'], inplace=True)

#     return df

# # 绘制热力图（修复纬度在x轴，经度在y轴）
# def plot_latlon_heatmap(df, value_col, title, cmap='plasma'):
#     plt.figure(figsize=(14, 12))

#     # 对数变换
#     df['log_value'] = np.log1p(df[value_col])

#     # 注意纬度在 x 轴，经度在 y 轴
#     sns.scatterplot(
#         x='lat',       # 纬度在x轴
#         y='lon',       # 经度在y轴
#         hue='log_value',
#         size='log_value',
#         palette=cmap,
#         sizes=(20, 200),
#         data=df
#     )

#     plt.title(title, fontsize=18, fontweight='bold', fontproperties='SimHei')  # 黑体
#     plt.xlabel("纬度", fontsize=14, fontproperties='SimHei')
#     plt.ylabel("经度", fontsize=14, fontproperties='SimHei')
#     plt.legend(title=value_col, loc='upper right')
#     plt.grid(True)
#     plt.show()

# # 主函数
# def main():
#     # 合并数据
#     merged_df = merge_grid_files(grid_folder, output_file)

#     # 映射经纬度
#     merged_df = map_grid_to_latlon(merged_df, grid_map_file)

#     # 绘制热力图
#     plot_latlon_heatmap(merged_df, 'run', '运行中车辆数量热力图（经纬度修复）', cmap='plasma')
#     plot_latlon_heatmap(merged_df, 'non_run', '非运行中车辆数量热力图（经纬度修复）', cmap='plasma')

# # 执行
# main()


# import pandas as pd
# import os
# import numpy as np
# import matplotlib.pyplot as plt
# import seaborn as sns

# # 文件路径
# grid_folder = "./grid_v2"
# grid_map_file = "./grid_map_with_xy.csv"
# output_file = "./merged_grid_data_with_xy.csv"

# # 合并所有网格数据
# def merge_grid_files(folder, output_file):
#     all_files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".csv")]
#     df_list = []

#     for file in all_files:
#         df = pd.read_csv(file)
#         df = df[df['grid_id'] != -1]  # 剔除未识别数据
#         df_list.append(df)

#     merged_df = pd.concat(df_list, ignore_index=True)
#     merged_df.to_csv(output_file, index=False)
#     print(f"合并后的文件保存为：{output_file}")
#     return merged_df

# # 将网格编号映射为 (x, y) 坐标
# def map_grid_to_xy(df, grid_map_file):
#     grid_map = pd.read_csv(grid_map_file)

#     # 映射 x 和 y
#     df = df.merge(grid_map[['网格编号', 'x', 'y']], left_on='grid_id', right_on='网格编号', how='left')
#     df.drop(columns=['网格编号'], inplace=True)

#     return df

# # 绘制热力图（基于x, y）
# def plot_xy_heatmap(df, value_col, title, cmap='plasma'):
#     plt.figure(figsize=(14, 12))

#     # 对数变换
#     df['log_value'] = np.log1p(df[value_col])

#     sns.scatterplot(
#         x='x',
#         y='y',
#         hue='log_value',
#         size='log_value',
#         palette=cmap,
#         sizes=(20, 200),
#         data=df
#     )

#     plt.title(title, fontsize=18, fontweight='bold', fontproperties='SimHei')  # 黑体
#     plt.xlabel("X 坐标", fontsize=14, fontproperties='SimHei')
#     plt.ylabel("Y 坐标", fontsize=14, fontproperties='SimHei')
#     plt.legend(title=value_col, loc='upper right')
#     plt.grid(True)
#     plt.show()

# # 主函数
# def main():
#     # 合并数据
#     merged_df = merge_grid_files(grid_folder, output_file)

#     # 映射 x, y 坐标
#     merged_df = map_grid_to_xy(merged_df, grid_map_file)

#     # 绘制热力图
#     plot_xy_heatmap(merged_df, 'run', '运行中车辆数量热力图（基于x, y）', cmap='plasma')
#     plot_xy_heatmap(merged_df, 'non_run', '非运行中车辆数量热力图（基于x, y）', cmap='plasma')

# # 执行
# main()
