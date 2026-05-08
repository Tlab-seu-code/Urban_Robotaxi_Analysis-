# -*- coding: utf-8 -*-
"""
Created on Mon Jun  9 20:50:31 2025

@author: WuxiTlab
"""

import pandas as pd
import numpy as np

def clean_hv_data(input_file, output_file):
    # 读取原始数据
    df = pd.read_csv(input_file)
    
    # 基础数据校验
    original_count = len(df)
    
    # 转换时间格式并计算行程时间（秒）
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['end_time'] = pd.to_datetime(df['end_time'])
    df['duration'] = (df['end_time'] - df['start_time']).dt.total_seconds()
    
    # 初步过滤
    df_clean = df[
        (df['duration'] > 60) &           # 行程时间大于1分钟
        (df['travel_length'] > 100) &     # 行程距离大于100米
        (df['duration'] < 4*3600) &       # 行程时间小于4小时
        (df['travel_length'] < 150000)    # 行程距离小于150公里
    ].copy()
    
    # 计算速度（km/h）
    df_clean['speed'] = (df_clean['travel_length']/1000) / (df_clean['duration']/3600)
    
    # 速度合理性过滤
    df_clean = df_clean[
        (df_clean['speed'] > 1) & 
        (df_clean['speed'] < 120)
    ]
    
    # IQR方法过滤异常值
    def filter_iqr(series, iqr_factor=3):
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - iqr_factor*iqr
        upper_bound = q3 + iqr_factor*iqr
        return (series >= lower_bound) & (series <= upper_bound)
    
    duration_filter = filter_iqr(df_clean['duration'])
    distance_filter = filter_iqr(df_clean['travel_length'])
    speed_filter = filter_iqr(df_clean['speed'])
    
    df_final = df_clean[duration_filter & distance_filter & speed_filter]
    
    # 输出清洗结果
    print(f"原始数据记录数: {original_count}")
    print(f"清洗后保留记录数: {len(df_final)}")
    print(f"数据清洗完成，保存路径: {output_file}")
    
    # 保存清洗后的数据
    df_final.to_csv(output_file, index=False)

# 执行清洗
clean_hv_data('v9-hdv.csv', 'v10-hdv.csv')