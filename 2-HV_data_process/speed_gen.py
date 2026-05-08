# -*- coding: utf-8 -*-
"""
Created on Tue Mar 18 14:16:34 2025

@author: WuxiTlab
"""

# import os
# import pandas as pd

# # 文件路径
# input_folder = 'input_v2'
# output_folder = 'input_v3'

# # 确保输出文件夹存在
# os.makedirs(output_folder, exist_ok=True)

# # 分块大小
# chunksize = 100000  # 每批读取10万行

# # 速度范围限制
# min_speed = 0          # 最小速度限制（低速异常）
# max_speed = 150        # 最大速度限制（高速异常）

# # 函数：清洗速度异常值
# def clean_speed(chunk):
#     """剔除速度异常值"""
#     valid_chunk = chunk[(chunk['speed'] >= min_speed) & (chunk['speed'] <= max_speed)]
#     return valid_chunk

# # 批量处理 CSV 文件
# for file_name in os.listdir(input_folder):
#     if file_name.endswith('.csv'):
#         input_file = os.path.join(input_folder, file_name)
#         output_file = os.path.join(output_folder, file_name)

#         print(f"🚀 正在清洗文件：{file_name}")

#         first_write = True

#         with pd.read_csv(input_file, chunksize=chunksize) as reader:
#             for i, chunk in enumerate(reader):
#                 print(f"🛠️ 处理批次 {i + 1}")

#                 # 清洗速度异常值
#                 cleaned_chunk = clean_speed(chunk)

#                 # 将清理后的数据保存到新文件
#                 mode = 'w' if first_write else 'a'
#                 header = first_write
#                 cleaned_chunk.to_csv(output_file, index=False, encoding='utf-8-sig', mode=mode, header=header)
#                 first_write = False

#         print(f"✅ 清洗完成：{output_file}")

# print("🎯 所有文件清洗完成！")

# import os
# import pandas as pd

# # 文件路径
# input_folder = 'input_v3'
# output_folder = 'speed_v1'

# # 确保输出文件夹存在
# os.makedirs(output_folder, exist_ok=True)

# # 分块大小
# chunksize = 100000  # 每批读取10万行

# # 函数：仅保留 state=1 的行
# def filter_state(chunk):
#     """筛选出 state = 1 的行"""
#     return chunk[chunk['state'] == 1]

# # 批量处理 CSV 文件
# for file_name in os.listdir(input_folder):
#     if file_name.endswith('.csv'):
#         input_file = os.path.join(input_folder, file_name)
#         output_file = os.path.join(output_folder, file_name)

#         print(f"🚀 正在处理文件：{file_name}")

#         first_write = True

#         # 流式读取和写入
#         with pd.read_csv(input_file, chunksize=chunksize) as reader:
#             for i, chunk in enumerate(reader):
#                 print(f"🛠️ 处理批次 {i + 1}")

#                 # 筛选出 state = 1 的行
#                 filtered_chunk = filter_state(chunk)

#                 # 将筛选后的数据保存
#                 mode = 'w' if first_write else 'a'
#                 header = first_write
#                 filtered_chunk.to_csv(output_file, index=False, encoding='utf-8-sig', mode=mode, header=header)
#                 first_write = False

#         print(f"✅ 完成清洗：{output_file}")

# print("🎯 所有文件清洗完成！")

# import os
# import pandas as pd

# # 文件路径
# folder = 'speed_v2'

# # 分块大小（10万行）
# chunksize = 100000  

# # 批量处理 CSV 文件
# for file_name in os.listdir(folder):
#     if file_name.endswith('.csv'):
#         file_path = os.path.join(folder, file_name)

#         print(f"🚀 正在处理文件：{file_name}")

#         # 临时输出文件，防止数据出错时丢失原文件
#         temp_file = file_path + '.tmp'

#         first_write = True

#         # 分块读取与处理
#         with pd.read_csv(file_path, chunksize=chunksize) as reader:
#             for i, chunk in enumerate(reader):
#                 print(f"🛠️  处理批次 {i + 1}")

#                 # 时间格式化，只保留时间部分
#                 chunk['time'] = pd.to_datetime(chunk['time']).dt.strftime('%H:%M:%S')

#                 # 写入临时文件
#                 mode = 'w' if first_write else 'a'
#                 header = first_write
#                 chunk.to_csv(temp_file, index=False, encoding='utf-8-sig', mode=mode, header=header)

#                 first_write = False

#         # 替换原文件
#         os.replace(temp_file, file_path)

#         print(f"✅ 文件处理完成并覆盖：{file_name}")

# print("🎯 所有文件已处理！")


# import os
# import csv
# from xml.etree import ElementTree as ET
# from collections import defaultdict
# import time

# # 1. 读取路网文件获取所有edge的id_y（保留完整ID）
# def get_all_edges(net_file):
#     print("⏳ 正在解析路网文件...")
#     start_time = time.time()
#     tree = ET.parse(net_file)
#     root = tree.getroot()
#     edges = {edge.get('id') for edge in root.findall('edge')}
#     print(f"✅ 路网文件解析完成，共找到 {len(edges)} 个edge，耗时 {time.time()-start_time:.2f}秒")
#     return edges

# # 2. 增强版文件处理
# def process_file(input_path, output_path, all_idys):
#     print(f"\n🚀 开始处理文件: {os.path.basename(input_path)}")
#     start_time = time.time()
    
#     # 存储数据结构
#     hourly_data = defaultdict(lambda: defaultdict(list))
#     hourly_avg = defaultdict(list)
    
#     with open(input_path, 'r', encoding='utf-8') as f:
#         reader = csv.reader(f)
#         header = next(reader)  # 跳过表头
        
#         line_count = 0
#         for row in reader:
#             try:
#                 line_count += 1
#                 # 进度提示
#                 if line_count % 100000 == 0:
#                     print(f"📊 已处理 {line_count} 行...")
                
#                 # 解析数据（保留完整id_y）
#                 time_str = row[1]
#                 hour = int(time_str.split(':')[0])
#                 idy = row[-1]  # 直接获取完整id_y
#                 speed = float(row[4])
                
#                 # 存储数据
#                 hourly_data[hour][idy].append(speed)
#                 hourly_avg[hour].append(speed)
#             except Exception as e:
#                 print(f"⚠️ 行 {line_count} 处理出错: {str(e)}")

#     print(f"🔢 数据解析完成，共处理 {line_count} 行")
    
#     # 计算小时平均速度
#     print("🧮 正在计算统计量...")
#     hour_avg_speed = {}
#     for hour in hourly_avg:
#         hour_avg_speed[hour] = sum(hourly_avg[hour])/len(hourly_avg[hour]) if hourly_avg[hour] else 0

#     # 生成结果
#     results = []
#     for hour in range(24):
#         # 显示处理进度
#         if hour % 6 == 0:
#             print(f"⏳ 正在生成 {hour:02d}:00 时段数据...")
        
#         current_avg = hour_avg_speed.get(hour, 0)
#         for idy in all_idys:
#             speeds = hourly_data[hour].get(idy, [])
            
#             count = len(speeds)
#             if count == 0:
#                 results.append([
#                     f"{hour:02d}:00:00",
#                     idy,
#                     0,
#                     -1,
#                     -1,
#                     round(current_avg, 2)
#                 ])
#             else:
#                 results.append([
#                     f"{hour:02d}:00:00",
#                     idy,
#                     count,
#                     max(speeds),
#                     min(speeds),
#                     round(sum(speeds)/count, 2)
#                 ])

#     # 写入结果
#     os.makedirs(os.path.dirname(output_path), exist_ok=True)
#     with open(output_path, 'w', newline='') as f:
#         writer = csv.writer(f)
#         writer.writerow(['hour', 'id_y', 'count', 'max_speed', 'min_speed', 'avg_speed'])
#         writer.writerows(results)
    
#     print(f"✅ 文件处理完成，耗时 {time.time()-start_time:.2f}秒")

# # 主程序
# if __name__ == "__main__":
#     # 配置路径
#     NET_FILE = 'robust.net.xml'
#     INPUT_DIR = 'speed_v2'
#     OUTPUT_DIR = 'speed_v3'

#     try:
#         # 获取所有edge的ID
#         all_edges = get_all_edges(NET_FILE)
        
#         # 创建输出目录
#         os.makedirs(OUTPUT_DIR, exist_ok=True)
        
#         # 获取文件列表
#         files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.csv')]
#         print(f"\n📂 发现 {len(files)} 个待处理文件")
        
#         # 处理所有CSV文件
#         for idx, filename in enumerate(files, 1):
#             input_path = os.path.join(INPUT_DIR, filename)
#             output_path = os.path.join(OUTPUT_DIR, filename)
#             print(f"\n📁 正在处理文件 ({idx}/{len(files)})：{filename}")
#             process_file(input_path, output_path, all_edges)
            
#     except Exception as e:
#         print(f"❌ 发生严重错误：{str(e)}")
#     finally:
#         print("\n🎉 所有文件处理完成！结果已保存至 speed_v3 目录")

# import os
# import csv
# import datetime
# from collections import defaultdict

# def merge_files(input_dir, output_path):
#     # 使用三层字典结构进行分组：{(hour, idy, weekday): [records]}
#     grouped_data = defaultdict(list)

#     # 遍历输入目录
#     for filename in os.listdir(input_dir):
#         if not filename.endswith('.csv'):
#             continue
        
#         try:
#             # 解析日期并判断工作日
#             date_str = filename.split('.')[0]
#             date_obj = datetime.datetime.strptime(date_str, "%Y%m%d")
#             weekday = 0 if date_obj.weekday() >= 5 else 1  # 0=周末，1=工作日
            
#             with open(os.path.join(input_dir, filename)) as f:
#                 reader = csv.DictReader(f)
#                 for row in reader:
#                     try:
#                         # 提取基础数据
#                         hour = row['hour'][:2]  # 取前两位小时数
#                         idy = row['id_y']
                        
#                         # 转换速度单位
#                         def convert(speed):
#                             return round(float(speed)/3.6, 2) if float(speed) != -1 else -1
                        
#                         record = (
#                             int(row['count']),
#                             convert(row['max_speed']),
#                             convert(row['min_speed']),
#                             convert(row['avg_speed'])
#                         )
                        
#                         # 按特征分组
#                         key = (hour, idy, weekday)
#                         grouped_data[key].append(record)
                        
#                     except Exception as e:
#                         print(f"处理文件 {filename} 行错误: {str(e)}")
#                         continue
                        
#         except Exception as e:
#             print(f"处理文件 {filename} 失败: {str(e)}")
#             continue

#     # 生成最终结果
#     with open(output_path, 'w', newline='') as f:
#         writer = csv.writer(f)
#         writer.writerow([
#             'hour', 'id_y', 'weekday', 
#             'count', 'max_speed', 'min_speed', 'avg_speed'
#         ])
        
#         # 处理每个分组
#         for key in sorted(grouped_data.keys()):
#             hour, idy, weekday = key
#             records = grouped_data[key]
            
#             # 计算统计指标
#             total_count = sum(r[0] for r in records)
            
#             # 有效极值列表（排除-1）
#             valid_max = [r[1] for r in records if r[1] != -1]
#             valid_min = [r[2] for r in records if r[2] != -1]
            
#             if total_count > 0:
#                 # 正常计算模式
#                 max_speed = max(valid_max) if valid_max else -1
#                 min_speed = min(valid_min) if valid_min else -1
#                 avg_speed = round(sum(r[3]*r[0] for r in records)/total_count, 2)
#             else:
#                 # 无数据模式
#                 avg_values = [r[3] for r in records]
#                 avg_speed = round(sum(avg_values)/len(avg_values), 2) if avg_values else 0
#                 max_speed = -1
#                 min_speed = -1
            
#             # 格式化小时列
#             formatted_hour = f"{hour}:00:00"
            
#             writer.writerow([
#                 formatted_hour,
#                 idy,
#                 weekday,
#                 total_count,
#                 max_speed,
#                 min_speed,
#                 avg_speed
#             ])

# if __name__ == "__main__":
#     # 配置参数
#     INPUT_DIR = "speed_v3"
#     OUTPUT_PATH = "speed_data.csv"
    
#     # 执行合并
#     print("🚀 开始合并文件...")
#     print("⚙ 正在处理数据（速度单位自动转换为m/s）")
#     merge_files(INPUT_DIR, OUTPUT_PATH)
#     print(f"✅ 合并完成！结果保存至 {OUTPUT_PATH}")



# import os 
# import csv
# import datetime
# from collections import defaultdict

# def merge_files(input_dir, output_path):
#     # 使用三层字典结构进行分组：{(hour, idy, weekday): [records]}
#     grouped_data = defaultdict(list)

#     # 遍历输入目录
#     for filename in os.listdir(input_dir):
#         if not filename.endswith('.csv'):
#             continue
        
#         try:
#             # 解析日期并判断工作日
#             date_str = filename.split('.')[0]
#             date_obj = datetime.datetime.strptime(date_str, "%Y%m%d")
#             weekday = 0 if date_obj.weekday() >= 5 else 1  # 0=周末，1=工作日
            
#             with open(os.path.join(input_dir, filename)) as f:
#                 reader = csv.DictReader(f)
#                 for row in reader:
#                     try:
#                         # 提取基础数据
#                         hour = row['hour'][:2]  # 取前两位小时数
#                         idy = row['id_y']
                        
#                         # 转换速度单位
#                         def convert(speed):
#                             return round(float(speed)/3.6, 2) if float(speed) != -1 else -1
                        
#                         record = (
#                             int(row['count']),
#                             convert(row['max_speed']),
#                             convert(row['min_speed']),
#                             convert(row['avg_speed'])
#                         )
                        
#                         # 按特征分组
#                         key = (hour, idy, weekday)
#                         grouped_data[key].append(record)
                        
#                     except Exception as e:
#                         print(f"处理文件 {filename} 行错误: {str(e)}")
#                         continue
                        
#         except Exception as e:
#             print(f"处理文件 {filename} 失败: {str(e)}")
#             continue

#     # 计算每个分组的统计信息
#     grouped_stats = {}
#     for key in grouped_data:
#         hour, idy, weekday = key
#         records = grouped_data[key]
        
#         total_count = sum(r[0] for r in records)
        
#         valid_max = [r[1] for r in records if r[1] != -1]
#         valid_min = [r[2] for r in records if r[2] != -1]
        
#         if total_count > 0:
#             max_speed = max(valid_max) if valid_max else -1
#             min_speed = min(valid_min) if valid_min else -1
#             avg_speed = round(sum(r[3] * r[0] for r in records) / total_count, 2)
#         else:
#             avg_values = [r[3] for r in records]
#             avg_speed = round(sum(avg_values) / len(avg_values), 2) if avg_values else 0
#             max_speed = -1
#             min_speed = -1
        
#         grouped_stats[key] = (total_count, max_speed, min_speed, avg_speed)
        
#     # 计算每个小时和工作日的平均速度
#     hour_weekday_avg = defaultdict(list)
#     for key in grouped_stats:
#         hour, idy, weekday = key
#         avg_speed = grouped_stats[key][3]
#         if avg_speed != -1:  # 排除无效数据
#             hour_weekday_avg[(hour, weekday)].append(avg_speed)

#     # 计算平均
#     avg_hour_weekday = {}
#     for hw in hour_weekday_avg:
#         speeds = hour_weekday_avg[hw]
#         avg = round(sum(speeds)/len(speeds), 2) if speeds else 0
#         avg_hour_weekday[hw] = avg

#     # 替换平均速度过低的条目
#     new_grouped_stats = {}
#     for key in grouped_stats:
#         hour, idy, weekday = key
#         total_count, max_speed, min_speed, avg_speed = grouped_stats[key]
        
#         # 处理有效但过低的数据
#         if avg_speed != -1 and avg_speed < 1:
#             current_avg = avg_hour_weekday.get((hour, weekday), avg_speed)  # 保持原值作为默认值
#             avg_speed = current_avg
        
#         new_grouped_stats[key] = (total_count, max_speed, min_speed, avg_speed)

#     # 写入最终结果
#     with open(output_path, 'w', newline='') as f:
#         writer = csv.writer(f)
#         writer.writerow(['hour', 'id_y', 'weekday', 'count', 'max_speed', 'min_speed', 'avg_speed'])
        
#         for key in sorted(new_grouped_stats.keys()):
#             hour, idy, weekday = key
#             total_count, max_speed, min_speed, avg_speed = new_grouped_stats[key]
#             formatted_hour = f"{hour}:00:00"
#             writer.writerow(
#                 [formatted_hour, idy, weekday, total_count, max_speed, min_speed, avg_speed]
#                 )

# merge_files("speed_v3", "speed_data.csv")
        
        
# import os
# import pandas as pd

# # 文件路径
# folder = 'input_v3'

# # 分块大小（10万行）
# chunksize = 100000  

# # 批量处理 CSV 文件
# for file_name in os.listdir(folder):
#     if file_name.endswith('.csv'):
#         file_path = os.path.join(folder, file_name)

#         print(f"🚀 正在处理文件：{file_name}")

#         # 临时输出文件，防止数据出错时丢失原文件
#         temp_file = file_path + '.tmp'

#         first_write = True

#         # 分块读取与处理
#         with pd.read_csv(file_path, chunksize=chunksize) as reader:
#             for i, chunk in enumerate(reader):
#                 print(f"🛠️  处理批次 {i + 1}")

#                 # 时间格式化，只保留时间部分
#                 chunk['time'] = pd.to_datetime(chunk['time']).dt.strftime('%H:%M:%S')

#                 # 写入临时文件
#                 mode = 'w' if first_write else 'a'
#                 header = first_write
#                 chunk.to_csv(temp_file, index=False, encoding='utf-8-sig', mode=mode, header=header)

#                 first_write = False

#         # 替换原文件
#         os.replace(temp_file, file_path)

#         print(f"✅ 文件处理完成并覆盖：{file_name}")

# print("🎯 所有文件已处理！")

import pandas as pd
import pickle
import os
from sumolib import net
from tqdm import tqdm

# 文件路径
SPEED_DATA_FILE = "speed_data.csv"
SPEED_FILLED_STEP1 = "speed_filled_step1.csv"
SPEED_DICT_CACHE = "speed_dict.pkl"
SUMO_NET_FILE = "robust.net.xml"
OUTPUT_FILE = "speed_data_filled.csv"


# ✅ 第一步：同一路段其他时间或工作日的数据补全
def fill_same_road_speed(df):
    grouped = df.groupby("id_y")
    filled_data = []

    for _, group in tqdm(grouped, desc="补全同一路段速度", unit="路段"):
        for _, row in group.iterrows():
            if row["count"] == 0:
                valid_rows = group[group["count"] > 0]
                if not valid_rows.empty:
                    row["avg_speed"] = valid_rows["avg_speed"].mean()
                    row["max_speed"] = valid_rows["max_speed"].mean()
                    row["min_speed"] = valid_rows["min_speed"].mean()
                    row["count"] = -2  # 标记为同一路段补全
            filled_data.append(row)

    filled_df = pd.DataFrame(filled_data)
    filled_df.to_csv(SPEED_FILLED_STEP1, index=False)  # 保存第一步结果
    return filled_df


# ✅ 第二步：基于SUMO路网连接关系补全
def fill_neighbor_speed(df, net_file, bfs_depth=2):
    # 解析SUMO路网
    road_net = net.readNet(net_file)

    # 读取或创建 speed_dict
    if os.path.exists(SPEED_DICT_CACHE):
        print(f"正在加载 {SPEED_DICT_CACHE} ...")
        with open(SPEED_DICT_CACHE, "rb") as f:
            speed_dict = pickle.load(f)
    else:
        print("构建 speed_dict 并缓存...")
        speed_dict = {row["id_y"]: row for _, row in df.iterrows()}
        with open(SPEED_DICT_CACHE, "wb") as f:
            pickle.dump(speed_dict, f)  # 缓存字典，加速后续访问

    # 补全数据
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="补全邻居速度", unit="行"):
        if row["count"] == 0 or row["count"] == -2:
            edge_id = row["id_y"]
            # BFS 搜索邻居路段
            visited = set()
            queue = [(edge_id, 0)]
            neighbor_speeds = []

            while queue:
                current_edge, depth = queue.pop(0)
                if depth > bfs_depth:
                    break

                if current_edge in visited:
                    continue
                visited.add(current_edge)

                # 获取邻接路段
                try:
                    edge = road_net.getEdge(current_edge)
                    for outgoing_edge in edge.getOutgoing():
                        neighbor = outgoing_edge.getID()
    
                        # 收集有速度数据的邻居
                        if neighbor in speed_dict:
                            neighbor_row = speed_dict[neighbor]
                            if neighbor_row["count"] > 0:
                                neighbor_speeds.append(neighbor_row["avg_speed"])
    
                        # 加入队列进行进一步搜索
                        queue.append((neighbor, depth + 1))
                except:
                    pass

            # 使用邻居速度补全
            if neighbor_speeds:
                row["avg_speed"] = sum(neighbor_speeds) / len(neighbor_speeds)
                row["count"] = -3  # 标记为邻居补全

    return df


# ✅ **执行流程**
if __name__ == "__main__":
    # 读取原始数据
    speed_data = pd.read_csv(SPEED_DATA_FILE)

    # **第一步：同一路段补全**
    if os.path.exists(SPEED_FILLED_STEP1):
        print(f"正在加载 {SPEED_FILLED_STEP1} ...")
        speed_data_filled = pd.read_csv(SPEED_FILLED_STEP1)
    else:
        print("开始同一路段补全...")
        speed_data_filled = fill_same_road_speed(speed_data)

    # **第二步：邻居补全**
    print("开始邻居路段补全...")
    speed_data_filled = fill_neighbor_speed(speed_data_filled, SUMO_NET_FILE)

    # **保存最终结果**
    speed_data_filled.to_csv(OUTPUT_FILE, index=False)
    print(f"补全完成，结果保存在 {OUTPUT_FILE}")

