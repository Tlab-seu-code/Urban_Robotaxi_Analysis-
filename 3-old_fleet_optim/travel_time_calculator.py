# -*- coding: utf-8 -*-
"""
Created on Thu Dec 26 18:53:36 2024

@author: TLab
"""
import csv
import sumolib
from collections import defaultdict
import copy

# 初始参数
v_init = 4.0  # 初始速度 (m/s)
tolerance = 1e-3  # 收敛误差容忍值
time_codes = range(9,15)  # 时间编码范围
traj_file = "v4_traj.csv"  # 行程数据文件

# 读取路网，提取所有边的ID和长度
net = sumolib.net.readNet("robust.net.xml")  # 只需加载一次路网
edges = net.getEdges()
edge_lengths = {edge.getID(): edge.getLength() for edge in edges}
edge_speeds = {edge.getID(): v_init for edge in edges}
edge_ids = [edge.getID() for edge in edges]
total_err = []
total_free_edge=[]
# 遍历每个时间编码
for time_code in time_codes:
    print(f"处理时间编码 {time_code} ...")
    count = 0
    v_init += 1
    # 初始化边速度
    edge_speeds = {edge_id: v_init for edge_id in edge_speeds}

    # 从 traj 文件中提取对应时间编码的 trips
    trips = []
    edge_to_trips = defaultdict(set)  # 创建反向索引
    covered_edges = set()
    with open(traj_file, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if 1: # int(row["时间编码"]) == time_code:
                trips.append({
                    "start_edge": row["起点边ID"],
                    "end_edge": row["终点边ID"],
                    "start_off": float(row["起点边距离"]),
                    "end_off": float(row["终点边距离"]),
                    "real_time": float(row["旅行时间"]),
                    "path": row["path"].split(",")
                })
                # 更新反向索引
                for edge_id in trips[-1]['path']:
                    edge_to_trips[edge_id].add(len(trips)-1)
                    covered_edges.add(edge_id)
                
    uncovered_edges = set(edge_ids)-set(covered_edges)
    
    # 开始迭代计算
    converged = False
    while not converged:
        count += 1
        print(f"数据集{time_code}:第{count}轮循环")
        total_error = 0.0
        estimated_time = []

        # Step 1: 遍历每个行程，计算时间差和误差
        for trip in trips:
            # 根据路径计算估算时间
            e = sum(
                edge_lengths[edge_id] / edge_speeds[edge_id]
                for edge_id in trip["path"]
            )
            e -= trip["start_off"] / edge_speeds[trip["path"][0]]
            e -= (edge_lengths[trip["path"][-1]] - trip["end_off"]) / edge_speeds[trip["path"][-1]]
            estimated_time.append(e)
            total_error += abs(trip["real_time"] - e) / trip["real_time"]

        # 计算平均误差
        relative_error = total_error / len(trips)
        print(f"误差：{relative_error}")
        
        # 计算offset
        offset = {} 
        for i in covered_edges:
            offset[i] = 0
            for j in edge_to_trips[i]:
                offset[i] += estimated_time[j]-trips[j]["real_time"]
        
        OK = 0
        k = 1.2
        
        new_edge_speeds = copy.deepcopy(edge_speeds)
        
        # 更新
        # Step 2: 更新被覆盖的边的速度
        while OK == 0:
            print(f"数据集{time_code}:第{count}轮循环,调整k={k}")
            for i in covered_edges:
                if offset[i] < 0:
                    new_edge_speeds[i] = edge_speeds[i] / k
                else:
                    new_edge_speeds[i] = edge_speeds[i] * k
        
            new_estimated_time = []
            
            total_error = 0.0
            
            for trip in trips:
                # 根据路径计算估算时间
                e = sum(
                    edge_lengths[edge_id] / new_edge_speeds[edge_id]
                    for edge_id in trip["path"]
                )
                e -= trip["start_off"] / edge_speeds[trip["path"][0]]
                e -= (edge_lengths[trip["path"][-1]] - trip["end_off"]) / edge_speeds[trip["path"][-1]]
                new_estimated_time.append(e)
                total_error += abs(trip["real_time"] - e) / trip["real_time"]

    
            # 计算平均误差
            new_relative_error = total_error / len(trips)            
            
            # 判断是否收敛
            if new_relative_error < relative_error:
                edge_speeds = new_edge_speeds
                OK = 1
                break
            else:
                k = 1 + 0.75 * (k - 1)
                if k < 1.0001:
                    converged = True
                    OK = 1
                    break

    # Step 3: 更新未覆盖边的速度
    finish = 0
    covered_edges = set(covered_edges)
    uncovered_edges = set(uncovered_edges)
    while finish == 0:
        print(f"数据集{time_code}:剩余边数{len(uncovered_edges)}")
        finish = 1
        neighbor = {}
        for edge_id in uncovered_edges:
            edge = net.getEdge(edge_id)
            neighbor[edge_id]=[]
            for n in edge.getIncoming().keys():
                if n.getID() not in uncovered_edges:
                    neighbor[edge_id].append(n)
            for n in edge.getOutgoing().keys():
                if n.getID() not in uncovered_edges:
                    neighbor[edge_id].append(n)
                    
        # 将字典项转换为一个列表，列表的每个元素是一个元组，包含键和值
        items = list(neighbor.items())
 
        # 根据数组长度（即值的长度）对列表进行排序，注意这里使用了 -len(value) 来实现降序排序
        items.sort(key=lambda item: -len(item[1]))
 
        # 遍历排序后的列表
        for key, value in items:    
            if value:
                neighbor_speeds = [
                    edge_speeds[n.getID()]
                     for n in value
                ]
                # 使用邻居速度均值更新
                edge_speeds[edge_id] = (
                    sum(neighbor_speeds) / len(neighbor_speeds)
                )
                uncovered_edges.remove(key)
                covered_edges.add(key)
                if uncovered_edges != set():
                    finish = 0

    # 保存每条边的最终速度到文件
    output_file = f"final_speeds_{time_code}.csv"
    with open(output_file, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["edge_id", "final_speed", "length"])
        for edge_id, speed in edge_speeds.items():
            writer.writerow([edge_id, speed, net.getEdge(edge_id).getLength()])

    print(f"时间编码 {time_code} 处理完成，误差{relative_error}")
    total_err.append(relative_error)
    total_free_edge.append(len(uncovered_edges))
print("所有时间编码处理完成。")
print(total_err)
print(total_free_edge)