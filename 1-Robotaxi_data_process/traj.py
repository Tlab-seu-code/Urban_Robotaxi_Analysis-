# -*- coding: utf-8 -*-
"""
Created on Tue Dec 24 21:17:07 2024

@author: TLab
"""

# import pandas as pd
# from datetime import datetime

# # 读取数据
# df = pd.read_csv('original.csv')

# # 筛选订单来源字段，不能是调度单和充电单
# df = df[~df['订单来源'].isin(['调度单', '充电单'])]

# # 筛选订单状态字段为完成
# df = df[df['订单状态'] == '完成']

# # 处理呼单时间字段，将其转换为datetime格式
# df['呼单时间'] = pd.to_datetime(df['呼单时间'])

# # 根据呼单时间判断工作日/休息日
# df['工作日类型'] = df['呼单时间'].apply(lambda x: '工作日' if x.weekday() < 5 else '休息日')

# df['旅行时间'] = df['行程时长'] - df['接驾时长']

# # 根据呼单时间判断早高峰/午间/晚高峰/夜间
# def get_peak_time(hour):
#     if 7 <= hour < 9:
#         return '早高峰'
#     elif 9 <= hour < 17:
#         return '午间'
#     elif 17 <= hour < 20:
#         return '晚高峰'
#     else:
#         return '夜间'

# df['早晚高峰类型'] = df['呼单时间'].apply(lambda x: get_peak_time(x.hour))

# # 只保留需要的字段
# df = df[['起点经度', '起点纬度', '终点经度', '终点纬度', '呼单时间', '工作日类型', '早晚高峰类型', '旅行时间']]

# # 保存到新的csv文件
# df.to_csv('traj.csv', index=False)

import pandas as pd
import sumolib

# 加载SUMO路网
net = sumolib.net.readNet('osm.net.xml')

# 读取traj.csv
df = pd.read_csv('traj.csv')

df['起点边ID'] = None
df['终点边ID'] = None
df['起点边距离'] = -1
df['终点边距离'] = -1

import math

def calculate_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

# 定义函数获取邻接边的ID
def get_edge_id(x, y, radius=1000):
    # 获取起点或终点附近的边（根据给定的半径）
    try:
        edges = net.getNeighboringEdges(x, y, radius)
    except:
        edges = None
    if edges:
        # 如果找到邻接的边，返回第一个边的ID
        dis = 1000
        edge = edges[0][0]
        for i in edges:
            if i[1]<dis:
                edge = i[0]
                dis = i[1]
        from_point = edge.getFromNode().getCoord()
        node_dis = calculate_distance(from_point[0],from_point[1],x,y)
        l = edge.getLength()
        b = node_dis**2-dis**2
        if b <= 0:
            pos = 0
        elif b > l:
            pos = l
        else:
            pos = math.sqrt(b)
        return edge.getID(), pos  # 假设我们取第一个邻接的边
    else:
        return None, -1  # 如果没有邻接的边，返回None
    
# 记录处理进度
def process_row(row, index, total_rows):
    # 每处理100条数据输出一次信息
    if index % 10 == 0:
        print(f'处理进度: {index}/{total_rows} 行')

    # 获取起点经纬度
    start_lon, start_lat = row['起点经度'], row['起点纬度']
    end_lon, end_lat = row['终点经度'], row['终点纬度']
    
    # 将经纬度转换为SUMO的x, y坐标
    start_x, start_y = net.convertLonLat2XY(start_lon, start_lat)
    end_x, end_y = net.convertLonLat2XY(end_lon, end_lat)
    
    # 检查转换后的坐标是否有效
    if None in [start_x, start_y, end_x, end_y]:
        row['起点边ID'] = None
        row['终点边ID'] = None
        row['起点边距离'] = -1
        row['终点边距离'] = -1
        return row
    
    # 获取起点和终点的邻接边ID
    start_edge_id, start_pos = get_edge_id(start_x, start_y)
    
    end_edge_id, end_pos = get_edge_id(end_x, end_y)
    
    # 将邻接边ID添加到行中
    row['起点边ID'] = start_edge_id
    row['终点边ID'] = end_edge_id
    row['起点边距离'] = start_pos
    row['终点边距离'] = end_pos
    
    return row

# 获取总行数
total_rows = len(df)

# 使用enumerate获取索引并处理每一行数据
for idx, row in df.iterrows():
    df.loc[idx] = process_row(row, idx, total_rows)

# 保存处理后的数据到新的CSV文件
df.to_csv('traj_v10.csv', index=False, encoding='utf-8')

# import pandas as pd
# import sumolib

# # 加载SUMO路网
# net = sumolib.net.readNet('osm.net.xml')

# # 读取数据
# df = pd.read_csv('traj_with_edges.csv')

# # 1. 剔除没有匹配到边的行程，即起点边距离或终点边距离为-1的行
# df_filtered = df[(int(df['起点边距离']) != -1) & (int(df['终点边距离']) != -1)]

# # 2. 剔除旅行时间<120或>3600的行程
# df_filtered = df_filtered[(df_filtered['旅行时间'] >= 120) & (df_filtered['旅行时间'] <= 3600)]

# # 获取总行数
# total_rows = len(df_filtered)

# # 3. 计算路径长度和平均速度
# path_list = []  # 用于存储路径ID
# avg_speed_list = []  # 用于存储平均速度
# valid_rows = []  # 用于存储有效行索引

# for idx, row in enumerate(df_filtered.itertuples(), 1):
#     start_edge = row.起点边ID
#     end_edge = row.终点边ID
    
#     try:
#         # 获取路径和路径长度
#         path, path_length = net.getShortestPath(net.getEdge(start_edge), net.getEdge(end_edge))
        
#         # 提取路径中的每个边的ID
#         edge_ids = [edge.getID() for edge in path]
        
#         # 将路径ID列表转换为字符串
#         path_str = ",".join(edge_ids)
        
#         # 计算平均速度
#         avg_speed = path_length / row.旅行时间
        
#         # 添加到列表中
#         avg_speed_list.append(avg_speed)
#         path_list.append(path_str)
#         valid_rows.append(True)
        
#     except Exception as e:
#         # 如果获取路径失败，则返回None
#         print(f"Error calculating path for {start_edge} to {end_edge}: {e}")
#         avg_speed_list.append(None)
#         path_list.append(None)
#         valid_rows.append(False)
    
#     # 每100条数据输出一次进度
#     if idx % 100 == 0:
#         print(f"处理进度: {idx}/{total_rows} 行")

# # 4. 将结果添加到DataFrame中
# df_filtered['平均速度'] = avg_speed_list
# df_filtered['path'] = path_list

# # 5. 删除包含None的行（无效行）
# df_filtered = df_filtered[valid_rows]

# # 6. 剔除平均速度低于0.5或高于30的行程
# df_filtered = df_filtered[(df_filtered['平均速度'] >= 0.5) & (df_filtered['平均速度'] <= 30)]

# # 7. 保存为v3_traj.csv
# df_filtered.to_csv('v3_traj.csv', index=False, encoding='utf-8')

# print("数据处理完成，保存为 v3_traj.csv")


