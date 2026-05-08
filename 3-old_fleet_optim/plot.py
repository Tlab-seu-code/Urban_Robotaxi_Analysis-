import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 配置中文字体为黑体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 或者 'SimHei' 根据安装的字体来选择
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

def visualize_taxi_data(file_path):
    # 读取已处理的数据
    df = pd.read_csv(file_path)

    # 统计各类订单的数量
    # 1. 调度虚拟单 (index > 0)
    dispatch_virtual_count = df[df['订单来源'] == '调度单'].shape[0]
    
    # 2. 普通完成单 (订单类型为 完成 且 index = 0)
    completed_normal_count = df[(df['用户id'] != 'virtual-schedule') 
                                & (df['订单状态'] == '完成')
                                & (df['订单来源'] != '调度单')
                                & (df['订单来源'] != '充电单')            
                                ].shape[0]
    
    # 3. 取消单 (订单类型为 取消)
    cancel_count = df[df['订单状态'].str.contains('取消')].shape[0]
    
    # 4. 充电调度单 (订单类型既不是 完成 也不是 取消)
    charging_dispatch_count = df[df['订单来源'].str.contains('充电单')].shape[0]

    # 绘制柱状图
    categories = ['调度完成单', '乘客完成单', '取消单', '充电完成单']
    counts = [dispatch_virtual_count, completed_normal_count, cancel_count, charging_dispatch_count]

    fig, ax = plt.subplots(figsize=(4, 6))
    sns.barplot(x=categories, y=counts, palette="Set2", ax=ax)

    # 在每个柱子上添加数字
    for p in ax.patches:
        ax.annotate(f'{int(p.get_height())}',
                    (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='center', fontsize=12,
                    xytext=(0, 5), textcoords='offset points')

    # 设置标题和标签
    ax.set_title('各类订单数量分布')
    ax.set_xlabel('订单类型')
    ax.set_ylabel('数量')

    # 展示图表
    plt.tight_layout()
    plt.show()
    

def analyze_cancel_orders_with_duration(file_path):
    """
    分析取消订单数据并绘制数量分布图及接驾时长、行程时长分布。

    参数:
    - file_path: str，CSV文件的路径

    返回:
    - None，直接显示图表
    """
    # 读取数据
    data = pd.read_csv(file_path)

    # 筛选订单类型为“乘客单-取消”的订单
    data = data[data['订单类型'] == '乘客单-取消']

    # 定义四类取消订单的条件
    cancel_I = data[
        (data['车辆接单时间'].isna()) & 
        (data['车辆出发时间'].isna()) & 
        (data['到达起点时间'].isna())
    ]
    cancel_II = data[
        (~data['车辆接单时间'].isna()) & 
        (data['车辆出发时间'].isna()) & 
        (data['到达起点时间'].isna())
    ]
    cancel_III = data[
        (~data['车辆接单时间'].isna()) & 
        (~data['车辆出发时间'].isna()) & 
        (data['到达起点时间'].isna())
    ]
    cancel_IV = data[
        (~data['车辆接单时间'].isna()) & 
        (~data['车辆出发时间'].isna()) & 
        (~data['到达起点时间'].isna()) & 
        (data['行程开始时间'].isna())
    ]

    # 创建字典以便处理
    cancel_types = {
        "I类取消单": cancel_I,
        "II类取消单": cancel_II,
        "III类取消单": cancel_III,
        "IV类取消单": cancel_IV
    }

    # 统计各类取消订单的数量
    cancel_counts = {key: len(df) for key, df in cancel_types.items()}

    # 绘制数量分布柱状图
    plt.figure(figsize=(10, 6))
    bars = plt.bar(cancel_counts.keys(), cancel_counts.values(), color=['blue', 'orange', 'green', 'red'])
    plt.title("各类取消订单数量分布", fontsize=16)
    plt.xlabel("取消订单类型", fontsize=14)
    plt.ylabel("数量", fontsize=14)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # 在柱子顶部添加数量标注
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, height, str(height), ha='center', va='bottom', fontsize=12)

    plt.show()

    # 绘制接驾时长和行程时长的分布
    for cancel_type, df in cancel_types.items():
        # 接驾时长(s)分布
        plt.figure(figsize=(10, 6))
        df['接驾时长(s)'] = pd.to_numeric(df['接驾时长(s)'], errors='coerce')  # 转换为数值型，处理缺失值
        values = df['接驾时长(s)'].dropna()
        n, bins, patches = plt.hist(values, bins=30, color='blue', alpha=0.7, rwidth=0.8)
        plt.title(f"{cancel_type} - 接驾时长(s)分布", fontsize=16)
        plt.xlabel("接驾时长(s)", fontsize=14)
        plt.ylabel("频数", fontsize=14)
        plt.grid(axis='y', linestyle='--', alpha=0.7)

        # 添加数量标注
        for i in range(len(patches)):
            plt.text(bins[i] + (bins[i + 1] - bins[i]) / 2, n[i], str(int(n[i])), ha='center', va='bottom', fontsize=10)

        plt.show()

        # 行程时长(s)分布
        plt.figure(figsize=(10, 6))
        df['行程时长(s)'] = pd.to_numeric(df['行程时长(s)'], errors='coerce')  # 转换为数值型，处理缺失值
        values = df['行程时长(s)'].dropna()
        n, bins, patches = plt.hist(values, bins=30, color='orange', alpha=0.7, rwidth=0.8)
        plt.title(f"{cancel_type} - 行程时长(s)分布", fontsize=16)
        plt.xlabel("行程时长(s)", fontsize=14)
        plt.ylabel("频数", fontsize=14)
        plt.grid(axis='y', linestyle='--', alpha=0.7)

        # 添加数量标注
        for i in range(len(patches)):
            plt.text(bins[i] + (bins[i + 1] - bins[i]) / 2, n[i], str(int(n[i])), ha='center', va='bottom', fontsize=10)

        plt.show()

import matplotlib.pyplot as plt
import numpy as np


def load_grid_map(grid_file='grid_map.csv'):
    """
    加载网格信息，并将其转换为一个字典，方便根据经纬度查找网格编号。
    :param grid_file: 网格信息的CSV文件路径，默认为 'grid_map.csv'
    :return: 返回一个字典，包含经纬度范围和网格编号
    """
    grid_df = pd.read_csv(grid_file)
    grid_map = {}
    
    for _, row in grid_df.iterrows():
        lon_start, lat_start = row['起始经度'], row['起始纬度']
        lon_end, lat_end = row['终止经度'], row['终止纬度']
        grid_map[(lon_start, lat_start, lon_end, lat_end)] = int(row['网格编号'])  # 转换网格编号为整数
    
    return grid_map

def find_grid(lon, lat, grid_map):
    """
    根据经纬度查找所属网格编号。
    
    :param lon: 经度
    :param lat: 纬度
    :param grid_map: 网格编号字典
    :return: 所属网格编号
    """
    for (lon_start, lat_start, lon_end, lat_end), grid_id in grid_map.items():
        if lon_start <= lon < lon_end and lat_start <= lat < lat_end:
            return grid_id
    return None  # 如果没有找到对应的网格，返回 None

def plot_grid_heatmap(input_file='v11-grid.csv'):
    """
    读取订单数据，统计起点和终点网格编号的频次，并绘制热力图。
    
    :param input_file: 输入包含网格编号的CSV文件路径，默认为 'v11-grid.csv'
    """
    # 加载网格信息
    grid_map = load_grid_map('grid_map.csv')
    
    # 读取包含网格编号的CSV文件
    data = pd.read_csv(input_file)
    
    # 统计每个起点网格编号的频次
    start_grid_counts = data['起点网格编号'].value_counts().sort_index()
    # 统计每个终点网格编号的频次
    end_grid_counts = data['终点网格编号'].value_counts().sort_index()

    # 获取网格编号的最大编号
    max_grid_id = max(start_grid_counts.index.max(), end_grid_counts.index.max())

    # 创建空的频次矩阵（行：经度，列：纬度）
    grid_lon_vals = []
    grid_lat_vals = []
    start_grid_matrix = []
    end_grid_matrix = []
    
    # 根据网格编号构建对应的经纬度范围
    for (lon_start, lat_start, lon_end, lat_end), grid_id in grid_map.items():
        grid_lon_vals.append((lon_start + lon_end) / 2)  # 取经度的中间值
        grid_lat_vals.append((lat_start + lat_end) / 2)  # 取纬度的中间值
        start_grid_matrix.append((lon_start, lat_start, lon_end, lat_end, grid_id))
        end_grid_matrix.append((lon_start, lat_start, lon_end, lat_end, grid_id))

    # 设置画布
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    # 绘制起点网格热力图
    start_matrix = np.zeros((len(grid_lon_vals), len(grid_lat_vals)))
    for i, grid_data in enumerate(start_grid_matrix):
        lon_start, lat_start, lon_end, lat_end, grid_id = grid_data
        start_matrix[i] = int(start_grid_counts.get(grid_id, 0))  # 获取频次值
        
    sns.heatmap(start_matrix, annot=True, fmt="g", cmap="YlGnBu", xticklabels=grid_lon_vals, yticklabels=grid_lat_vals, ax=axes[0])
    axes[0].set_title('起点网格分布热力图')
    axes[0].set_xlabel('经度')
    axes[0].set_ylabel('纬度')

    # 绘制终点网格热力图
    end_matrix = np.zeros((len(grid_lon_vals), len(grid_lat_vals)))
    for i, grid_data in enumerate(end_grid_matrix):
        lon_start, lat_start, lon_end, lat_end, grid_id = grid_data
        end_matrix[i] = int(end_grid_counts.get(grid_id, 0))  # 获取频次值
        
    sns.heatmap(end_matrix, annot=True, fmt="g", cmap="YlGnBu", xticklabels=grid_lon_vals, yticklabels=grid_lat_vals, ax=axes[1])
    axes[1].set_title('终点网格分布热力图')
    axes[1].set_xlabel('经度')
    axes[1].set_ylabel('纬度')

    # 显示热力图
    plt.tight_layout()
    plt.show()

# 使用示例
# plot_grid_heatmap(input_file='v11-grid.csv')

# 调用示例
# analyze_cancel_orders_with_duration("output_with_nature.csv")



# 调用示例
# analyze_cancel_orders_with_duration("output_with_nature.csv")

# 调用示例
# vanalyze_cancel_orders("output_with_nature.csv")

# 示例调用
visualize_taxi_data('v1-vir.csv')
