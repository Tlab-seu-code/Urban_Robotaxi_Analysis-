# -*- coding: utf-8 -*-
"""
Created on Tue Jun 10 16:10:20 2025

@author: WuxiTlab
"""

    
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from datetime import datetime, timedelta

def plot_final_heatmap(date, interval_minutes=10):
    # 设置Nature样式参数
    plt.rcParams.update({
        'font.sans-serif': 'Arial',
        'font.size': 8,
        'axes.labelsize': 10,
        'axes.titlesize': 12,
        'xtick.labelsize': 6,
        'ytick.labelsize': 8,
        'figure.dpi': 300,
        'figure.figsize': (8, 2)  # 新尺寸要求
    })
    
    # 数据预处理
    df = pd.read_csv('v3-districts.csv')
    df = df[df['订单状态'] != '取消']
    
    time_cols = ['呼单时间', '取消时间']
    for col in time_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    
    target_date = pd.to_datetime(date)
    df = df[df['呼单时间'].dt.date == target_date.date()]
    
    # 生成时间网格
    time_bins = pd.date_range(start=f"{date} 00:00:00", 
                            end=f"{date} 23:59:59", 
                            freq=f"{interval_minutes}T")
    
    # 创建转置矩阵
    vehicles = df['车辆id'].unique()
    status_matrix = np.zeros((len(time_bins)-1, len(vehicles)), dtype=np.uint8)
    
    # 状态优先级编码
    status_priority = status_priority = {
            '调度单': 1,
            '充电单': 2,
            'app': 3,
            '小程序': 3,
            '百度地图': 3
        }
    for vidx, vehicle in enumerate(vehicles):
        orders = df[df['车辆id'] == vehicle]
        for _, row in orders.iterrows():
            start = row['呼单时间']
            end = row['取消时间'] if pd.notnull(row['取消时间']) else start + timedelta(minutes=10)
            
            # 计算时间槽
            left = np.searchsorted(time_bins, start, side='right') - 1
            right = np.searchsorted(time_bins, end, side='left')
            slots = slice(max(0, left), min(len(time_bins)-1, right))
            
            # 更新矩阵
            current_code = status_priority.get(row['订单来源'], 0)
            np.maximum(status_matrix[slots, vidx], current_code, out=status_matrix[slots, vidx])
    
    # 创建可视化
    fig, ax = plt.subplots()
    cmap = plt.cm.colors.ListedColormap([
        '#F0F0F0',  # Idle
        '#4E79A7',  # Dispatch
        '#59A14F',  # Charging
        '#E15759'   # Passenger
    ])
    
    # 显示转置矩阵
    im = ax.imshow(status_matrix, aspect='auto', cmap=cmap,
                  origin='lower', interpolation='none',
                  extent=[0, len(vehicles), 0, len(time_bins)-1])
    
    # 坐标轴设置
    ax.set_xlabel('Vehicle ID', labelpad=2)
    ax.set_ylabel('Time', labelpad=2)
    ax.yaxis.set_label_position("right")
    ax.yaxis.tick_right()
    
    # 时间刻度（y轴）
    yticks = np.arange(0, len(time_bins), 6*60//interval_minutes)
    ax.set_yticks(yticks)
    ax.set_yticklabels([time_bins[i].strftime('%H:%M') for i in yticks], 
                      rotation=0, va='center')
    
    # 车辆ID刻度（x轴）
    # ax.set_xticks(np.arange(len(vehicles)))
    # ax.set_xticklabels(vehicles, rotation=90, ha='center', fontsize=4)
    # ax.xaxis.set_major_locator(plt.MaxNLocator(20))  # 显示部分ID
    
    # 图例
    legend_elements = [
        Patch(facecolor='#E15759', edgecolor='w', label='Passenger'),
        Patch(facecolor='#59A14F', edgecolor='w', label='Charging'),
        Patch(facecolor='#4E79A7', edgecolor='w', label='Dispatch'),
        Patch(facecolor='#F0F0F0', edgecolor='w', label='Idle')
    ]
    ax.legend(handles=legend_elements, loc='lower center',
             bbox_to_anchor=(0.5, -1.29), ncol=4)
    
    plt.tight_layout(pad=0.5)
    plt.savefig('final_heatmap.svg', bbox_inches='tight')
    plt.show()

# 使用示例
plot_final_heatmap('2024/12/2')
