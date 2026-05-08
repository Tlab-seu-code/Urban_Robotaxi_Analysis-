# -*- coding: utf-8 -*-
"""
Created on Sun Feb  9 15:43:37 2025

@author: WuxiTlab
"""

# import os
# import pandas as pd
# from glob import glob

# # 文件夹路径
# input_folder = "input"
# output_folder = "speed_output"
# chunk_size = 10**6  # 每次读取100万行

# # 确保输出文件夹存在
# os.makedirs(output_folder, exist_ok=True)

# # 获取所有 CSV 文件
# csv_files = glob(os.path.join(input_folder, "*.csv"))

# # 处理每个 CSV 文件
# for input_file in csv_files:
#     output_file = os.path.join(output_folder, os.path.basename(input_file))  # 生成输出文件路径
#     filtered_data = []  # 存储过滤后的数据
#     processed_lines = 0  # 已处理的行数

#     # 逐块读取和处理数据
#     for chunk in pd.read_csv(input_file, chunksize=chunk_size, encoding='utf-8'):
#         filtered_chunk = chunk[chunk['state'] == 1]
#         filtered_data.append(filtered_chunk)

#         # 更新处理的行数并输出进度
#         processed_lines += len(chunk)
#         print(f"处理文件 {input_file} 进度：{processed_lines} 行")

#     # 保存筛选后的数据
#     if filtered_data:
#         result = pd.concat(filtered_data)
#         result.to_csv(output_file, index=False)
#         print(f"筛选后的数据已保存到 {output_file}")
#     else:
#         print(f"文件 {input_file} 中没有满足条件的数据。")
# import os
# import pandas as pd
# import matplotlib.pyplot as plt

# # 设置中文字体为黑体
# plt.rcParams['font.sans-serif'] = ['SimHei']
# plt.rcParams['axes.unicode_minus'] = False

# # 设置文件夹路径
# folder = 'length_output'

# # 所有文件中存放速度的列表
# all_speeds = []

# # 遍历所有文件
# for filename in os.listdir(folder):
#     if filename.endswith('orders_with_length.csv'):
#         filepath = os.path.join(folder, filename)
#         df = pd.read_csv(filepath)

#         # 去除 duration 或 travel_length 无效值
#         df = df[df['duration'] > 0]
#         df = df[df['travel_length'] > 0]

#         # duration 是秒，转换为小时再计算速度 km/h
#         df['recomputed_speed'] = df['travel_length'] / 1000 / (df['duration'] / 3600)

#         # 过滤掉异常值，比如超过 120km/h 的
#         df = df[(df['recomputed_speed'] > 0) & (df['recomputed_speed'] < 120)]

#         all_speeds.extend(df['recomputed_speed'].tolist())

# # 绘图
# plt.figure(figsize=(10, 6))
# plt.hist(all_speeds, bins=60, color='lightgreen', edgecolor='black')
# plt.xlabel('重新计算的平均速度 (km/h)')
# plt.ylabel('订单数量')
# plt.title('订单平均速度分布图（基于 travel_length 和 duration）')
# plt.grid(True, linestyle='--', alpha=0.6)
# plt.tight_layout()
# plt.show()
# import os
# import pandas as pd
# import matplotlib.pyplot as plt
# import matplotlib.ticker as ticker

# # 设置中文字体
# plt.rcParams['font.sans-serif'] = ['SimHei']
# plt.rcParams['axes.unicode_minus'] = False

# def classify_time_period(hour):
#     """根据小时分类时间段"""
#     if 7 <= hour < 9:
#         return '早 (7-9)'
#     elif 11 <= hour < 13:
#         return '中 (11-13)'
#     elif 17 <= hour < 19:
#         return '晚 (17-19)'
#     elif hour >= 23 or hour < 6:
#         return '夜 (23-6)'
#     else:
#         return '其他'

# # 初始化存储容器
# speed_data = {
#     '早 (7-9)': [],
#     '中 (11-13)': [],
#     '晚 (17-19)': [],
#     '夜 (23-6)': []
# }

# # 遍历文件
# folder = 'length_output'
# for filename in os.listdir(folder):
#     if filename.endswith('orders_with_length.csv'):
#         filepath = os.path.join(folder, filename)
#         df = pd.read_csv(filepath)
        
#         # 数据清洗
#         df = df[(df['duration'] > 0) & (df['travel_length'] > 0)]
#         df['start_time'] = pd.to_datetime(df['start_time'])
        
#         # 计算速度
#         df['recomputed_speed'] = df['travel_length'] / 1000 / (df['duration'] / 3600)
#         df = df[(df['recomputed_speed'] > 0) & (df['recomputed_speed'] < 120)]
        
#         # 分类时间段
#         df['period'] = df['start_time'].dt.hour.apply(classify_time_period)
        
#         # 收集数据
#         for period in speed_data:
#             period_speeds = df[df['period'] == period]['recomputed_speed'].tolist()
#             speed_data[period].extend(period_speeds)

# # 创建2x2子图
# fig, axes = plt.subplots(2, 2, figsize=(16, 12))
# colors = ['#4C72B0', '#DD8452', '#55A868', '#C44E52']
# titles = list(speed_data.keys())

# # 绘制各时段分布
# for idx, (ax, title) in enumerate(zip(axes.flat, titles)):
#     data = speed_data[title]
#     ax.hist(data, bins=60, color=colors[idx], edgecolor='black', alpha=0.8)
    
#     ax.set_title(f'{title}时段速度分布', fontsize=14)
#     ax.set_xlabel('平均速度 (km/h)', fontsize=12)
#     ax.set_ylabel('订单数量', fontsize=12)
#     ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
#     ax.yaxis.set_major_locator(ticker.MaxNLocator(6))
#     ax.grid(True, linestyle='--', alpha=0.6)
#     ax.set_xlim(0, 120)
#     ax.set_axisbelow(True)

# plt.tight_layout()
# plt.show()

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from matplotlib.gridspec import GridSpec

# 中文字体配置
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def classify_time_period(hour):
    """动态时段分类器"""
    period_rules = [
        (7, 9, '早高峰 (7-9)'),
        (11, 13, '午间 (11-13)'),
        (17, 19, '晚高峰 (17-19)'),
        (23, 6, '夜间 (23-6)')
    ]
    for start, end, label in period_rules:
        if start > end:  # 处理跨天时段
            if hour >= start or hour < end:
                return label
        elif start <= hour < end:
            return label
    return '其他时段'

# 自定义分箱配置
distance_bins = list(range(0, 101, 2))  # 0-20每2km，25+每5km
speed_bins = list(range(0, 121, 5))  # 速度分箱规则

def load_and_process_data(folder_path):
    """数据加载与处理管道"""
    analysis_data = {
        'distance': {'早高峰 (7-9)': [], '午间 (11-13)': [], 
                    '晚高峰 (17-19)': [], '夜间 (23-6)': []},
        'speed': {'早高峰 (7-9)': [], '午间 (11-13)': [], 
                 '晚高峰 (17-19)': [], '夜间 (23-6)': []}
    }
    all_distances = []
    
    for file in os.listdir(folder_path):
        if file.endswith('orders_with_length.csv'):
            df = pd.read_csv(os.path.join(folder_path, file))
            
            # 数据质量过滤
            df['recomputed_speed'] = (df['travel_length'] / 1000) / (df['duration'] / 3600)
            df = df[(df['duration'] > 60) & (df['travel_length'] > 500)]  # 过滤超短行程
            df = df[df['recomputed_speed'].between(5, 100)]  # 合理速度范围
            
            # 特征工程
            df['start_hour'] = pd.to_datetime(df['start_time']).dt.hour
            df['travel_km'] = df['travel_length'] / 1000
            df['period'] = df['start_hour'].apply(classify_time_period)
            
            # 数据存储
            for period in analysis_data['distance']:
                period_mask = df['period'] == period
                period_data = df[period_mask]
                
                analysis_data['distance'][period].extend(period_data['travel_km'].tolist())
                analysis_data['speed'][period].extend(period_data['recomputed_speed'].tolist())
            
            all_distances.extend(df['travel_km'].tolist())
    
    return analysis_data, all_distances

def plot_combined_distribution(data, bins, title, xlabel, highlight=100):
    """组合式分布可视化"""
    plt.figure(figsize=(14, 7))
    
    # 主直方图
    n, bins, patches = plt.hist(data, bins=bins, 
                               color='#1f77b4', edgecolor='white',
                               linewidth=0.8, alpha=0.9, zorder=2)
    
    # 分界标识线
    if highlight:
        plt.axvline(highlight, color='#d62728', linestyle='--', 
                   linewidth=1.2, alpha=0.8, zorder=3)
        plt.text(highlight+0.5, max(n)*0.95, '精细化分界点', rotation=90,
                va='top', ha='left', color='#d62728', fontsize=10)
    
    # 分布曲线
    centers = (bins[:-1] + bins[1:]) / 2
    plt.plot(centers, n, color='#2ca02c', linewidth=2, 
            alpha=0.8, linestyle='--', zorder=4)
    
    # 可视化优化
    plt.gca().xaxis.set_major_locator(ticker.MultipleLocator(10))
    plt.gca().xaxis.set_minor_locator(ticker.AutoMinorLocator(5))
    plt.grid(which='major', linestyle='--', alpha=0.7, zorder=1)
    plt.grid(which='minor', linestyle=':', alpha=0.3, zorder=1)
    
    plt.title(title, fontsize=14, pad=20)
    plt.xlabel(xlabel, fontsize=12, labelpad=10)
    plt.ylabel('订单频次', fontsize=12, labelpad=10)
    plt.xticks(rotation=45)
    plt.xlim(left=0)
    plt.tight_layout()
    plt.show()

def plot_period_comparison(analysis_data, metric='distance'):
    """分时段对比可视化"""
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(2, 2, figure=fig, hspace=0.25, wspace=0.2)
    colors = ['#4C72B0', '#DD8452', '#55A868', '#C44E52']
    titles = ['早高峰 (7-9)', '午间 (11-13)', '晚高峰 (17-19)', '夜间 (23-6)']
    
    bins = distance_bins if metric == 'distance' else speed_bins
    xlabel = '行程距离 (公里)' if metric == 'distance' else '平均速度 (km/h)'
    
    for idx, period in enumerate(titles):
        ax = fig.add_subplot(gs[idx//2, idx%2])
        data = analysis_data[metric][period]
        
        # 直方图
        n, bins, _ = ax.hist(data, bins=bins, density=False,
                            color=colors[idx], alpha=0.8,
                            edgecolor='white', linewidth=0.6)
        
        # 核密度估计
        if metric == 'distance':
            from scipy.stats import gaussian_kde
            density = gaussian_kde(data)
            xs = np.linspace(min(data), max(data), 200)
            ax2 = ax.twinx()
            ax2.plot(xs, density(xs), color='black', 
                    linewidth=1.5, alpha=0.6, linestyle='--')
            ax2.set_ylabel('密度分布', fontsize=9, color='#555555')
            ax2.tick_params(axis='y', colors='#555555', labelsize=8)
        
        # 可视化优化
        ax.set_title(f'{period} {xlabel.split(" ")[0]}分布', fontsize=12)
        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_ylabel('订单数量', fontsize=10)
        ax.xaxis.set_major_locator(ticker.MultipleLocator(10 if metric=='distance' else 20))
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.set_xlim(0, 100 if metric=='distance' else 120)
        
    plt.suptitle(f'分时段{xlabel}分布对比', y=0.98, fontsize=14)
    plt.tight_layout()
    plt.show()

# 主程序
if __name__ == "__main__":
    # 数据加载
    analysis_data, all_distances = load_and_process_data('length_output')
    
    # 整体分布可视化
    plot_combined_distribution(
        all_distances, 
        bins=distance_bins,
        title='行程距离分布（0-20km精细分箱）\n垂直红线标识分箱策略变化点',
        xlabel='行程距离 (公里)',
        highlight=100
    )
    
    # 分时段对比分析
    plot_period_comparison(analysis_data, metric='distance')
    plot_period_comparison(analysis_data, metric='speed')