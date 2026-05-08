# -*- coding: utf-8 -*-
"""
Created on Sun Jun  8 19:43:38 2025

@author: WuxiTlab
"""
import os
import csv
import sumolib
from xml.etree import ElementTree as ET
from xml.dom import minidom
from datetime import datetime

def load_net(net_file):
    """加载SUMO路网文件"""
    if not os.path.exists(net_file):
        raise FileNotFoundError(f"路网文件 {net_file} 不存在")
    return sumolib.net.readNet(net_file)

def compute_shortest_path(net, from_edge_id, to_edge_id, from_pos, to_pos):
    """使用sumolib内置方法计算路径"""
    try:
        from_edge = net.getEdge(from_edge_id)
        to_edge = net.getEdge(to_edge_id)
    except sumolib.SumoException:
        return None
    
    path_edges, _ = net.getShortestPath(
        fromEdge=from_edge,
        toEdge=to_edge,
        vClass="passenger",
        fromPos=float(from_pos),
        toPos=float(to_pos)
    )
    return [e.getID() for e in path_edges] if path_edges else None

def generate_rou_xml(input_csv, target_date, net_file, output_rou_file):
    """生成符合SUMO规范的rou.xml文件"""
    net = load_net(net_file)
    root = ET.Element("routes")
    
    # 第一阶段：收集并处理所有订单数据
    orders = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        valid_orders = [row for row in reader if row['日期'] == target_date]
        
        print(f"开始处理 {len(valid_orders)} 个订单...")
        for idx, row in enumerate(valid_orders):
            try:
                # 解析时间
                depart_time = datetime.strptime(row['到达起点时间'], "%Y-%m-%d %H:%M:%S")
                depart_sec = depart_time.hour * 3600 + depart_time.minute * 60 + depart_time.second
                
                # 计算路径
                route_edges = compute_shortest_path(
                    net=net,
                    from_edge_id=row['起点边ID'],
                    to_edge_id=row['终点边ID'],
                    from_pos=row['起点边距离'],
                    to_pos=row['终点边距离']
                )
                
                if not route_edges:
                    print(f"跳过订单 {row['订单号']}：无法计算路径")
                    continue
                
                orders.append({
                    "id": row['订单号'],
                    "depart": depart_sec,
                    "route": route_edges
                })
                
                # 打印处理进度
                if (idx+1) % 100 == 0 or (idx+1) == len(valid_orders):
                    print(f"已处理 {idx+1}/{len(valid_orders)} 订单 | 有效 {len(orders)} 条")
                    
            except Exception as e:
                print(f"处理订单 {row['订单号']} 时出错：{str(e)}")
    
    # 第二阶段：按出发时间排序
    print("正在排序车辆...")
    orders.sort(key=lambda x: x['depart'])
    
    # 第三阶段：生成XML
    print("生成XML结构...")
    for order in orders:
        vehicle = ET.SubElement(root, "vehicle", 
                              id=order['id'],
                              type="arcfox_alphaT",
                              depart=str(order['depart']))
        ET.SubElement(vehicle, "route", edges=" ".join(order['route']))
    
    # 美化输出
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    with open(output_rou_file, 'w', encoding='utf-8') as f:
        f.write(xml_str)
    
    print(f"成功生成 {len(orders)} 辆车的路径文件：{output_rou_file}")

# 使用示例
# generate_rou_xml(
#     input_csv="../dataV3/v6_traj.csv",
#     target_date="2024-11-12",
#     net_file="robust.net.xml",
#     output_rou_file="output.rou.xml"
# )


import os
import csv
import random
import sumolib
from xml.etree import ElementTree as ET
from xml.dom import minidom
from datetime import datetime
import hashlib

def generate_vehicle_id(order_id):
    """生成SUMO兼容的车辆ID（处理中文和特殊字符）"""
    return hashlib.md5(order_id.encode('utf-8')).hexdigest()[:12]  # 取前12位缩短长度

def load_network(net_file):
    """加载SUMO路网"""
    if not os.path.exists(net_file):
        raise FileNotFoundError(f"路网文件 {net_file} 不存在")
    return sumolib.net.readNet(net_file)

def find_nearest_edge(net, lon, lat, search_radius=100):
    """通过经纬度查找最近的道路边"""
    try:
        x, y = net.convertLonLat2XY(float(lon), float(lat))
        candidate_edges = net.getNeighboringEdges(x, y, search_radius)
        return min(candidate_edges, key=lambda e: e[1])[0].getID() if candidate_edges else None
    except Exception as e:
        print(f"坐标转换错误 ({lon}, {lat}): {str(e)}")
        return None

def calculate_route(net, origin_edge, destination_edge):
    """计算两点间最短路径"""
    try:
        path = net.getShortestPath(net.getEdge(origin_edge), 
                                 net.getEdge(destination_edge),
                                 vClass="passenger")[0]
        return [e.getID() for e in path] if path else None
    except sumolib.SumoException:
        return None

def create_route_file(input_csv, target_date, net_file, output_file, 
                     vehicle_types=None, search_radius=100):
    """
    生成SUMO车辆路径文件
    :param vehicle_types: 车型比例字典，如 {'citroen_triomphe':0.7, 'dfpv_e70_bev':0.3}
    :param search_radius: 道路搜索半径（米）
    """
    # 初始化参数
    vehicle_types = vehicle_types or {'elysee_cng': 1.0}
    total_weight = sum(vehicle_types.values())
    if total_weight <= 0:
        raise ValueError("车型比例参数无效")
    
    # 准备概率分布
    type_names = list(vehicle_types.keys())
    type_weights = [w/total_weight for w in vehicle_types.values()]
    
    # 加载路网数据
    net = load_network(net_file)
    valid_orders = []
    
    # 处理CSV数据
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        matching_rows = [row for row in reader if row['date'] == target_date]
        
        print(f"正在处理 {len(matching_rows)} 条订单...")
        for idx, row in enumerate(matching_rows):
            
            try:
                vid = generate_vehicle_id(row['order_id'])
            except KeyError:
                print(f"订单记录缺失order_id字段：{row}")
                continue
            
            # 时间转换处理
            
            try:
                depart_time = datetime.strptime(row['start_time'], "%Y-%m-%d %H:%M:%S")
                depart_seconds = int(depart_time.timestamp() % 86400)
            except ValueError:
                print(f"时间格式错误：{row['start_time']}")
                continue
            
            # 道路匹配
            origin_edge = find_nearest_edge(net, row['start_lon'], row['start_lat'], search_radius)
            dest_edge = find_nearest_edge(net, row['end_lon'], row['end_lat'], search_radius)
            if not origin_edge or not dest_edge:
                print(f"订单 {row['order_id']} 道路匹配失败")
                continue
            
            # 路径计算
            route = calculate_route(net, origin_edge, dest_edge)
            if not route:
                print(f"订单 {row['order_id']} 无有效路径")
                continue
            
            # 车型选择
            selected_type = random.choices(type_names, weights=type_weights, k=1)[0]
            
            valid_orders.append({
                'vid': vid,
                'depart': depart_seconds,
                'route': route,
                'vtype': selected_type
            })
            
            # 进度显示
            if (idx+1) % 100 == 0:
                print(f"已处理 {idx+1}/{len(matching_rows)} 条记录")

    # 按出发时间排序
    valid_orders.sort(key=lambda x: x['depart'])
    
    # 生成XML结构
    root = ET.Element("routes")
    for order in valid_orders:
        vehicle = ET.SubElement(root, "vehicle", 
                              id=order['vid'],
                              type=order['vtype'],
                              depart=str(order['depart']))
        ET.SubElement(vehicle, "route", edges=" ".join(order['route']))
    
    # 美化输出
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(xml_str)
    
    print(f"成功生成含 {len(valid_orders)} 辆车的路径文件：{output_file}")

# 示例调用
if __name__ == "__main__":
    generate_config = {
        'input_csv': '../dataV3/v2-hdv.csv',
        'target_date': '20240708',  # 需与CSV中的date列格式一致
        'net_file': 'robust.net.xml',
        'output_file': 'hdv.rou.xml',
        'vehicle_types': {
            'elysee_cng': 0.2,
            'elysee_p': 0.2,
            'citroen_triomphe': 0.3,
            'dfpv_a60_hev_e': 0.1,
            'dfpv_a60_hev_p': 0.1,
            'dfpv_e70_bev': 0.1
        },
        'search_radius': 150
    }
    
    create_route_file(**generate_config)