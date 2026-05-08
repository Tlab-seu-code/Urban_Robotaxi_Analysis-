import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import matplotlib.dates as mdates
from collections import defaultdict
import glob
import os
from scipy.interpolate import interp1d

def load_orders_from_csv(date_str, csv_file='v12-traj.csv'):
    """从CSV文件加载指定日期的订单数据"""
    try:
        df = pd.read_csv(csv_file)
        
        csv_date = date_str.replace('-', '/')
        
        day_data = df[df['日期'] == csv_date].copy()
        
        if len(day_data) == 0:
            print(f"CSV中未找到 {csv_date} 的数据")
            return [], []
        
        print(f"从CSV加载 {csv_date} 的数据: {len(day_data)} 个订单")
        
        orders = []
        for _, row in day_data.iterrows():
            try:
                call_time = pd.to_datetime(row['到达起点时间']) if pd.notna(row['到达起点时间']) else None
                accept_time = pd.to_datetime(row['接单时间']) if pd.notna(row['接单时间']) else None
                end_time = pd.to_datetime(row['到达目的地时间']) if pd.notna(row['到达目的地时间']) else None
                
                if call_time and accept_time and end_time:
                    order = {
                        'order_id': row['订单号'],
                        'call_time': call_time,
                        'accept_time': accept_time,
                        'end_time': end_time,
                        'start_edge': row.get('起点边ID', ''),
                        'end_edge': row.get('终点边ID', ''),
                        'time_period': 'csv_data'
                    }
                    orders.append(order)
            except Exception as e:
                print(f"处理订单 {row['订单号']} 时出错: {e}")
                continue
        
        print(f"成功处理 {len(orders)} 个有效订单")
        
        order_chains = []
        for order in orders:
            order_chains.append([order['order_id']])
        
        return orders, order_chains
        
    except Exception as e:
        print(f"从CSV加载数据失败: {e}")
        return [], []

def load_daily_data(data_dir, date_str):
    """加载单天的数据"""
    time_periods = ['night_early', 'morning', 'midday', 'evening', 'night_late']
    
    daily_orders = []
    daily_chains = []
    daily_car_counts = []
    period_car_counts = {}
    
    print(f"使用标准时段划分: {time_periods}")
    
    if date_str in ['2024-11-23', '2024-11-24']:
        print(f"检测到 {date_str}，从CSV文件加载订单数据，从pkl文件加载order_chains")
        orders, _ = load_orders_from_csv(date_str)
        
        if orders:
            daily_orders.extend(orders)
            
            for period in time_periods:
                pattern = f"{data_dir}/*{date_str}*{period}*.pkl"
                files = glob.glob(pattern)
                if files:
                    try:
                        with open(files[0], 'rb') as f:
                            data = pickle.load(f)
                        
                        if 'order_chains' in data:
                            chains = data['order_chains']
                            daily_chains.extend(chains)
                            print(f"  {period}: 添加了 {len(chains)} 个订单链")
                        
                        if 'car_count' in data:
                            car_count = data['car_count']
                            daily_car_counts.append(car_count)
                            period_car_counts[period] = car_count
                            print(f"  {period}: 车辆数 {car_count}")
                    except Exception as e:
                        print(f"  加载pkl文件失败: {e}")
            
            max_fleet_size = max(daily_car_counts) if daily_car_counts else len(orders)
            avg_car_count = sum(daily_car_counts) / len(daily_car_counts) if daily_car_counts else len(orders)
            
            print(f"{date_str} 混合数据: {len(orders)} 个订单, {len(daily_chains)} 个订单链, 最大车队规模: {max_fleet_size}")
            return daily_orders, daily_chains, max_fleet_size, avg_car_count, period_car_counts
        else:
            print(f"{date_str}: 无法从CSV加载数据")
            return [], [], 0, 0, {}
    
    for period in time_periods:
        pattern = f"{data_dir}/*{date_str}*{period}*.pkl"
        files = glob.glob(pattern)
        
        if files:
            file_path = files[0]
            print(f"加载文件: {file_path}")
            
            try:
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)
                
                if 'optimized_orders' in data:
                    orders = data['optimized_orders']
                    daily_orders.extend(orders)
                    print(f"  {period}: 添加了 {len(orders)} 个订单")
                
                if 'order_chains' in data:
                    chains = data['order_chains']
                    daily_chains.extend(chains)
                    print(f"  {period}: 添加了 {len(chains)} 个订单链")
                
                if 'car_count' in data:
                    car_count = data['car_count']
                    daily_car_counts.append(car_count)
                    period_car_counts[period] = car_count
                    print(f"  {period}: 车辆数 {car_count}")
                    
            except Exception as e:
                print(f"  加载文件失败: {e}")
        else:
            print(f"未找到文件: {pattern}")
    
    max_fleet_size = max(daily_car_counts) if daily_car_counts else 0
    avg_car_count = sum(daily_car_counts) / len(daily_car_counts) if daily_car_counts else 0
    
    for period in time_periods:
        if period not in period_car_counts:
            period_car_counts[period] = max_fleet_size
        else:
            period_car_counts[period] = max_fleet_size
    
    print(f"{date_str} 统一最大车队规模: {max_fleet_size}, 平均车队规模: {avg_car_count}")
    
    return daily_orders, daily_chains, max_fleet_size, avg_car_count, period_car_counts

def process_daily_vehicle_states(orders, order_chains, date_str, car_count=None, period_car_counts=None):
    """处理单天的车辆状态数据"""
    if not orders or not order_chains:
        return None, None, None, None, None
    
    vehicle_orders = defaultdict(list)
    
    for chain_idx, chain in enumerate(order_chains):
        vehicle_id = f"vehicle_{chain_idx}"
        
        if isinstance(chain, dict) and 'orders' in chain:
            order_ids = chain['orders']
        elif isinstance(chain, list):
            order_ids = chain
        else:
            continue
        
        for order_id in order_ids:
            for order in orders:
                if order.get('order_id') == order_id:
                    vehicle_orders[vehicle_id].append(order)
                    break
    
    print(f"{date_str}: 找到 {len(vehicle_orders)} 辆车的订单数据")
    
    all_times = []
    for order in orders:
        for time_key in ['call_time', 'accept_time', 'end_time']:
            if time_key in order and order[time_key]:
                all_times.append(order[time_key])
    
    if not all_times:
        print(f"{date_str}: 未找到时间数据")
        return None, None, None, None, None
    
    start_time = min(all_times)
    end_time = max(all_times)
    print(f"{date_str}: 时间范围 {start_time} 到 {end_time}")
    
    time_range = pd.date_range(start=start_time, end=end_time, freq='1min')
    
    carrying_passengers = np.zeros(len(time_range))
    picking_up = np.zeros(len(time_range))
    waiting = np.zeros(len(time_range))
    
    for vehicle_id, vehicle_order_list in vehicle_orders.items():
        vehicle_order_list.sort(key=lambda x: x.get('call_time', datetime.min))
        
        for i, order in enumerate(vehicle_order_list):
            call_time = order.get('call_time')
            accept_time = order.get('accept_time')
            end_time = order.get('end_time')
            
            if not all([call_time, accept_time, end_time]):
                continue
            
            call_idx = get_time_index(call_time, time_range)
            accept_idx = get_time_index(accept_time, time_range)
            end_idx = get_time_index(end_time, time_range)
            
            if call_idx is None or accept_idx is None or end_idx is None:
                continue
            
            if accept_idx < call_idx:
                picking_up[accept_idx:call_idx] += 1
            
            if call_idx < end_idx:
                carrying_passengers[call_idx:end_idx] += 1
            
            if i < len(vehicle_order_list) - 1:
                next_order = vehicle_order_list[i + 1]
                next_accept_time = next_order.get('accept_time')
                if next_accept_time:
                    next_accept_idx = get_time_index(next_accept_time, time_range)
                    if next_accept_idx is not None and end_idx < next_accept_idx:
                        waiting[end_idx:next_accept_idx] += 1
    
    total_vehicles = np.zeros(len(time_range))
    
    for vehicle_id, vehicle_order_list in vehicle_orders.items():
        vehicle_order_list.sort(key=lambda x: x.get('call_time', datetime.min))
        
        if vehicle_order_list:
            first_accept = min(order.get('accept_time') for order in vehicle_order_list if order.get('accept_time'))
            last_end = max(order.get('end_time') for order in vehicle_order_list if order.get('end_time'))
            
            start_idx = get_time_index(first_accept, time_range)
            end_idx = get_time_index(last_end, time_range)
            
            if start_idx is not None and end_idx is not None:
                total_vehicles[start_idx:end_idx+1] += 1
    
    fixed_total_vehicles = carrying_passengers + picking_up + waiting
    
    return time_range, carrying_passengers, picking_up, waiting, total_vehicles, fixed_total_vehicles

def get_time_index(dt, time_range):
    """获取时间在时间序列中的索引"""
    try:
        time_diff = np.abs((time_range - dt).total_seconds())
        min_idx = np.argmin(time_diff)
        if time_diff[min_idx] <= 60:
            return min_idx
        return None
    except:
        return None

def load_car_counts_from_csv(csv_file='car_counts_summary.csv'):
    """从CSV文件加载car_count数据"""
    try:
        df = pd.read_csv(csv_file)
        car_counts_dict = {}
        
        for _, row in df.iterrows():
            date = row['date']
            period = row['period']
            car_count = row['car_count']
            
            if date not in car_counts_dict:
                car_counts_dict[date] = {}
            car_counts_dict[date][period] = car_count
        
        print(f"成功加载CSV数据，包含 {len(car_counts_dict)} 天的数据")
        return car_counts_dict
    except Exception as e:
        print(f"加载CSV文件失败: {e}")
        return {}

def smooth_data(data, time_range, smoothing_factor=0.1, is_red_line=False):
    """对数据进行平滑处理，使用移动平均和高斯滤波"""
    if len(data) < 3:
        return data
    
    if is_red_line:
        window_size = 15
    else:
        window_size = 8
    
    if len(data) >= window_size:
        data_series = pd.Series(data)
        moving_avg = data_series.rolling(window=window_size, center=True, min_periods=1).mean()
        data = moving_avg.values
    
    time_numeric = np.array([t.timestamp() for t in time_range])
    
    try:
        f = interp1d(time_numeric, data, kind='cubic', bounds_error=False, fill_value='extrapolate')
        
        time_dense = np.linspace(time_numeric.min(), time_numeric.max(), len(time_numeric) * 5)
        
        smoothed_data = f(time_dense)
        
        from scipy.ndimage import gaussian_filter1d
        if is_red_line:
            smoothed_data = gaussian_filter1d(smoothed_data, sigma=smoothing_factor * 2)
        else:
            smoothed_data = gaussian_filter1d(smoothed_data, sigma=smoothing_factor)
        
        f_smooth = interp1d(time_dense, smoothed_data, kind='linear', bounds_error=False, fill_value='extrapolate')
        final_data = f_smooth(time_numeric)
        
        return final_data
    except:
        return data

def create_weekly_fleet_dynamics_plot(daily_data, output_dir='fleet_dynamics_plots'):
    """创建一周的车队动态图"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    plt.style.use('default')
    plt.rcParams.update({
        'font.family': 'Arial',
        'font.size': 18,
        'axes.linewidth': 1.2,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.grid': True,
        'grid.alpha': 0.3,
        'grid.linewidth': 0.5,
        'figure.facecolor': 'white',
        'axes.facecolor': 'white'
    })
    
    fig, ax = plt.subplots(figsize=(24, 6))
    
    colors = {
        'carrying': '#FF6B35',
        'picking': '#4682B4',
        'waiting': '#43A047',
        'total': '#D32F2F',
        'robotaxi_total': '#000000'
    }
    
    all_carrying = []
    all_picking = []
    all_waiting = []
    all_total = []
    daily_max_fleet_sizes = []
    
    dates = ['2024-11-18', '2024-11-19', '2024-11-20', '2024-11-21', '2024-11-22', '2024-11-23', '2024-11-24']
    first_points = {}
    last_points = {}
    for i, date in enumerate(dates):
        if date in daily_data and daily_data[date]['time_range'] is not None:
            time_range = daily_data[date]['time_range']
            carrying = daily_data[date]['carrying_passengers']
            picking = daily_data[date]['picking_up']
            waiting = daily_data[date]['waiting']
            total = daily_data[date]['total_vehicles']
            fixed_total = daily_data[date]['fixed_total_vehicles']
            max_fleet = daily_data[date]['max_fleet_size']
            
            carrying_smooth = smooth_data(carrying, time_range, smoothing_factor=0.5)
            picking_smooth = smooth_data(picking, time_range, smoothing_factor=0.5)
            waiting_smooth = smooth_data(waiting, time_range, smoothing_factor=0.5)
            total_smooth = smooth_data(total, time_range, smoothing_factor=0.5)
            fixed_total_smooth = smooth_data(fixed_total, time_range, smoothing_factor=0.8, is_red_line=True)
            
            robotaxi_dispatch_data = {
                '2024-11-18': 396,
                '2024-11-19': 400,
                '2024-11-20': 397,
                '2024-11-21': 400,
                '2024-11-22': 399,
                '2024-11-23': 450,
                '2024-11-24': 476
            }

            ratios = np.array([
                1, 1, 1, 1, 0.999404762, 0.998214286, 0.996428571, 0.978869048,
                0.941964286, 0.933035714, 0.941964286, 0.9375, 0.941964286, 0.935416667,
                0.920535714, 0.92172619, 0.937797619, 0.961904762, 0.973214286, 0.976488095,
                0.952083333, 0.952380952, 0.948214286, 0.961309524
            ], dtype=float)

            base = float(robotaxi_dispatch_data.get(date, 0))
            N, R = len(time_range), len(ratios)

            if N == 0:
                robotaxi_total_data = np.array([], dtype=float)
            elif N == R:
                robotaxi_total_data = base * ratios
            else:
                bin_idx = np.floor(np.arange(N) * R / N).astype(int)
                bin_idx = np.clip(bin_idx, 0, R - 1)
                robotaxi_total_data = base * ratios[bin_idx]

            robotaxi_total_data = np.rint(robotaxi_total_data).astype(int)
            print(robotaxi_total_data)
            
            day_start = pd.Timestamp(date)
            day_end = day_start + pd.Timedelta(days=1)


            vals = np.asarray(robotaxi_total_data, dtype=float)
            N = len(vals)
            if N > 0:
                try:
                    x_core = pd.to_datetime(time_range)
                    assert len(x_core) == N
                except Exception:
                    offsets_h = np.linspace(0, 24, N, endpoint=False)
                    x_core = day_start + pd.to_timedelta(offsets_h, unit='h')

                s = pd.Series(vals, index=x_core).sort_index()

                hourly_index = pd.date_range(day_start, day_end, freq='H')

                s_hourly = s.groupby(s.index.floor('H')).first().reindex(hourly_index).ffill()

                ax.plot(
                    hourly_index[:-1], s_hourly.values[:-1],
                    color=colors['robotaxi_total'], linewidth=1.5, alpha=1.0,
                    label='Robotaxi volume' if i == 0 else "", zorder=10
                )
                first_points[date] = (hourly_index[0], float(s_hourly.iloc[0]))
                last_points[date] = (hourly_index[-2], float(s_hourly.iloc[-2]))

            if 'daily_transitions' not in locals():
                daily_transitions = []
            daily_transitions.append({
                'date': date,
                'day_start': day_start,
                'day_end': day_end,
                'value': robotaxi_dispatch_data.get(date, 0)
            })
            
            ax.plot(time_range, carrying_smooth, color=colors['carrying'], linewidth=1.5, alpha=0.7, 
                   label='With passenger' if i == 0 else "")
            ax.plot(time_range, picking_smooth, color=colors['picking'], linewidth=1.5, alpha=0.7,
                   label='Driving to pick up' if i == 0 else "")
            ax.plot(time_range, waiting_smooth, color=colors['waiting'], linewidth=1.5, alpha=0.7,
                   label='Waiting to pick up' if i == 0 else "")
            ax.plot(time_range, fixed_total_smooth, color=colors['total'], linewidth=2, alpha=0.8,
                   label='Minimum fleet volume' if i == 0 else "")
            
            all_carrying.extend(carrying)
            all_picking.extend(picking)
            all_waiting.extend(waiting)
            all_total.extend(total)
            daily_max_fleet_sizes.append(max_fleet)
    print(first_points)
    if 'daily_transitions' in locals() and len(daily_transitions) > 1:
        for d_cur, d_nxt in zip(dates[:-1], dates[1:]):
            if d_cur in last_points and d_nxt in first_points:
                (t23, v23) = last_points[d_cur]
                (t00, v00) = first_points[d_nxt]
                ax.plot([t23, t00], [v23, v00],
                        color=colors['robotaxi_total'], linewidth=1.5, alpha=1.0, zorder=10)

    if all_total:
        avg_total = np.mean(all_total)
        ax.axhline(y=avg_total, color='red', linestyle='--', linewidth=2, alpha=0.8,
                  label='Average minimum fleet')
    
    ax.set_ylabel('Number of vehicles', fontsize=22, fontweight='bold')
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 8, 16, 24], interval=1))
    ax.xaxis.set_minor_locator(plt.NullLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=18)
    
    if daily_data:
        all_times = []
        for date_data in daily_data.values():
            if date_data['time_range'] is not None:
                all_times.extend(date_data['time_range'])
        if all_times:
            min_time = min(all_times)
            max_time = max(all_times)
            
            dates = ['2024-11-18', '2024-11-19', '2024-11-20', '2024-11-21', '2024-11-22', '2024-11-23', '2024-11-24']
            weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            for i, date in enumerate(dates):
                day_start = pd.Timestamp(date)
                day_center = day_start + pd.Timedelta(hours=12)
                
                y_pos = ax.get_ylim()[0] - (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.12
                ax.text(day_center, y_pos, weekdays[i], ha='center', va='top', 
                       fontsize=24, fontweight='bold', fontfamily='Arial', 
                       color='#000000')
    
    if daily_data:
        all_times = []
        for date_data in daily_data.values():
            if date_data['time_range'] is not None:
                all_times.extend(date_data['time_range'])
        if all_times:
            ax.set_xlim(min(all_times), max(all_times))
    
    if all_total:
        max_robotaxi = max([396, 400, 397, 400, 399, 450, 476])
        max_data = max(max(all_total), max_robotaxi)
        ax.set_ylim(0, max_data * 1.1)
    
    ax.yaxis.set_major_locator(plt.MaxNLocator(nbins=8, integer=True))
    plt.setp(ax.yaxis.get_majorticklabels(), fontsize=18, fontweight='normal')
    ax.tick_params(axis='y', which='major', labelsize=18, width=1.5, length=6)
    
    robotaxi_values = []
    for date_data in daily_data.values():
        if 'robotaxi_total' in date_data:
            robotaxi_values.extend(date_data['robotaxi_total'])
    
    if robotaxi_values:
        avg_robotaxi = np.mean(robotaxi_values)
        ax.legend(loc='upper center', frameon=True, fancybox=True, shadow=True, fontsize=20.5,
                  bbox_to_anchor=(0.5, 1.08), ncol=6, columnspacing=1.0)
    else:
        ax.legend(loc='upper center', frameon=True, fancybox=True, shadow=True, fontsize=20.5,
                  bbox_to_anchor=(0.5, 1.08), ncol=6, columnspacing=1.0)
    
    plt.tight_layout()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plt.savefig(f'{output_dir}/weekly_fleet_dynamics_{timestamp}.svg', dpi=2000, bbox_inches='tight', facecolor='white')
    plt.savefig(f'{output_dir}/weekly_fleet_dynamics_{timestamp}.pdf', dpi=2000, bbox_inches='tight', facecolor='white')
    
    plt.show()
    
    print(f"\n=== 一周车队动态统计 ===")
    print(f"每日最大车队规模: {daily_max_fleet_sizes}")
    if all_total:
        print(f"平均载客中车辆数: {np.mean(all_carrying):.2f}")
        print(f"平均接客途中车辆数: {np.mean(all_picking):.2f}")
        print(f"平均等待接客车辆数: {np.mean(all_waiting):.2f}")
        print(f"平均总车辆数: {np.mean(all_total):.2f}")
        print(f"最大总车辆数: {np.max(all_total):.2f}")

def main():
    """主函数"""
    data_dir = "improved_integrated_results"
    print(f"使用数据目录: {data_dir}")
    
    dates = ['2024-11-18', '2024-11-19', '2024-11-20', '2024-11-21', '2024-11-22', '2024-11-23', '2024-11-24']
    
    daily_data = {}
    
    print("正在加载一周的数据...")
    for date in dates:
        print(f"\n=== 处理 {date} ===")
        orders, chains, max_fleet_size, avg_car_count, period_car_counts = load_daily_data(data_dir, date)
        
        if orders:
            result = process_daily_vehicle_states(orders, chains, date, avg_car_count, period_car_counts)
            if result[0] is not None:
                time_range, carrying, picking, waiting, total, fixed_total = result
                daily_data[date] = {
                    'time_range': time_range,
                    'carrying_passengers': carrying,
                    'picking_up': picking,
                    'waiting': waiting,
                    'total_vehicles': total,
                    'fixed_total_vehicles': fixed_total,
                    'max_fleet_size': max_fleet_size
                }
            else:
                print(f"{date}: 无法处理车辆状态数据")
        else:
            print(f"{date}: 无法加载订单数据")
    
    print(f"\n成功处理 {len(daily_data)} 天的数据")
    
    if daily_data:
        print("\n正在创建一周车队动态图...")
        create_weekly_fleet_dynamics_plot(daily_data)
    else:
        print("没有可用的数据来创建图表")

if __name__ == "__main__":
    main()
