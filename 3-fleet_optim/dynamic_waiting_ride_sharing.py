try:
    import pandas as pd
except ImportError:
    pd = None
import math
from datetime import datetime
import pickle
import os
from typing import List, Dict, Optional
import logging
try:
    import sumolib
except ImportError:
    sumolib = None
import csv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

traj_file = "v12-traj.csv"
speed_file = "speed_filled_step1.csv"
network_file = "robust.net.xml"
output_folder = "ride_sharing_results"
os.makedirs(output_folder, exist_ok=True)

WALKING_RADIUS_METERS = 500
DEFAULT_MAX_CAPACITY = 3

def is_workday(date_obj):
    """判断是否为工作日"""
    return date_obj.weekday() < 5

class DynamicWaitingRideSharing:
    def __init__(
        self,
        net,
        max_wait_time_minutes: float = 5,
        max_wait_distance_meters: float = WALKING_RADIUS_METERS,
        max_vehicle_capacity: int = DEFAULT_MAX_CAPACITY
    ):
        self.waiting_orders: List[Dict] = []
        self.matched_pairs: List[Dict] = []
        self.total_orders = 0
        self.net = net
        self.distance_cache = {}
        self.max_wait_time_minutes = max_wait_time_minutes
        self.max_wait_distance_meters = max_wait_distance_meters
        self.max_wait_time_seconds = max_wait_time_minutes * 60
        self.max_vehicle_capacity = max_vehicle_capacity

    @staticmethod
    def get_order_passengers(order: Dict) -> int:
        """读取订单服务人数，默认1人。"""
        passengers = order.get('service_count', 1)
        try:
            passengers = int(passengers)
        except (TypeError, ValueError):
            passengers = 1
        return max(1, passengers)
    
    def calculate_distance(self, order1: Dict, order2: Dict) -> float:
        """使用路网中的实际距离计算两个订单间的距离，带缓存"""
        try:
            edge_pair1 = (order1['start_edge'], order2['start_edge'])
            edge_pair2 = (order1['end_edge'], order2['end_edge'])
            
            if edge_pair1 in self.distance_cache:
                start_distance = self.distance_cache[edge_pair1]
            else:
                start_edge1 = self.net.getEdge(order1['start_edge'])
                start_edge2 = self.net.getEdge(order2['start_edge'])
                start_path = self.net.getShortestPath(start_edge1, start_edge2)[0]
                if start_path:
                    start_distance = sum(edge.getLength() for edge in start_path)
                else:
                    start_distance = float('inf')
                self.distance_cache[edge_pair1] = start_distance
            
            if edge_pair2 in self.distance_cache:
                end_distance = self.distance_cache[edge_pair2]
            else:
                end_edge1 = self.net.getEdge(order1['end_edge'])
                end_edge2 = self.net.getEdge(order2['end_edge'])
                end_path = self.net.getShortestPath(end_edge1, end_edge2)[0]
                if end_path:
                    end_distance = sum(edge.getLength() for edge in end_path)
                else:
                    end_distance = float('inf')
                self.distance_cache[edge_pair2] = end_distance
            return min(start_distance, end_distance)
            
        except Exception:
            point1 = (order1['q_x'], order1['q_y'])
            point2 = (order2['q_x'], order2['q_y'])
            return math.hypot(point1[0] - point2[0], point1[1] - point2[1]) * 111000
    
    def quick_distance_check(self, order1: Dict, order2: Dict) -> float:
        """快速距离检查，使用经纬度距离进行预筛选"""
        point1 = (order1['q_x'], order1['q_y'])
        point2 = (order2['q_x'], order2['q_y'])
        return math.hypot(point1[0] - point2[0], point1[1] - point2[1]) * 111000
    
    def process_new_order(self, new_order: Dict) -> Optional[Dict]:
        """处理新订单"""
        self.total_orders += 1
        time_window_orders = []
        for waiting_order in self.waiting_orders:
            waiting_time = (new_order['call_time'] - waiting_order['call_time']).total_seconds()
            if waiting_time <= self.max_wait_time_seconds:
                time_window_orders.append(waiting_order)
        
        if not time_window_orders:
            self.waiting_orders.append(new_order)
            return None
            
        for waiting_order in time_window_orders:
            quick_distance = self.quick_distance_check(new_order, waiting_order)
            if quick_distance > self.max_wait_distance_meters * 1.5:
                continue
            distance = self.calculate_distance(new_order, waiting_order)
            if distance <= self.max_wait_distance_meters:
                total_passengers = self.get_order_passengers(new_order) + self.get_order_passengers(waiting_order)
                if total_passengers > self.max_vehicle_capacity:
                    continue
                waiting_time = (new_order['call_time'] - waiting_order['call_time']).total_seconds()
                match_pair = {
                    'order_a': new_order,
                    'order_b': waiting_order,
                    'match_time': new_order['call_time'],
                    'waiting_time': waiting_time,
                    'distance': distance,
                    'total_passengers': total_passengers
                }
                self.matched_pairs.append(match_pair)
                self.waiting_orders.remove(waiting_order)
                return match_pair
        
        self.waiting_orders.append(new_order)
        return None
    
    def check_waiting_orders(self, current_time: datetime) -> List[Dict]:
        """检查等待中的订单，移除超时的订单"""
        expired_orders = []
        
        for order in self.waiting_orders[:]:
            waiting_time = (current_time - order['call_time']).total_seconds()
            if waiting_time > self.max_wait_time_seconds:
                expired_orders.append(order)
                self.waiting_orders.remove(order)
        
        return expired_orders
    
    def save_results(self, output_file: str):
        """保存匹配结果"""
        results = {
            'matched_pairs': self.matched_pairs,
            'waiting_orders': self.waiting_orders,
            'total_orders': self.total_orders
        }
        
        with open(output_file, 'wb') as f:
            pickle.dump(results, f)
        
        logging.info(f"结果已保存到 {output_file}")

def main():
    os.makedirs(output_folder, exist_ok=True)
    if pd is None:
        raise ImportError("pandas未安装，无法运行示例入口")
    if sumolib is None:
        raise ImportError("sumolib未安装，无法运行示例入口")

    print("开始加载路网...")
    net = sumolib.net.readNet(network_file)
    print("路网加载完成.")

    print("构建边长度字典...")
    edge_lengths = {edge.getID(): edge.getLength() for edge in net.getEdges()}
    print(f"边长度字典构建完成，共 {len(edge_lengths)} 条边.")

    print("加载速度数据...")
    speed_length_data = {}
    try:
        with open(speed_file, 'r') as f:
            reader = csv.DictReader(f)
            print("CSV文件列名:", reader.fieldnames)
            for row in reader:
                edge_id = row['id_y']
                hour = row['hour']
                weekday = row['weekday'] == 'True'
                speed = float(row['avg_speed'])
                
                if edge_id in edge_lengths:
                    length = edge_lengths[edge_id]
                    speed_key = (hour, edge_id, weekday)
                    speed_length_data[speed_key] = {
                        'length': length,
                        'speed': speed
                    }
        print(f"速度数据加载完成，共 {len(speed_length_data)} 条记录.")
    except Exception as e:
        print(f"加载速度数据时出错: {e}")
        print("请检查速度数据文件的格式和列名")
        return

    print("加载并处理订单数据...")
    try:
        df = pd.read_csv(traj_file)
        df['呼单时间'] = pd.to_datetime(df['呼单时间'])
        df['接单时间'] = pd.to_datetime(df['接单时间'])
        df['到达起点时间'] = pd.to_datetime(df['到达起点时间'])
        df['到达目的地时间'] = pd.to_datetime(df['到达目的地时间'])
        target_date = '2024-11-12'
        df = df[df['呼单时间'].dt.date == pd.to_datetime(target_date).date()]
        
        print(f"2024-11-12 共有 {len(df)} 个订单")
        
        dw_system = DynamicWaitingRideSharing(net)

        orders = []
        for _, row in df.iterrows():
            try:
                start_edge = str(row['起点边ID'])
                end_edge = str(row['终点边ID'])

                if start_edge not in edge_lengths or end_edge not in edge_lengths:
                    continue

                order = {
                    "order_id": str(row['订单号']),
                    "start_edge": start_edge,
                    "end_edge": end_edge,
                    "start_off": float(row['起点边距离']),
                    "end_off": float(row['终点边距离']),
                    "call_time": row['呼单时间'],
                    "end_time": row['到达目的地时间'],
                    "q_x": float(row['起点经度']),
                    "q_y": float(row['起点纬度']),
                    "z_x": float(row['终点经度']),
                    "z_y": float(row['终点纬度'])
                }
                orders.append(order)
            except (ValueError, KeyError) as e:
                print(f"处理订单时出错: {e}")
                continue

        print(f"订单数据加载完成，共 {len(orders)} 条有效订单")
        
        orders.sort(key=lambda x: x['call_time'])
        print("订单已按时间排序")

        print("开始处理订单匹配...")
        for i, order in enumerate(orders):
            if i % 100 == 0:
                print(f"处理进度: {i}/{len(orders)} ({i/len(orders)*100:.1f}%)")
            dw_system.check_waiting_orders(order['call_time'])
            dw_system.process_new_order(order)
        
        print(f"处理完成！共处理 {len(orders)} 个订单")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f'ride_sharing_results/dw_ride_sharing_20241112_{timestamp}.pkl'
        dw_system.save_results(output_file)
        
        print(f"\n拼单完成！共找到 {len(dw_system.matched_pairs)} 个拼单对")
        print(f"结果已保存到 {output_file}")

        print("\n处理完成！所有结果已保存到", output_folder)

    except Exception as e:
        print(f"加载订单数据时发生错误: {e}")
        return

if __name__ == "__main__":
    main() 
