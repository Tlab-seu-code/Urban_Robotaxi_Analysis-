import pickle
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import seaborn as sns
from collections import defaultdict
import glob
import csv

# 设置字体和样式
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['axes.unicode_minus'] = False
plt.style.use('seaborn-v0_8')

def load_data_from_pkl_files(data_dir):
    """从pkl文件加载数据"""
    all_data = []
    
    # 获取所有pkl文件并按文件名排序（确保时间顺序）
    pkl_files = glob.glob(os.path.join(data_dir, "*.pkl"))
    pkl_files.sort()  # 按文件名排序，确保时间顺序
    
    for file_path in pkl_files:
        try:
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            # 从文件名提取信息
            filename = os.path.basename(file_path)
            
            # 使用正则表达式提取日期和时间段
            import re
            # 匹配格式: improved_fleet_optimization_2024-11-12_night_early_20250916_184257.pkl
            # 或者: improved_fleet_optimization_2024-12-1_evening_20250916_234358.pkl
            pattern = r'improved_fleet_optimization_(\d{4}-\d{1,2}-\d{1,2})_([^_]+(?:_[^_]+)?)_\d{8}_\d{6}\.pkl'
            match = re.match(pattern, filename)
            
            if match:
                date_str = match.group(1)
                time_period = match.group(2)
                
                # 解析日期
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                
                # 优先处理11月份的数据，但如果有其他月份也处理
                if date_obj.month == 11:
                    print(f"Processing {filename} - November data (month {date_obj.month})")
                else:
                    print(f"Processing {filename} - non-November data (month {date_obj.month})")
                
                weekday = date_obj.strftime('%A')
                weekday_short = date_obj.strftime('%A')  # 使用全称英文
            else:
                print(f"Could not parse filename: {filename}")
                continue
            
            # 检查数据是否有效
            if not data or not isinstance(data, dict):
                print(f"Skipping {filename} - invalid data format")
                continue
                
            # 检查数据格式并标记
            has_matching = 'matching' in data
            has_optimized_orders = 'optimized_orders' in data
            has_order_chains = 'order_chains' in data
            
            # 确定数据格式
            if has_matching and has_optimized_orders:
                data_format = "complete"  # 完整数据
                print(f"Processing {filename} - complete data format")
            elif has_order_chains:
                data_format = "chains_only"  # 只有order_chains
                print(f"Processing {filename} - chains_only data format")
            else:
                print(f"Skipping {filename} - no usable data format")
                print(f"Available keys: {list(data.keys())}")
                continue
            
            # 将时间段信息添加到数据中
            data['time_period'] = time_period
            
            all_data.append({
                'file_path': file_path,
                'date': date_obj,
                'date_str': date_str,
                'weekday': weekday,
                'weekday_short': weekday_short,
                'time_period': time_period,
                'data_format': data_format,
                'data': data
            })
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            continue
    
    return all_data

def generate_matching_from_order_chains(data):
    """从order_chains生成matching数据，参考bi_2_ori.py和bi_3_ori.py的逻辑"""
    matching = {}
    
    if 'order_chains' not in data:
        print("No order_chains found, cannot generate matching")
        return matching
    
    order_chains = data['order_chains']
    
    # 为每个订单链生成车辆ID和对应的订单列表
    for i, chain in enumerate(order_chains):
        if isinstance(chain, list) and len(chain) > 0:
            vehicle_id = f"vehicle_{i}_left"
            # 为每个订单创建left和right节点
            order_ids = []
            for j, order_id in enumerate(chain):
                if j < len(chain) - 1:  # 不是最后一个订单
                    order_ids.append(f"{order_id}_left")
                else:  # 最后一个订单
                    order_ids.append(f"{order_id}_left")
            
            matching[vehicle_id] = order_ids
    
    print(f"Generated matching for {len(matching)} vehicles from {len(order_chains)} order chains")
    return matching

def extract_vehicle_operation_times(data, data_format="complete"):
    """提取车辆运营时间数据"""
    vehicle_ops = []
    
    try:
        print(f"  Available keys: {list(data.keys())}")
        print(f"  Data format: {data_format}")
        
        # 根据数据格式分别处理
        if data_format == "complete":
            # 处理完整数据格式（matching + optimized_orders）
            if 'matching' in data and 'optimized_orders' in data:
                print(f"  Processing complete data format...")
                # 使用完整的matching数据
                matching = data['matching']
                optimized_orders = data['optimized_orders']
                
                print(f"  Matching data: {len(matching) if matching else 0} vehicles")
                print(f"  Optimized orders: {len(optimized_orders) if optimized_orders else 0} orders")
                
                if matching and optimized_orders:
                       # 创建订单ID到订单信息的映射
                       order_map = {}
                       for order in optimized_orders:
                           if isinstance(order, dict) and 'order_id' in order:
                               order_map[order['order_id']] = order
                           elif isinstance(order, str):
                               order_map[order] = {
                                   'order_id': order,
                                   'call_time': None,
                                   'end_time': None
                               }
                       
                       print(f"  Created order_map with {len(order_map)} orders")
                       print(f"  Sample order_map keys: {list(order_map.keys())[:3]}")
                       print(f"  Sample matching values: {list(matching.values())[0] if matching else 'None'}")
                       
                       # 统计每辆车的运营时间
                       for vehicle_id, order_ids in matching.items():
                           if not order_ids:
                               continue
                               
                           # 获取该车辆的所有订单
                           vehicle_orders = []
                           for order_id in order_ids:
                               # 去掉_left和_right后缀
                               clean_order_id = order_id.replace('_left', '').replace('_right', '')
                               if clean_order_id in order_map:
                                   vehicle_orders.append(order_map[clean_order_id])
                               else:
                                   # 尝试直接匹配
                                   if order_id in order_map:
                                       vehicle_orders.append(order_map[order_id])
                           
                           if not vehicle_orders:
                               continue
                           
                           # 过滤掉没有时间信息的订单
                           valid_orders = [order for order in vehicle_orders if order.get('accept_time') and order.get('end_time')]
                           
                           if not valid_orders:
                               continue
                               
                           # 计算该车辆的运营时间范围
                           # 使用accept_time作为车辆开始运营时间，end_time作为结束时间
                           start_times = [order['accept_time'] for order in valid_orders]
                           end_times = [order['end_time'] for order in valid_orders]
                           
                           vehicle_start = min(start_times)
                           vehicle_end = max(end_times)
                           
                           # 计算运营时长（小时）
                           operation_duration = (vehicle_end - vehicle_start).total_seconds() / 3600
                           
                           vehicle_ops.append({
                               'vehicle_id': vehicle_id,
                               'start_time': vehicle_start,
                               'end_time': vehicle_end,
                               'operation_duration': operation_duration,
                               'trip_count': len(valid_orders),
                               'start_hour': vehicle_start.hour + vehicle_start.minute / 60.0,
                               'end_hour': vehicle_end.hour + vehicle_end.minute / 60.0
                           })
                           print(f"  Added vehicle {vehicle_id}: {vehicle_start} to {vehicle_end}")
                       
                       print(f"  Extracted {len(vehicle_ops)} vehicles from complete data")
        
        elif data_format == "chains_only":
            # 处理只有order_chains的数据格式
            print(f"  Processing chains_only data format...")
            if 'order_chains' in data:
                order_chains = data['order_chains']
                print(f"  Found {len(order_chains)} order chains")
                
                # 为每个order_chain创建车辆运营信息
                for i, chain in enumerate(order_chains):
                    if isinstance(chain, list) and len(chain) > 0:
                        vehicle_id = f"vehicle_{i}"
                        
                        # 直接使用chain长度作为行程数
                        vehicle_ops.append({
                            'vehicle_id': vehicle_id,
                            'start_time': None,
                            'end_time': None,
                            'operation_duration': 0,
                            'trip_count': len(chain),
                            'start_hour': 0,
                            'end_hour': 0
                        })
                        print(f"  Added vehicle {vehicle_id}: {len(chain)} trips")
                
                print(f"  Extracted {len(vehicle_ops)} vehicles from order_chains")
            else:
                print(f"Warning: 没有order_chains数据，跳过处理")
                return []
        
        else:
            print(f"Warning: No usable data found. Available keys: {list(data.keys())}")
    
    except Exception as e:
        print(f"Error in extract_vehicle_operation_times: {e}")
        print(f"Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
    
    return vehicle_ops

# 移除这个函数，不再根据时间段限制车辆运营时间

def load_v12_order_times(v12_file_path):
    """从v12文件中加载订单时间信息"""
    order_times = {}
    try:
        with open(v12_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                order_id = row.get('订单号', '')
                if order_id:
                    try:
                        call_time = datetime.strptime(row['到达起点时间'], '%Y-%m-%d %H:%M:%S')
                        end_time = datetime.strptime(row['到达目的地时间'], '%Y-%m-%d %H:%M:%S')
                        accept_time = None
                        if '接单时间' in row and row['接单时间']:
                            accept_time = datetime.strptime(row['接单时间'], '%Y-%m-%d %H:%M:%S')
                        
                        order_times[order_id] = {
                            'call_time': call_time,
                            'accept_time': accept_time,
                            'end_time': end_time
                        }
                    except Exception as e:
                        continue
    except Exception as e:
        print(f"Error loading v12 file {v12_file_path}: {e}")
    
    return order_times

def create_operation_time_distribution_plot(all_data, output_dir='extended_data_fig5_plots'):
    """创建运营时间分布图 (图b) - 横向排列的一周格式，模仿论文小图格式"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 添加时间后缀避免覆盖
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 按星期几分组数据，合并所有月份的数据
    weekday_data = defaultdict(list)
    
    for data_item in all_data:
        weekday = data_item['weekday_short']
        data_format = data_item['data_format']
        vehicle_ops = extract_vehicle_operation_times(data_item['data'], data_format)
        
        for vehicle_op in vehicle_ops:
            # 只处理有时间信息的车辆
            if vehicle_op['start_hour'] > 0 or vehicle_op['end_hour'] > 0:
                weekday_data[weekday].append({
                    'start_hour': vehicle_op['start_hour'],
                    'end_hour': vehicle_op['end_hour'],
                    'operation_duration': vehicle_op['operation_duration'],
                    'date': data_item['date_str']
                })
    
    # 创建子图 - 1 行×7 列横向排列，使用正方形画布（进一步缩小）
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # 正方形画布：进一步缩小，每个子图宽高相等
    fig, axes = plt.subplots(1, 7, figsize=(24.5, 3.5))
    
    # 颜色方案：红橙黄绿蓝靛紫景点配色
    weekday_colors = {
        'Monday': '#E74C3C',    # 红
        'Tuesday': '#F39C12',   # 橙
        'Wednesday': '#F1C40F', # 黄
        'Thursday': '#2ECC71',  # 绿
        'Friday': '#3498DB',    # 蓝
        'Saturday': '#9B59B6',  # 靛/紫
        'Sunday': '#E91E63'     # 紫/粉
    }
    
    for i, weekday in enumerate(weekdays):
        ax = axes[i]
        
        if weekday in weekday_data and weekday_data[weekday]:
            # 合并该天所有时段的数据
            all_hours = []
            for d in weekday_data[weekday]:
                # 为每个车辆创建运营时间序列
                start_h = d['start_hour']
                end_h = d['end_hour']
                # 如果跨天，处理为两个部分
                if end_h < start_h:
                    all_hours.extend(np.arange(start_h, 24, 0.1))
                    all_hours.extend(np.arange(0, end_h, 0.1))
                else:
                    all_hours.extend(np.arange(start_h, end_h, 0.1))
            
            # 绘制密度图
            if all_hours:
                # 使用更平滑的核密度估计
                from scipy import stats
                
                # 创建更密集的时间点用于平滑
                x_smooth = np.linspace(0, 24, 1000)
                
                # 使用高斯核密度估计
                kde = stats.gaussian_kde(all_hours, bw_method=0.3)  # 调整带宽使曲线更平滑
                density = kde(x_smooth)
                
                # 绘制平滑的面积图
                ax.fill_between(x_smooth, density, alpha=0.7, color=weekday_colors[weekday])
                ax.set_xlim(0, 24)
                ax.set_ylim(0, max(density) * 1.1)
            else:
                # 没有数据时显示空白
                ax.set_xlim(0, 24)
                ax.set_ylim(0, 0.04)
        else:
            # 没有数据时显示空白
            ax.set_xlim(0, 24)
            ax.set_ylim(0, 0.04)
        
        # 设置坐标轴
        ax.set_xlim(0, 24)
        ax.set_ylim(0, 0.04)  # 根据论文图片调整 Y 轴范围
        
        # 设置 X 轴标签（字号进一步增大）
        ax.set_xticks([0, 4, 8, 12, 16, 20, 24])
        ax.set_xticklabels(['0', '4', '8', '12', '16', '20', '24'], fontsize=14, fontweight='bold')
        
        # 设置 Y 轴标签（字号进一步增大）
        ax.set_yticks([0, 0.01, 0.02, 0.03, 0.04])
        ax.set_yticklabels(['0.00', '0.01', '0.02', '0.03', '0.04'], fontsize=14, fontweight='bold')
        
        # 设置标题（字号进一步增大）
        ax.set_title(weekday, fontsize=18, fontweight='bold')
        
        # 添加网格（加粗）
        ax.grid(True, alpha=0.4, linewidth=1.5)
        
        # 只在第一个子图显示 Y 轴标签（字号进一步增大）
        if i == 0:
            ax.set_ylabel('Density', fontsize=16, fontweight='bold')
        else:
            ax.set_ylabel('')
    
    # 添加 X 轴总标签（字号进一步增大）
    fig.text(0.5, 0.02, 'Time of Operation (hour)', ha='center', fontsize=18, fontweight='bold')
    
    # 添加子图标签（字号进一步增大）
    fig.text(0.02, 0.95, 'b', fontsize=22, fontweight='bold')
    
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)
    plt.savefig(os.path.join(output_dir, f'operation_time_distribution_{timestamp}.pdf'), dpi=300, bbox_inches='tight')
    plt.show()

def create_lorenz_curves_plot(all_data, output_dir='extended_data_fig5_plots'):
    """创建Lorenz曲线图 (图c)"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 添加时间后缀避免覆盖
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 按星期几分组数据，合并同一天的所有时段
    weekday_data = defaultdict(list)
    
    # 先按日期和星期分组
    daily_data = defaultdict(lambda: defaultdict(list))
    
    for data_item in all_data:
        weekday = data_item['weekday_short']
        date_str = data_item['date_str']
        data_format = data_item['data_format']
        vehicle_ops = extract_vehicle_operation_times(data_item['data'], data_format)
        
        # 统计每辆车的服务行程数
        vehicle_trips = {}
        for vehicle_op in vehicle_ops:
            vehicle_trips[vehicle_op['vehicle_id']] = vehicle_op['trip_count']
        
        if vehicle_trips:
            daily_data[date_str][weekday].append({
                'vehicle_trips': vehicle_trips,
                'total_trips': sum(vehicle_trips.values()),
                'total_vehicles': len(vehicle_trips),
                'time_period': data_item['time_period']
            })
    
    # 合并同一天所有时段的数据
    for date_str, weekday_periods in daily_data.items():
        for weekday, period_data in weekday_periods.items():
            # 合并该天该星期的所有时段
            combined_vehicle_trips = {}
            total_trips = 0
            total_vehicles = set()
            
            for period_info in period_data:
                for vehicle_id, trip_count in period_info['vehicle_trips'].items():
                    if vehicle_id in combined_vehicle_trips:
                        combined_vehicle_trips[vehicle_id] += trip_count
                    else:
                        combined_vehicle_trips[vehicle_id] = trip_count
                    total_vehicles.add(vehicle_id)
                total_trips += period_info['total_trips']
            
            if combined_vehicle_trips:
                weekday_data[weekday].append({
                    'vehicle_trips': combined_vehicle_trips,
                    'total_trips': total_trips,
                    'total_vehicles': len(total_vehicles),
                    'date': date_str
                })
    
    # 创建子图 - 使用正方形画布（进一步缩小）
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    fig, axes = plt.subplots(1, 7, figsize=(24.5, 3.5))
    
    # 颜色方案：红橙黄绿蓝靛紫景点配色
    colors = ['#E74C3C', '#F39C12', '#F1C40F', '#2ECC71', '#3498DB', '#9B59B6', '#E91E63']
    
    for i, weekday in enumerate(weekdays):
        ax = axes[i]
        
        if weekday in weekday_data and weekday_data[weekday]:
            # 为每个日期创建 Lorenz 曲线
            for date_data in weekday_data[weekday]:
                vehicle_trips = date_data['vehicle_trips']
                total_trips = date_data['total_trips']
                total_vehicles = date_data['total_vehicles']
                
                if total_trips == 0 or total_vehicles == 0:
                    continue
                
                # 按行程数排序车辆
                sorted_vehicles = sorted(vehicle_trips.items(), key=lambda x: x[1], reverse=True)
                
                # 计算累积百分比
                cumulative_trips = 0
                cumulative_vehicles = 0
                x_points = [0]
                y_points = [0]
                
                for j, (vehicle_id, trip_count) in enumerate(sorted_vehicles):
                    cumulative_trips += trip_count
                    cumulative_vehicles += 1
                    
                    x_points.append(cumulative_vehicles / total_vehicles * 100)
                    y_points.append(cumulative_trips / total_trips * 100)
                
                # 绘制曲线（加粗线条）
                ax.plot(x_points, y_points, color=colors[i], alpha=0.7, linewidth=2)
        else:
            print(f"No data available for {weekday}")
        
        # 绘制对角线（完美平等线，加粗）
        ax.plot([0, 100], [0, 100], 'k--', alpha=0.5, linewidth=2)
        
        ax.set_title(f'{weekday}', fontsize=18, fontweight='bold')
        ax.set_xlabel('Vehicles Used (%)', fontsize=16, fontweight='bold')
        ax.set_ylabel('Trips Served (%)', fontsize=16, fontweight='bold')
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.4, linewidth=1.5)
        
        # 设置刻度（字号进一步增大）
        ax.set_xticks(range(0, 101, 20))
        ax.set_yticks(range(0, 101, 20))
        ax.tick_params(axis='both', labelsize=14, width=1.5)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'lorenz_curves_{timestamp}.pdf'), dpi=300, bbox_inches='tight')
    plt.show()

def main():
    """主函数"""
    data_dir = "improved_integrated_results"
    
    print("Loading data from pkl files...")
    all_data = load_data_from_pkl_files(data_dir)
    print(f"Loaded {len(all_data)} data files")
    
    if not all_data:
        print("No data files found!")
        return
    
    # 打印一些调试信息
    print("Sample data structure:")
    for i, data_item in enumerate(all_data[:3]):
        print(f"  File {i+1}: {data_item['date_str']} {data_item['weekday_short']} {data_item['time_period']}")
    
    print("Creating operation time distribution plot...")
    create_operation_time_distribution_plot(all_data)
    
    print("Creating Lorenz curves plot...")
    create_lorenz_curves_plot(all_data)
    
    print("Plots saved to 'extended_data_fig5_plots' directory")

if __name__ == "__main__":
    main()
