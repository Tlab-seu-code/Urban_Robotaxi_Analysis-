# -*- coding: utf-8 -*-
"""
Created on Tue Feb 11 17:02:00 2025

@author: WuxiTlab
"""


import os
import pandas as pd
from datetime import datetime

# 获取工作日或休息日
def get_weekday_status(date):
    weekday = datetime.strptime(date, '%Y%m%d').weekday()
    return 0 if weekday < 5 else 1  # 0 for workday, 1 for weekend

# 获取高峰情况
def get_peak_status(time_str):
    time = datetime.strptime(time_str, '%H:%M:%S')
    hour = time.hour
    if 7 <= hour < 10:
        return 0  # Early morning peak
    elif 10 <= hour < 16:
        return 1  # Afternoon
    elif 16 <= hour < 20:
        return 2  # Evening peak
    else:
        return 3  # Nighttime

# 处理每个csv文件
def process_speed_data(file_path):
    # 从文件名中提取日期
    date_str = os.path.basename(file_path).split('.')[0]
    
    # 读取csv文件
    df = pd.read_csv(file_path)

    # 仅保留必要的列：日期、时间、speed、id_y
    df['date'] = date_str
    df = df[['date', 'time', 'speed', 'id_y']]
    
    # 添加工作日/休息日列
    df['is_weekend'] = df['date'].apply(get_weekday_status)
    
    # 添加高峰时间段列
    df['peak_time'] = df['time'].apply(get_peak_status)
    
    return df

# 批量处理speed文件夹下的csv文件
def process_all_files(speed_folder):
    all_data = []
    files = [f for f in os.listdir(speed_folder) if f.endswith('.csv')]
    total_files = len(files)
    
    for idx, file_name in enumerate(files):
        file_path = os.path.join(speed_folder, file_name)
        processed_data = process_speed_data(file_path)
        all_data.append(processed_data)
        
        # 打印进度
        progress = (idx + 1) / total_files * 100
        print(f'Processing file {idx + 1}/{total_files} ({progress:.2f}%)')

    # 合并所有数据
    final_df = pd.concat(all_data, ignore_index=True)
    return final_df

# 调用函数处理所有文件
speed_folder = 'speed_v2'  # 文件夹路径
final_df = process_all_files(speed_folder)

# 保存处理后的数据
final_df.to_csv('processed_speed_data.csv', index=False)
