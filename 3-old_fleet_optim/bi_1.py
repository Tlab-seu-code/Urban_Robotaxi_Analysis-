# -*- coding: utf-8 -*-
"""
Created on Fri Dec 27 19:41:32 2024

@author: TLab
"""

import os
import csv
import networkx as nx
import sumolib
from datetime import datetime
import pickle

# 文件路径
traj_file = "v5_traj.csv"
speed_file = "final_speeds_10.csv"  # 假设是使用时间编码 10 的速度文件
network_file = "robust.net.xml"  # SUMO 路网文件
output_folder = "graph"  # 保存的二部图文件夹

# 创建保存文件夹
os.makedirs(output_folder, exist_ok=True)

# 读取路网
net = sumolib.net.readNet(network_file)

# 读取速度和长度表
edge_speeds = {}
with open(speed_file, "r", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        edge_id = row["edge_id"]
        final_speed = float(row["final_speed"])
        length = float(row["length"])
        edge_speeds[edge_id] = {"speed": final_speed, "length": length}

# 读取行程数据，并按日期分类
orders_by_date = {}
with open(traj_file, "r", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        order_date = row["到达起点时间"].split(" ")[0]  # 提取日期部分
        start_edge = row["起点边ID"]
        end_edge = row["终点边ID"]
        start_dist = float(row["起点边距离"])
        end_dist = float(row["终点边距离"])
        call_time = datetime.strptime(row["到达起点时间"], "%Y-%m-%d %H:%M:%S")
        travel_time = float(row["旅行时间"])
        end_time = datetime.strptime(row["到达目的地时间"], "%Y-%m-%d %H:%M:%S")
        order = {
            "order_id": row["订单号"],
            "start_edge": start_edge,
            "end_edge": end_edge,
            "start_off": start_dist,
            "end_off": end_dist,
            "call_time": call_time,
            "end_time": end_time,
            "q_x": float(row["起点X"]),
            "q_y": float(row["起点Y"]),
            "z_x": float(row["终点X"]),
            "z_y": float(row["终点Y"]),
        }
        if order_date not in orders_by_date:
            orders_by_date[order_date] = []
        orders_by_date[order_date].append(order)

import time

# 遍历所有日期并生成二部图
for date, orders in orders_by_date.items():
    # if datetime.strptime(date, "%Y-%m-%d") < datetime.strptime("2024-11-15 00:00:00", "%Y-%m-%d %H:%M:%S"):
    #     continue
    print(f"正在处理日期 {date} 的数据，共有 {len(orders)} 条订单...")
    G = nx.DiGraph()  # 使用有向二部图

    # 构造节点
    for order in orders:
        order_id = order["order_id"]
        G.add_node(f"{order_id}_left", bipartite=0)
        G.add_node(f"{order_id}_right", bipartite=1)

    # 构造边
    H = 0
    total_edges = 0
    t1 = time.time()
    t2 = time.time()
    
    for i, order_a in enumerate(orders):
        # 每处理 10 条边打印一次进度

        OK = 0 # 默认排序
        H = 0
        
        threshold = 0
        BL = [0] * len(orders)
        while (OK < 100 or threshold < 5000) and threshold <= 10000:
            threshold += 1000   
            print(OK, threshold, sum(BL))
            for j, order_b in enumerate(orders):
                if i == j or BL[j] == 1:
                    continue
                   
                # 检查时间条件：A的到达时间必须早于B的到达起点时间
                # if j % 100 == 0:
                #     print(f"{j}:{(order_b['call_time'] - order_a['end_time']).total_seconds()} {OK}")
                
                if order_a["end_time"] <= order_b["call_time"] and (order_b['call_time'] - order_a['end_time']).total_seconds() < 7200 and ((order_b["q_x"]-order_a["z_x"])**2 + (order_b["q_y"]-order_a["z_y"])**2 < threshold ** 2):
                    BL[j] = 1
                    try:
                        # 获取最短路径
                        start_edge = order_a["end_edge"]
                        end_edge = order_b["start_edge"]
                        H += 1
                        shortest_path = net.getShortestPath(
                                net.getEdge(start_edge), net.getEdge(end_edge)
                            )[0]
        
                        # 计算路径行驶时间
                        total_time = 0
                        for edged in shortest_path:
                            edge_id = edged.getID()
                            if edge_id in edge_speeds:
                                length = edge_speeds[edge_id]["length"]
                                speed = edge_speeds[edge_id]["speed"]
                                total_time += length / speed  # 时间 = 路径长度 / 速度
                            else:
                                print(f"Edge {edge_id} 不在速度表中，跳过该边")
        
                        total_time -= order_a["start_off"] / edge_speeds[order_a["end_edge"]]["speed"]
                        total_time -= (edge_speeds[order_b["start_edge"]]["length"] - order_b["start_off"]) / edge_speeds[order_b["start_edge"]]["speed"]
        
                        # 检查是否满足时间条件
                        time_diff = (order_b["call_time"] - order_a["end_time"]).total_seconds()
                        if time_diff >= total_time:
                            # 添加边
                            G.add_edge(f"{order_a['order_id']}_left", f"{order_b['order_id']}_right")
                            total_edges += 1
                            OK += 1
                    except:
                        print(f"{start_edge}->{end_edge}error")
                        
        for j, order_b in enumerate(orders):
                # 补位两小时以后的订单全部加入
            if order_a["end_time"] <= order_b["call_time"] and BL[j] == 0 and (order_b['call_time'] - order_a['end_time']).total_seconds() > 7200:
                G.add_edge(f"{order_a['order_id']}_left", f"{order_b['order_id']}_right")
                total_edges += 1
                OK += 1  
        t2 = t1
        t1 = time.time()
        print(f"    已处理 {i} / {len(orders)} 订单... {OK} {t1-t2}")

    # 保存图
    output_file = os.path.join(output_folder, f"bipartite_graph_{date}.gpickle")
    with open(output_file, "wb") as f:
        pickle.dump(G, f)

    print(f"日期 {date} 的二部图已保存到 {output_file}，总边数: {total_edges}")

print("所有日期的二部图生成完成！")
print(G.edges)