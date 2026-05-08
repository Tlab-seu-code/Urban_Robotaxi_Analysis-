# -*- coding: utf-8 -*-
"""
Created on Fri Apr 25 13:20:18 2025

@author: TLab
"""
# import pandas as pd
# import matplotlib.pyplot as plt
# from matplotlib import rcParams, ticker 

# # 设置中文字体为黑体
# plt.rcParams['font.sans-serif'] = ['SimHei']
# plt.rcParams['axes.unicode_minus'] = False

# # 读取CSV
# df = pd.read_csv('v3-districts.csv')

# # 筛选有效数据
# df = df[df['到达起点时间'].notnull() & df['到达目的地时间'].notnull() & (df['行程里程'] > 0)]

# # 时间转换
# df['到达起点时间'] = pd.to_datetime(df['到达起点时间'])
# df['到达目的地时间'] = pd.to_datetime(df['到达目的地时间'])

# # 计算行程时间和平均速度
# df['行程小时'] = (df['到达目的地时间'] - df['到达起点时间']).dt.total_seconds() / 3600
# df['平均速度'] = df['行程里程'] / df['行程小时']
# df = df[df['平均速度'].notnull() & (df['平均速度'] > 0) & (df['平均速度'] < 120)]

# # 定义时间段分割函数
# def get_time_period(hour):
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

# # 提取小时并分类时间段
# df['时段'] = df['到达起点时间'].dt.hour.apply(get_time_period)

# # 筛选需要的时间段
# periods = ['早 (7-9)', '中 (11-13)', '晚 (17-19)', '夜 (23-6)']
# df_periods = df[df['时段'].isin(periods)]

# # 创建2x2子图布局
# fig, axes = plt.subplots(2, 2, figsize=(14, 12))
# plt.subplots_adjust(hspace=0.4, wspace=0.3)  # 调整子图间距

# # 颜色列表和时段顺序
# colors = ['skyblue', 'salmon', 'lightgreen', 'plum']
# time_periods = periods

# # 遍历绘制每个子图
# for i, period in enumerate(time_periods):
#     ax = axes[i//2, i%2]
#     data = df_periods[df_periods['时段'] == period]['平均速度']
    
#     ax.hist(data, bins=50, color=colors[i], edgecolor='black', alpha=0.8)
#     ax.set_xlabel('平均速度 (km/h)', fontsize=12)
#     ax.set_ylabel('订单数量', fontsize=12)
#     ax.set_title(f'{period}时段 平均速度分布', fontsize=14)
#     ax.grid(True, linestyle='--', alpha=0.7)
#     ax.set_xlim(0, 120)
#     ax.set_axisbelow(True)  # 网格线在数据下方
    
#     # 设置统一刻度间隔
#     ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
#     ax.yaxis.set_major_locator(ticker.MaxNLocator(6))

# plt.tight_layout()
# plt.show()

# import pandas as pd
# import matplotlib.pyplot as plt
# from matplotlib import rcParams
# import matplotlib.ticker as ticker

# # 设置中文字体为黑体
# plt.rcParams['font.sans-serif'] = ['SimHei']
# plt.rcParams['axes.unicode_minus'] = False

# # 读取CSV
# df = pd.read_csv('v3-districts.csv')

# # 筛选有效数据：包含到达起点时间、到达目的地时间、行程里程
# df = df[df['到达起点时间'].notnull() & df['到达目的地时间'].notnull() & (df['行程里程'] > 0)]

# # 时间转换
# df['到达起点时间'] = pd.to_datetime(df['到达起点时间'])
# df['到达目的地时间'] = pd.to_datetime(df['到达目的地时间'])

# # 行程时间（小时）
# df['行程小时'] = (df['到达目的地时间'] - df['到达起点时间']).dt.total_seconds() / 3600

# # 计算平均速度 km/h
# df['平均速度'] = df['行程里程'] / df['行程小时']
# df = df[df['平均速度'].notnull() & (df['平均速度'] > 0) & (df['平均速度'] < 120)]  # 过滤异常值

# # 绘图：平均速度分布
# plt.figure(figsize=(10, 6))
# plt.hist(df['平均速度'], bins=50, color='skyblue', edgecolor='black')
# plt.xlabel('平均速度 (km/h)')
# plt.ylabel('订单数量')
# plt.title('订单平均速度分布')
# plt.grid(True, linestyle='--', alpha=0.7)
# plt.tight_layout()
# plt.show()

# import pandas as pd
# import matplotlib.pyplot as plt
# import seaborn as sns
# from matplotlib.colors import Normalize
# import numpy as np

# # 网格参数
# min_lon = 113.942617
# max_lon = 114.629031
# min_lat = 30.255898
# max_lat = 30.742468
# lon_step = 0.0103997242944
# lat_step = 0.0089831117499

# # 计算行列范围
# num_cols = int(round((max_lon - min_lon) / lon_step))
# num_rows = int(round((max_lat - min_lat) / lat_step))

# # 预先生成全量行列索引
# full_rows = pd.Index(range(num_rows), name='row')
# full_cols = pd.Index(range(num_cols), name='col')

# def calculate_grid(lon, lat):
#     """计算经纬度对应的行列"""
#     try:
#         if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
#             return -1, -1
#         col = int((lon - min_lon) // lon_step)
#         row = int((lat - min_lat) // lat_step)
#         return row, col
#     except:
#         return -1, -1
    
# # 读取数据
# df = pd.read_csv('v3-districts.csv', parse_dates=['呼单时间', '开始行程时间'])

# # 数据预处理
# filtered_df = df[
#     (df['订单状态'] != '取消') &
#     (~df['订单来源'].isin(['调度单', '充电单']))
# ].copy()

# # 计算等待时间（确保非负）
# filtered_df['等待时间'] = (
#     (filtered_df['开始行程时间'] - filtered_df['呼单时间']).dt.total_seconds() / 60
# )
# filtered_df = filtered_df[filtered_df['等待时间'] >= 0]

# # 计算网格行列
# grid_data = filtered_df['起点经度'].combine(
#     filtered_df['起点纬度'],
#     lambda lon, lat: calculate_grid(lon, lat)
# )
# filtered_df['row'] = grid_data.apply(lambda x: x[0])
# filtered_df['col'] = grid_data.apply(lambda x: x[1])

# valid_df = filtered_df[
#     (filtered_df['row'] >= 0) & 
#     (filtered_df['col'] >= 0) &
#     (filtered_df['row'] < num_rows) &
#     (filtered_df['col'] < num_cols)
# ].copy()

# # 添加小时列
# valid_df['hour'] = valid_df['呼单时间'].dt.hour


# # 创建全局颜色规范
# all_wait_times = valid_df['等待时间']
# vmin = max(all_wait_times.min(), 0.1)  # 避免0值
# vmax = 20 # all_wait_times.max()

# # 创建颜色映射
# cmap = plt.cm.viridis.copy()
# cmap.set_bad('white')  # 设置缺失值为白色

# # 遍历24小时生成热力图
# for hour in range(24):
#     # 过滤当前小时数据
#     hour_df = valid_df[valid_df['hour'] == hour]
    
#     # 创建数据透视表
#     heatmap_data = hour_df.pivot_table(
#         index='row',
#         columns='col',
#         values='等待时间',
#         aggfunc='mean',
#         dropna=False
#     )
    
#     # 扩展为全量网格
#     heatmap_data = heatmap_data.reindex(
#         index=full_rows,
#         columns=full_cols
#     )
    
#     # 创建画布
#     plt.figure(figsize=(15, 10))
    
#     # 绘制热力图
#     sns.heatmap(
#         heatmap_data,
#         cmap=cmap,
#         norm=Normalize(vmin=vmin, vmax=vmax),
#         mask=heatmap_data.isnull(),
#         cbar_kws={'label': '等待时间（分钟）'}
#     )
    
#     # 设置图表属性
#     plt.title(f'等待时间分布 - {hour:02d}:00')
#     plt.gca().invert_yaxis()
#     plt.xlabel('列编号 (共{}列)'.format(num_cols))
#     plt.ylabel('行编号 (共{}行)'.format(num_rows))
    
#     # 保存图片
#     plt.savefig(f'heatmap_hour_{hour:02d}.png', bbox_inches='tight')
#     plt.close()
    
# print("所有小时热力图生成完毕")

# import pandas as pd
# import matplotlib.pyplot as plt
# import seaborn as sns
# import glob
# import os
# import numpy as np

# # 配置参数
# grid_folder = "grid_v2"  # 新数据存放目录
# output_img_folder = "ratio_heatmaps"  # 热力图输出目录
# os.makedirs(output_img_folder, exist_ok=True)

# # 网格系统参数
# num_cols = 66  # 根据之前计算的列数
# num_rows = 54   # 根据之前计算的行数

# # 创建完整网格索引
# full_cols = pd.Index(range(num_cols), name='x')
# full_rows = pd.Index(range(num_rows), name='y')

# # 颜色配置
# cmap = plt.cm.get_cmap('viridis').copy()
# cmap.set_bad('#e0e0e0')  # 灰色表示无数据
# norm = plt.Normalize(vmin=0, vmax=1)  # 固定比例范围0-1

# # 合并所有数据文件

# df = pd.read_csv('consolidated_data.csv')

# # 数据清洗
# plot_df = df[(df['x'].between(0, num_cols-1)) & 
#              (df['y'].between(0, num_rows-1))].copy()
# plot_df['non_run_ratio'] = plot_df['non_run_ratio'].replace(-1, np.nan)

# # 生成24小时热力图
# for hour in range(24):
#     plt.figure(figsize=(15, 10))
    
#     # 筛选数据并构建矩阵
#     hour_df = plot_df[plot_df['hour'] == hour]
#     matrix = hour_df.pivot_table(
#         index='y',
#         columns='x',
#         values='non_run_ratio',
#         aggfunc='mean'
#     )
    
#     # 对齐完整网格
#     matrix = matrix.reindex(index=full_rows, columns=full_cols)
    
#     # 绘制热力图
#     sns.heatmap(
#         matrix,
#         cmap=cmap,
#         norm=norm,
#         square=True,
#         cbar_kws={'label': '车辆非运行时间占比'},
#         mask=matrix.isnull()
#     )
    
#     # 美化图表
#     plt.title(f'车辆停留热点分布 {hour:02d}:00-{hour+1:02d}:00', fontsize=16)
#     plt.xlabel('网格列号', fontsize=12)
#     plt.ylabel('网格行号', fontsize=12)
#     plt.gca().invert_yaxis()
    
#     # 保存输出
#     plt.savefig(
#         os.path.join(output_img_folder, f'vehicle_stop_ratio_{hour:02d}.png'),
#         bbox_inches='tight',
#         dpi=150,
#         facecolor='white'
#     )
#     plt.close()

# print("热力图生成完成：", output_img_folder)

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams
import matplotlib.ticker as ticker
import numpy as np

# 中文字体配置
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def classify_time_period(hour):
    """动态时段分类"""
    if 7 <= hour < 9:
        return '早高峰 (7-9)'
    elif 11 <= hour < 13:
        return '午间 (11-13)'
    elif 17 <= hour < 19:
        return '晚高峰 (17-19)'
    elif 23 <= hour or hour < 6:
        return '夜间 (23-6)'
    else:
        return '其他时段'

# 读取并处理数据
df = pd.read_csv('v3-districts.csv')

# 数据清洗
df = df[
    df['到达起点时间'].notnull() & 
    df['到达目的地时间'].notnull() & 
    (df['行程里程'] > 0)
]

# 时间处理
df['到达起点时间'] = pd.to_datetime(df['到达起点时间'])
df['出发小时'] = df['到达起点时间'].dt.hour
df['时段'] = df['出发小时'].apply(classify_time_period)

# 过滤有效时段数据
periods = ['早高峰 (7-9)', '午间 (11-13)', '晚高峰 (17-19)', '夜间 (23-6)']
df = df[df['时段'].isin(periods)]

# 设置统一分箱
max_distance = df['行程里程'].max()
bins = np.arange(0, max_distance + 2, 2)  # 2km粒度分箱

# 创建2x2子图布局
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('分时段行程距离分布（2公里粒度）', fontsize=16, y=1.02)

# 为每个时段绘制分布
colors = ['#4C72B0', '#55A868', '#C44E52', '#8172B2']
for idx, period in enumerate(periods):
    ax = axes[idx//2, idx%2]
    period_data = df[df['时段'] == period]['行程里程']
    
    # 绘制直方图
    n, bins, patches = ax.hist(
        period_data, 
        bins=bins,
        color=colors[idx],
        edgecolor='white',
        linewidth=0.8,
        alpha=0.85
    )
    
    # 添加平均线
    avg = period_data.mean()
    ax.axvline(avg, color='red', linestyle='--', linewidth=1.5)
    ax.text(
        avg*1.05, max(n)*0.9, 
        f'平均距离：{avg:.1f}km',
        color='red',
        fontsize=10
    )
    
    # 坐标轴格式化
    ax.xaxis.set_major_locator(ticker.MultipleLocator(10))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(2))
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.grid(which='major', linestyle='--', alpha=0.7)
    ax.grid(which='minor', linestyle=':', alpha=0.3)
    
    # 标签设置
    ax.set_title(f'{period}时段', fontsize=12, pad=12)
    ax.set_xlabel('行程距离（公里）', fontsize=10)
    ax.set_ylabel('订单数量', fontsize=10)
    ax.set_xlim(left=0)

plt.tight_layout()
plt.show()