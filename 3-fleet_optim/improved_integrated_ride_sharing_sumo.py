#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的集成动态拼单功能脚本 - SUMO路径版本
基于bi_1_ori.py的SUMO路径计算逻辑
"""

import os
import csv
try:
    import networkx as nx
except ImportError:
    nx = None
from datetime import datetime, timedelta
import pickle
import time
import math
from typing import List, Dict, Tuple, Optional, Any
import logging
try:
    import sumolib
except ImportError:
    sumolib = None
import json
import inspect
import argparse

from dynamic_waiting_ride_sharing import DynamicWaitingRideSharing

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('improved_integrated_sumo.log'),
        logging.StreamHandler()
    ]
)

traj_file = "v12-traj.csv"
speed_file = "speed_filled_step1.csv"
network_file = "robust.net.xml"
output_folder = "improved_integrated_results_v12_sumo"
os.makedirs(output_folder, exist_ok=True)

MAX_IDLE_TIME_SECONDS = 7200  # 最大允许空闲时间 (2 小时)
DEFAULT_TRANSFER_SPEED_MPS = 8.0  # 直线距离模式下的默认调度速度

SENSITIVITY_CONFIGS = [
    {"name": "w3m_d300m_straight", "dw_max_wait_minutes": 3, "dw_max_distance_m": 300, "use_sumo_paths": False},
    {"name": "w5m_d500m_straight", "dw_max_wait_minutes": 5, "dw_max_distance_m": 500, "use_sumo_paths": False},
    {"name": "w8m_d800m_straight", "dw_max_wait_minutes": 8, "dw_max_distance_m": 800, "use_sumo_paths": False},
]


def create_dynamic_waiting_system(net, config: Dict[str, Any]):
    """兼容不同DynamicWaitingRideSharing构造函数签名，注入灵敏度参数。"""
    kwargs = {}
    try:
        signature = inspect.signature(DynamicWaitingRideSharing.__init__)
        params = signature.parameters
        if "max_wait_time_minutes" in params:
            kwargs["max_wait_time_minutes"] = config["dw_max_wait_minutes"]
        if "max_wait_distance_meters" in params:
            kwargs["max_wait_distance_meters"] = config["dw_max_distance_m"]
        if "max_vehicle_capacity" in params:
            kwargs["max_vehicle_capacity"] = 3
    except Exception as e:
        logging.warning(f"读取DynamicWaitingRideSharing签名失败，将使用默认构造参数: {e}")
    system = DynamicWaitingRideSharing(net, **kwargs)
    if hasattr(system, "max_wait_time_minutes"):
        system.max_wait_time_minutes = config["dw_max_wait_minutes"]
    if hasattr(system, "max_wait_distance_meters"):
        system.max_wait_distance_meters = config["dw_max_distance_m"]
    if hasattr(system, "max_vehicle_capacity"):
        system.max_vehicle_capacity = 3
    return system

def convert_coords_to_meters(orders):
    """将订单的经纬度坐标转换为米制坐标"""
    if not orders:
        return orders
    
    try:
        import pyproj
        utm_proj = pyproj.Proj(proj='utm', zone=49, ellps='WGS84', north=True)
        wgs84_proj = pyproj.Proj(proj='latlong', datum='WGS84')
        
        transformer = pyproj.Transformer.from_proj(wgs84_proj, utm_proj, always_xy=True)
        def latlon_to_utm(lat, lon):
            x, y = transformer.transform(lon, lat)
            return x, y
        
        converted_orders = []
        for order in orders:
            converted_order = order.copy()
            
            start_x, start_y = latlon_to_utm(order['q_y'], order['q_x'])
            converted_order['q_x_m'] = start_x
            converted_order['q_y_m'] = start_y
            
            end_x, end_y = latlon_to_utm(order['z_y'], order['z_x'])
            converted_order['z_x_m'] = end_x
            converted_order['z_y_m'] = end_y
            
            converted_orders.append(converted_order)
        
        return converted_orders
        
    except ImportError:
        logging.warning("pyproj未安装，使用线性近似方法")
        return convert_coords_to_meters_linear(orders)

def convert_coords_to_meters_linear(orders):
    """线性近似方法（备用方案）"""
    if not orders:
        return orders
    
    center_lat = 30.6  # 武汉中心纬度
    center_lon = 114.2  # 武汉中心经度
    
    lat_to_meters = 111000
    lon_to_meters = 111000 * math.cos(math.radians(30.6))  # 约95500米
    
    converted_orders = []
    for order in orders:
        converted_order = order.copy()
        
        lat_diff = order['q_y'] - center_lat
        lon_diff = order['q_x'] - center_lon
        converted_order['q_x_m'] = lon_diff * lon_to_meters
        converted_order['q_y_m'] = lat_diff * lat_to_meters
        
        lat_diff = order['z_y'] - center_lat
        lon_diff = order['z_x'] - center_lon
        converted_order['z_x_m'] = lon_diff * lon_to_meters
        converted_order['z_y_m'] = lat_diff * lat_to_meters
        
        converted_orders.append(converted_order)
    
    return converted_orders

def build_graph_sumo(orders, net, speed_length_data, workday, use_sumo_paths=True):
    """构建二部图：支持SUMO路径或直线距离模式。"""
    if nx is None:
        raise ImportError("networkx未安装，无法构建二部图")
    mode_name = "SUMO路径" if use_sumo_paths else "直线距离"
    print(f"\n=== 构建二部图（{mode_name}版） ===")
    G = nx.DiGraph()
    n = len(orders)
    
    for order in orders:
        order_id = order["order_id"]
        G.add_node(f"{order_id}_left", bipartite=0)
        G.add_node(f"{order_id}_right", bipartite=1)
    
    total_edges = 0
    start_time = time.time()
    path_calculation_stats = {"attempts": 0, "successes": 0}
    
    for i, order_a in enumerate(orders):
        if i % 100 == 0:
            print(f"处理进度: {i+1}/{n}")
        
        OK = 0
        threshold = 0
        BL = [0] * len(orders)
        
        while threshold <= 1000:  # 保持原始逻辑
            threshold += 1000   
            
            for j, order_b in enumerate(orders):
                if i == j or BL[j] == 1:
                    continue
                   
                if (order_a["end_time"] <= order_b["call_time"] and 
                    (order_b['call_time'] - order_a['end_time']).total_seconds() < 7200):
                    
                    BL[j] = 1
                    
                    path_calculation_stats["attempts"] += 1
                    try:
                        if use_sumo_paths:
                            start_edge = order_a["end_edge"]
                            end_edge = order_b["start_edge"]
                            shortest_path = net.getShortestPath(
                                net.getEdge(start_edge), net.getEdge(end_edge)
                            )[0]
                            if shortest_path is None:
                                continue
                            hour = order_a['end_time'].strftime('%H:00:00')
                            total_time = 0
                            for edge in shortest_path:
                                edge_id = edge.getID()
                                length = net.getEdge(edge_id).getLength()
                                speed_key = (hour, edge_id, workday)
                                speed = speed_length_data.get(speed_key, {}).get("speed", DEFAULT_TRANSFER_SPEED_MPS)
                                total_time += length / speed
                        else:
                            dx = order_b["q_x_m"] - order_a["z_x_m"]
                            dy = order_b["q_y_m"] - order_a["z_y_m"]
                            direct_distance = math.hypot(dx, dy)
                            total_time = direct_distance / DEFAULT_TRANSFER_SPEED_MPS

                        total_time = max(0, total_time)
                        time_diff = (order_b["call_time"] - order_a["end_time"]).total_seconds()
                        if time_diff >= total_time:
                            G.add_edge(f"{order_a['order_id']}_left", f"{order_b['order_id']}_right")
                            total_edges += 1
                            OK += 1
                            path_calculation_stats["successes"] += 1
                    except Exception as e:
                        logging.debug(f"调度时间计算失败: {e}")
                        continue
        
        for j, order_b in enumerate(orders):
            if (order_a["end_time"] <= order_b["call_time"] and 
                BL[j] == 0 and 
                (order_b['call_time'] - order_a['end_time']).total_seconds() > 7200):
                G.add_edge(f"{order_a['order_id']}_left", f"{order_b['order_id']}_right")
                total_edges += 1
                OK += 1
    
    end_time = time.time()
    print(f"二部图构建完成：{n}个节点，{total_edges}条边，耗时: {end_time - start_time:.2f}秒")
    print(f"路径计算统计：尝试 {path_calculation_stats['attempts']} 次，成功 {path_calculation_stats['successes']} 次")
    return G

def build_order_chains(matching: Dict) -> List[List[str]]:
    """根据最大匹配构建订单链路"""
    filtered_edges = []
    for left, right in matching.items():
        if left.endswith("_left") and right.endswith("_right"):
            left_order = left.replace("_left", "")
            right_order = right.replace("_right", "")
            filtered_edges.append((left_order, right_order))

    order_chains = [[order[0], order[1]] for order in filtered_edges]
     
    merged = True
     
    while merged:
        merged = False
        i = -1
        j = -1
        while i < (len(order_chains)-1):
            i += 1
            j = -1
            while j < (len(order_chains)-1):
                j += 1
                if i == j:
                    continue
                
                chain_i = order_chains[i]
                chain_j = order_chains[j]
                
                if (chain_i[-1] == chain_j[0]) or (chain_i[0] == chain_j[-1]):
                    if chain_i[-1] == chain_j[0]:
                        merged_chain = chain_i + chain_j[1:]
                    else:  # chain_i[0] == chain_j[-1]
                        merged_chain = chain_j[:-1] + chain_i
                    
                    order_chains[i] = merged_chain
                    order_chains.pop(j)
                    
                    if i > j:
                        i -= 1
                    
                    merged = True
                    break
    
    return order_chains

def get_time_period(dt: datetime) -> str:
    """根据时间确定时段"""
    hour = dt.hour
    if 0 <= hour < 7:
        return 'night_early'
    elif 7 <= hour < 9:
        return 'morning'
    elif 9 <= hour < 17:
        return 'midday'
    elif 17 <= hour < 20:
        return 'evening'
    else:  # 20 <= hour < 24
        return 'night_late'

def is_workday(date_str):
    """判断是否为工作日"""
    date = datetime.strptime(date_str, "%Y/%m/%d")
    return date.weekday() < 5  # 小于5为工作日（0-4）

def process_orders(
    orders: List[Dict],
    net,
    speed_length_data,
    workday,
    scenario_config: Dict[str, Any],
    run_bipartite: bool = True
) -> Dict:
    """处理订单，包括拼单和车队优化"""
    logging.info(f"开始处理 {len(orders)} 个订单...")
    
    logging.info("对订单按呼单时间排序...")
    orders.sort(key=lambda x: x['call_time'])
    logging.info(f"订单排序完成，时间范围: {orders[0]['call_time']} 到 {orders[-1]['call_time']}")
    
    logging.info("第一步：开始DW拼单...")
    logging.info("为拼单进行坐标转换...")
    orders_with_utm = convert_coords_to_meters(orders)
    logging.info(f"拼单坐标转换完成，共转换 {len(orders_with_utm)} 个订单")
    
    dw_system = create_dynamic_waiting_system(net, scenario_config)
    for i, order in enumerate(orders_with_utm):
        if i % 100 == 0:
            logging.info(f"拼单处理进度: {i}/{len(orders_with_utm)} ({i/len(orders_with_utm)*100:.1f}%)")
        dw_system.process_new_order(order)
    
    matched_pairs = dw_system.matched_pairs
    logging.info(f"DW拼单完成，得到 {len(matched_pairs)} 个拼单对")
    
    logging.info("第二步：构建优化后的订单列表...")
    optimized_orders = []
    
    for pair in matched_pairs:
        shared_order = {
            "order_id": f"shared_{pair['order_a']['order_id']}_{pair['order_b']['order_id']}",
            "start_edge": pair['order_a']['start_edge'],
            "end_edge": pair['order_b']['end_edge'],
            "start_off": pair['order_a']['start_off'],
            "end_off": pair['order_b']['end_off'],
            "call_time": min(pair['order_a']['call_time'], pair['order_b']['call_time']),
            "accept_time": min(pair['order_a']['accept_time'], pair['order_b']['accept_time']) if 'accept_time' in pair['order_a'] and 'accept_time' in pair['order_b'] else pair['order_a']['call_time'],
            "end_time": max(pair['order_a']['end_time'], pair['order_b']['end_time']),
            "q_x": pair['order_a']['q_x'],
            "q_y": pair['order_a']['q_y'],
            "z_x": pair['order_b']['z_x'],
            "z_y": pair['order_b']['z_y'],
            "q_x_m": pair['order_a']['q_x_m'],
            "q_y_m": pair['order_a']['q_y_m'],
            "z_x_m": pair['order_b']['z_x_m'],
            "z_y_m": pair['order_b']['z_y_m']
        }
        shared_order["time_period"] = get_time_period(shared_order["call_time"])
        optimized_orders.append(shared_order)
    
    matched_order_ids = set()
    for pair in matched_pairs:
        matched_order_ids.add(pair['order_a']['order_id'])
        matched_order_ids.add(pair['order_b']['order_id'])
    
    for order in orders_with_utm:
        if order['order_id'] not in matched_order_ids:
            optimized_orders.append(order)
    
    logging.info(f"优化后的订单列表构建完成，共 {len(optimized_orders)} 个订单")
    
    if run_bipartite:
        logging.info("第三步：开始车队规模优化...")
        G = build_graph_sumo(
            optimized_orders,
            net,
            speed_length_data,
            workday,
            use_sumo_paths=scenario_config["use_sumo_paths"]
        )
        logging.info("开始计算最大匹配...")
        start_time = time.time()
        left_set = {n for n, d in G.nodes(data=True) if d.get("bipartite") == 0}
        matching = nx.algorithms.bipartite.matching.maximum_matching(G, top_nodes=left_set)
        end_time = time.time()
        logging.info(f"最大匹配计算完成，耗时 {end_time - start_time:.2f} 秒")
        logging.info("第四步：构建订单链路...")
        order_chains = build_order_chains(matching)
        car_count = len(order_chains)
        total_length = sum(len(chain) for chain in order_chains)
        average_length = total_length / car_count if car_count else 0
        count_leq_5 = sum(1 for chain in order_chains if len(chain) <= 5)
        match_count = sum(1 for k in matching if k.endswith('_left'))
        fleet_size = len(optimized_orders) - match_count
    else:
        logging.info("第三步：已跳过二部图与车队优化（DW-only模式）")
        G = {}
        matching = {}
        order_chains = []
        car_count = len(optimized_orders)
        average_length = 0
        count_leq_5 = 0
        fleet_size = len(optimized_orders)
    
    logging.info(f"需要车辆: {car_count}")
    logging.info(f"链路的平均长度: {average_length}")
    logging.info(f"长度<=5的链路数量: {count_leq_5}")
    
    return {
        'original_orders': len(orders),
        'shared_orders': len(matched_pairs),
        'optimized_orders': optimized_orders,
        'optimized_fleet_size': fleet_size,
        'matching': matching,
        'graph': G,
        'order_chains': order_chains,
        'car_count': car_count,
        'average_chain_length': average_length,
        'chains_leq_5': count_leq_5,
        'matched_pairs_details': matched_pairs
    }

def load_orders():
    """加载订单数据"""
    print("加载订单数据...")
    orders_by_date = {}
    skipped_count = 0
    
    target_dates = [
        "2024/11/12", "2024/11/13", "2024/11/14", "2024/11/15", "2024/11/16", "2024/11/17", "2024/11/18",
        "2024/11/19", "2024/11/20", "2024/11/21", "2024/11/22", "2024/11/23", "2024/11/24", "2024/11/25",
        "2024/11/26", "2024/11/27", "2024/11/28", "2024/11/29", "2024/11/30", "2024/12/1", "2024/12/2",
        "2024/12/3", "2024/12/4", "2024/12/5", "2024/12/6", "2024/12/7", "2024/12/8", "2024/12/9",
        "2024/12/10", "2024/12/11", "2024/12/12"
    ]
    
    with open(traj_file, "r", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        total_rows = 0
        date_skipped = 0
        time_skipped = 0
        coord_skipped = 0
        
        for row in reader:
            total_rows += 1
            
            if "到达起点时间" in row and row["到达起点时间"]:
                order_date = row["到达起点时间"].split(" ")[0]
            else:
                date_skipped += 1
                continue
            
            if order_date not in target_dates:
                continue
                
            try:
                start_edge = row["起点边ID"]
                end_edge = row["终点边ID"]
                start_dist = float(row["起点边距离"])
                end_dist = float(row["终点边距离"])
                
                call_time = datetime.strptime(row["到达起点时间"], "%Y/%m/%d %H:%M")
                end_time = datetime.strptime(row["到达目的地时间"], "%Y/%m/%d %H:%M")
                    
            except (ValueError, TypeError) as e:
                time_skipped += 1
                if time_skipped <= 5:  # 只打印前5个错误
                    print(f"时间解析错误: {e}, 行数据: {row.get('订单号', 'N/A')}")
                continue
            
            try:
                if "接单时间" in row and row["接单时间"]:
                    accept_time = datetime.strptime(row["接单时间"], "%Y/%m/%d %H:%M")
                else:
                    accept_time = call_time  # 如果没有接单时间，使用呼单时间
            except (ValueError, TypeError):
                accept_time = call_time
            
            try:
                q_x = float(row["起点经度"]) if row["起点经度"] and row["起点经度"].strip() else 0.0
                q_y = float(row["起点纬度"]) if row["起点纬度"] and row["起点纬度"].strip() else 0.0
                z_x = float(row["终点经度"]) if row["终点经度"] and row["终点经度"].strip() else 0.0
                z_y = float(row["终点纬度"]) if row["终点纬度"] and row["终点纬度"].strip() else 0.0
            except (ValueError, TypeError) as e:
                coord_skipped += 1
                if coord_skipped <= 5:  # 只打印前5个错误
                    print(f"坐标解析错误: {e}, 行数据: {row.get('订单号', 'N/A')}")
                continue
            
            try:
                service_count = int(float(row.get("服务人次", 1) or 1))
            except (TypeError, ValueError):
                service_count = 1
            service_count = max(1, min(3, service_count))

            order = {
                "order_id": row['订单号'],
                "start_edge": start_edge,
                "end_edge": end_edge,
                "start_off": start_dist,
                "end_off": end_dist,
                "call_time": call_time,
                "end_time": end_time,
                "accept_time": accept_time,
                "q_x": q_x,
                "q_y": q_y,
                "z_x": z_x,
                "z_y": z_y,
                "service_count": service_count,
            }
            if order_date not in orders_by_date:
                orders_by_date[order_date] = []
            orders_by_date[order_date].append(order)
    
    print(f"\n数据加载统计:")
    print(f"总行数: {total_rows}")
    print(f"日期字段缺失: {date_skipped}")
    print(f"时间解析错误: {time_skipped}")
    print(f"坐标解析错误: {coord_skipped}")
    print(f"总跳过: {date_skipped + time_skipped + coord_skipped}")
    
    print("\n各日期订单统计:")
    for date in target_dates:
        orders = orders_by_date.get(date, [])
        count = len(orders)
        print(f"  {date}: {count} 条订单")
    
    return orders_by_date


def convert_timestamps(obj):
    """递归转换datetime对象为字符串"""
    if isinstance(obj, dict):
        return {k: convert_timestamps(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_timestamps(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, 'isoformat'):  # pandas.Timestamp
        return obj.isoformat()
    else:
        return obj

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="集成动态拼单与车队优化脚本")
    parser.add_argument("--dw-only", action="store_false", help="仅运行DW拼单，不运行二部图")
    args = parser.parse_args()

    print("开始处理v12数据（一个月数据，改进版集成动态拼单 - SUMO路径版）...")
    
    net = None
    speed_length_data = {}
    if not args.dw_only:
        if sumolib is None:
            raise ImportError("sumolib未安装，无法运行包含SUMO路网/二部图的流程")
        if nx is None:
            raise ImportError("networkx未安装，无法运行二部图流程")
        logging.info("开始加载路网...")
        net = sumolib.net.readNet(network_file)
        logging.info("路网加载完成")
        edge_lengths = {edge.getID(): edge.getLength() for edge in net.getEdges()}
        logging.info("开始加载速度数据...")
        with open(speed_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                edge_id = row['id_y']
                hour = row['hour']
                weekday = int(row['weekday'])
                speed = float(row['avg_speed'])
                if edge_id in edge_lengths:
                    length = edge_lengths[edge_id]
                    speed_key = (hour, edge_id, weekday)
                    speed_length_data[speed_key] = {
                        'length': length,
                        'speed': speed
                    }
        logging.info("速度数据加载完成")
    
    batch_size = 1  # 每次处理1天的数据
    print(f"将处理一个月数据")
    
    orders_by_date = load_orders()
    
    target_dates = [
        "2024/11/12", "2024/11/13", "2024/11/14", "2024/11/15", "2024/11/16", "2024/11/17", "2024/11/18",
        "2024/11/19", "2024/11/20", "2024/11/21", "2024/11/22", "2024/11/23", "2024/11/24", "2024/11/25",
        "2024/11/26", "2024/11/27", "2024/11/28", "2024/11/29", "2024/11/30", "2024/12/1", "2024/12/2",
        "2024/12/3", "2024/12/4", "2024/12/5", "2024/12/6", "2024/12/7", "2024/12/8", "2024/12/9",
        "2024/12/10", "2024/12/11", "2024/12/12"
    ]
    
    periods = [
        ("morning", 7, 10, "早高峰"),
        ("day", 10, 16, "日间"),
        ("evening", 16, 20, "晚高峰"),
        ("night", 20, 7, "夜间")  # 夜间：20:00-次日7:00（跨天）
    ]
    
    sensitivity_summary = []
    dw_only_summary = []
    for scenario_config in SENSITIVITY_CONFIGS:
        scenario_name = scenario_config["name"]
        scenario_output_folder = os.path.join(output_folder, scenario_name)
        os.makedirs(scenario_output_folder, exist_ok=True)

        print(f"\n{'#'*70}")
        print(f"开始场景: {scenario_name}")
        print(f"DW参数: 时间={scenario_config['dw_max_wait_minutes']}分钟, 空间={scenario_config['dw_max_distance_m']}米")
        print(f"调度距离模式: {'SUMO路径' if scenario_config['use_sumo_paths'] else '直线距离'}")
        print(f"{'#'*70}")

        all_results = {}
        total_orders = 0
        total_shared = 0
        total_cars = 0
        merged_passenger_distribution = {2: 0, 3: 0}
        merged_passenger_total = 0
        daily_passenger_stats = []

        for batch_start in range(0, len(target_dates), batch_size):
            batch_end = min(batch_start + batch_size, len(target_dates))
            batch_dates = target_dates[batch_start:batch_end]
            print(f"\n{'='*60}")
            print(f"处理批次 {batch_start//batch_size + 1}: {batch_dates[0]} 到 {batch_dates[-1]}")
            print(f"{'='*60}")

            for date in batch_dates:
                orders = orders_by_date.get(date, [])
                if not orders:
                    print(f"\n{date}: 无数据，跳过")
                    continue

                print(f"\n{'='*60}")
                print(f"处理日期: {date} ({len(orders)} 条订单)")
                print(f"{'='*60}")

                workday = is_workday(date)
                print(f"工作日状态: {'是' if workday else '否'}")

                daily_results = {}
                date_str = date.replace('/', '-')

                if date == "2024/11/12":
                    print(f"\n开始处理 {date} 夜间早段 (00:00-07:00)...")
                    early_night_orders = [order for order in orders if 0 <= order['call_time'].hour < 7]
                    print(f"夜间早段共 {len(early_night_orders)} 个订单")
                    if len(early_night_orders) > 0:
                        result = process_orders(
                            early_night_orders, net, speed_length_data, workday, scenario_config,
                            run_bipartite=not args.dw_only
                        )
                        if args.dw_only:
                            for pair in result['matched_pairs_details']:
                                pair_passengers = int(pair.get('total_passengers') or (
                                    int(pair['order_a'].get('service_count', 1)) + int(pair['order_b'].get('service_count', 1))
                                ))
                                merged_passenger_distribution[pair_passengers] = merged_passenger_distribution.get(pair_passengers, 0) + 1
                                merged_passenger_total += pair_passengers
                        daily_results["night_early"] = result
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        simplified_result = {
                            'original_orders': result['original_orders'],
                            'shared_orders': result['shared_orders'],
                            'optimized_fleet_size': result['optimized_fleet_size'],
                            'car_count': result['car_count'],
                            'average_chain_length': result['average_chain_length'],
                            'chains_leq_5': result['chains_leq_5'],
                            'order_chains': result['order_chains'],
                            'matched_pairs_details': result['matched_pairs_details']
                        }
                        pkl_file = f'{scenario_output_folder}/improved_fleet_optimization_v12_{date_str}_night_early_{timestamp}.pkl'
                        with open(pkl_file, 'wb') as f:
                            pickle.dump(simplified_result, f)
                        json_file = f'{scenario_output_folder}/improved_fleet_optimization_v12_{date_str}_night_early_{timestamp}.json'
                        with open(json_file, 'w', encoding='utf-8') as f:
                            json.dump(convert_timestamps(simplified_result), f, ensure_ascii=False, indent=2)
                        del result['graph']
                        del result['optimized_orders']
                    else:
                        daily_results["night_early"] = {
                            'original_orders': 0, 'shared_orders': 0, 'optimized_orders': [],
                            'optimized_fleet_size': 0, 'car_count': 0, 'average_chain_length': 0,
                            'chains_leq_5': 0, 'graph': {}, 'order_chains': [], 'matched_pairs_details': []
                        }

                for period_tag, start_hour, end_hour, period_name in periods:
                    if period_tag == "night" and date == "2024/11/12":
                        period_orders = [order for order in orders if order['call_time'].hour >= start_hour]
                    elif period_tag == "night":
                        period_orders = [order for order in orders if order['call_time'].hour >= start_hour or order['call_time'].hour < end_hour]
                    else:
                        period_orders = [order for order in orders if start_hour <= order['call_time'].hour < end_hour]

                    print(f"\n开始处理 {period_name} 时段，订单数: {len(period_orders)}")
                    if len(period_orders) > 0:
                        result = process_orders(
                            period_orders, net, speed_length_data, workday, scenario_config,
                            run_bipartite=not args.dw_only
                        )
                        if args.dw_only:
                            for pair in result['matched_pairs_details']:
                                pair_passengers = int(pair.get('total_passengers') or (
                                    int(pair['order_a'].get('service_count', 1)) + int(pair['order_b'].get('service_count', 1))
                                ))
                                merged_passenger_distribution[pair_passengers] = merged_passenger_distribution.get(pair_passengers, 0) + 1
                                merged_passenger_total += pair_passengers
                        daily_results[period_tag] = result
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        simplified_result = {
                            'original_orders': result['original_orders'],
                            'shared_orders': result['shared_orders'],
                            'optimized_fleet_size': result['optimized_fleet_size'],
                            'car_count': result['car_count'],
                            'average_chain_length': result['average_chain_length'],
                            'chains_leq_5': result['chains_leq_5'],
                            'order_chains': result['order_chains'],
                            'matched_pairs_details': result['matched_pairs_details']
                        }
                        pkl_file = f'{scenario_output_folder}/improved_fleet_optimization_v12_{date_str}_{period_tag}_{timestamp}.pkl'
                        with open(pkl_file, 'wb') as f:
                            pickle.dump(simplified_result, f)
                        json_file = f'{scenario_output_folder}/improved_fleet_optimization_v12_{date_str}_{period_tag}_{timestamp}.json'
                        with open(json_file, 'w', encoding='utf-8') as f:
                            json.dump(convert_timestamps(simplified_result), f, ensure_ascii=False, indent=2)
                        del result['graph']
                        del result['optimized_orders']
                    else:
                        daily_results[period_tag] = {
                            'original_orders': 0, 'shared_orders': 0, 'optimized_orders': [],
                            'optimized_fleet_size': 0, 'car_count': 0, 'average_chain_length': 0,
                            'chains_leq_5': 0, 'graph': {}, 'order_chains': [], 'matched_pairs_details': []
                        }

                daily_total_orders = 0
                daily_total_shared = 0
                daily_max_cars = 0
                if date == "2024/11/12" and "night_early" in daily_results:
                    result = daily_results["night_early"]
                    daily_total_orders += result['original_orders']
                    daily_total_shared += result['shared_orders']
                    daily_max_cars = max(daily_max_cars, result['car_count'])

                for period_tag, _, _, _ in periods:
                    result = daily_results[period_tag]
                    daily_total_orders += result['original_orders']
                    daily_total_shared += result['shared_orders']
                    daily_max_cars = max(daily_max_cars, result['car_count'])

                all_results[date] = daily_results
                total_orders += daily_total_orders
                total_shared += daily_total_shared
                total_cars += daily_max_cars

                daily_orders_1p = sum(1 for order in orders if int(order.get('service_count', 1)) == 1)
                daily_orders_2p = sum(1 for order in orders if int(order.get('service_count', 1)) == 2)
                daily_orders_3p = sum(1 for order in orders if int(order.get('service_count', 1)) == 3)
                daily_pairs = []
                for period_key in ("morning", "day", "evening", "night"):
                    daily_pairs.extend(daily_results.get(period_key, {}).get('matched_pairs_details', []))
                if date == "2024/11/12" and "night_early" in daily_results:
                    daily_pairs.extend(daily_results["night_early"].get('matched_pairs_details', []))

                daily_merge_1_1 = 0
                daily_merge_1_2 = 0
                for pair in daily_pairs:
                    try:
                        pa = int(pair.get('order_a', {}).get('service_count', 1))
                        pb = int(pair.get('order_b', {}).get('service_count', 1))
                    except (TypeError, ValueError):
                        pa, pb = 1, 1
                    pair_type = tuple(sorted((pa, pb)))
                    if pair_type == (1, 1):
                        daily_merge_1_1 += 1
                    elif pair_type == (1, 2):
                        daily_merge_1_2 += 1

                daily_passenger_stats.append({
                    'date': date,
                    'orders_1p': daily_orders_1p,
                    'orders_2p': daily_orders_2p,
                    'orders_3p': daily_orders_3p,
                    'merged_pairs_1p_1p': daily_merge_1_1,
                    'merged_pairs_1p_2p': daily_merge_1_2,
                    'merged_pairs_total': len(daily_pairs)
                })

        all_results['summary'] = {
            'scenario': scenario_name,
            'dw_max_wait_minutes': scenario_config['dw_max_wait_minutes'],
            'dw_max_distance_m': scenario_config['dw_max_distance_m'],
            'use_sumo_paths': scenario_config['use_sumo_paths'],
            'total_original_orders': total_orders,
            'total_shared_pairs': total_shared,
            'overall_sharing_rate': total_shared / total_orders * 100 if total_orders > 0 else 0,
            'total_cars': total_cars,
            'avg_daily_orders': total_orders / len(target_dates) if len(target_dates) > 0 else 0,
            'avg_daily_cars': total_cars / len(target_dates) if len(target_dates) > 0 else 0,
            'merged_pairs_2p': merged_passenger_distribution.get(2, 0),
            'merged_pairs_3p': merged_passenger_distribution.get(3, 0),
            'merged_passengers_total': merged_passenger_total
        }
        overall_orders_1p = sum(item['orders_1p'] for item in daily_passenger_stats)
        overall_orders_2p = sum(item['orders_2p'] for item in daily_passenger_stats)
        overall_orders_3p = sum(item['orders_3p'] for item in daily_passenger_stats)
        overall_merge_1_1 = sum(item['merged_pairs_1p_1p'] for item in daily_passenger_stats)
        overall_merge_1_2 = sum(item['merged_pairs_1p_2p'] for item in daily_passenger_stats)
        total_passengers = overall_orders_1p * 1 + overall_orders_2p * 2 + overall_orders_3p * 3
        total_original_orders = overall_orders_1p + overall_orders_2p + overall_orders_3p
        merged_pairs_count = overall_merge_1_1 + overall_merge_1_2          # 拼单总对数
        orders_in_merged = merged_pairs_count * 2
        unmatched_orders = total_original_orders - orders_in_merged
        total_orders_after_carpool = merged_pairs_count + unmatched_orders
        avg_passengers_per_order = total_passengers / total_orders_after_carpool if total_orders_after_carpool > 0 else 0
        
        all_results['daily_passenger_stats'] = daily_passenger_stats
        all_results['passenger_stats_overall'] = {
            'orders_1p': overall_orders_1p,
            'orders_2p': overall_orders_2p,
            'orders_3p': overall_orders_3p,
            'merged_pairs_1p_1p': overall_merge_1_1,
            'merged_pairs_1p_2p': overall_merge_1_2,
            'avg_passengers_per_order': avg_passengers_per_order,
            'total_orders_after_carpool': total_orders_after_carpool
        }
        
        scenario_result_file = os.path.join(scenario_output_folder, f"scenario_result_{scenario_name}.json")
        with open(scenario_result_file, "w", encoding="utf-8") as f:
            json.dump(convert_timestamps(all_results), f, ensure_ascii=False, indent=2)
        
        sensitivity_summary.append(all_results['summary'])
        
        if args.dw_only:
            dw_only_summary.append({
                'scenario': scenario_name,
                'dw_max_wait_minutes': scenario_config['dw_max_wait_minutes'],
                'dw_max_distance_m': scenario_config['dw_max_distance_m'],
                'use_sumo_paths': scenario_config['use_sumo_paths'],
                'merged_pairs_total': all_results['summary']['total_shared_pairs'],
                'merged_pairs_2p': all_results['summary']['merged_pairs_2p'],
                'merged_pairs_3p': all_results['summary']['merged_pairs_3p'],
                'merged_passengers_total': all_results['summary']['merged_passengers_total'],
                'orders_1p': overall_orders_1p,
                'orders_2p': overall_orders_2p,
                'orders_3p': overall_orders_3p,
                'merged_pairs_1p_1p': overall_merge_1_1,
                'merged_pairs_1p_2p': overall_merge_1_2,
                'avg_passengers_per_order': avg_passengers_per_order,
                'total_orders_after_carpool': total_orders_after_carpool
            })
        print(f"场景完成: {scenario_name}，结果写入 {scenario_result_file}")
        print("每日统计（订单1/2/3人，融合1+1/1+2）：")
        for row in daily_passenger_stats:
            print(
                f"  {row['date']}: 1人={row['orders_1p']}, 2人={row['orders_2p']}, 3人={row['orders_3p']}, "
                f"1+1={row['merged_pairs_1p_1p']}, 1+2={row['merged_pairs_1p_2p']}"
            )
        print(
            "整体统计: "
            f"1人={overall_orders_1p}, 2人={overall_orders_2p}, 3人={overall_orders_3p}, "
            f"1+1={overall_merge_1_1}, 1+2={overall_merge_1_2}"
        )
        print(f"拼单后平均每单人数: {avg_passengers_per_order:.3f} 人/单")
        print(f"拼单后总订单数（车辆任务数）: {total_orders_after_carpool}")
        
        if args.dw_only:
            print(f"[DW_ONLY] 场景 {scenario_name} 拼单人数统计："
                  f"2人融合单={all_results['summary']['merged_pairs_2p']}，"
                  f"3人融合单={all_results['summary']['merged_pairs_3p']}，"
                  f"融合订单总乘客数={all_results['summary']['merged_passengers_total']}")
        
        if args.dw_only:
            continue
    sensitivity_file = os.path.join(output_folder, "sensitivity_summary.json")
    with open(sensitivity_file, "w", encoding="utf-8") as f:
        json.dump(sensitivity_summary, f, ensure_ascii=False, indent=2)

    csv_file = os.path.join(output_folder, "sensitivity_summary.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(sensitivity_summary[0].keys()) if sensitivity_summary else [])
        if sensitivity_summary:
            writer.writeheader()
            writer.writerows(sensitivity_summary)

    print(f"\n灵敏度分析完成。")
    print(f"汇总JSON: {sensitivity_file}")
    print(f"汇总CSV: {csv_file}")
    print(f"所有场景结果保存在 {output_folder} 文件夹中")
    if args.dw_only:
        dw_only_file = os.path.join(output_folder, "dw_only_merged_passenger_summary.json")
        with open(dw_only_file, "w", encoding="utf-8") as f:
            json.dump(dw_only_summary, f, ensure_ascii=False, indent=2)
        print(f"[DW_ONLY] 融合单人数统计写入: {dw_only_file}")

if __name__ == "__main__":
    main()
