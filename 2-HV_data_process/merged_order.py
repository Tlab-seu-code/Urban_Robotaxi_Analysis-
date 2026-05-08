# -*- coding: utf-8 -*-
"""
Created on Thu May  8 20:22:41 2025

@author: WuxiTlab
"""

import os
import pandas as pd
import re

folder_path = 'length_output'
output_file = 'merged_orders_with_length.csv'
all_dfs = []

for filename in os.listdir(folder_path):
    match = re.match(r'(\d{8})_orders_with_length\.csv', filename)
    if match:
        date_str = match.group(1)
        file_path = os.path.join(folder_path, filename)
        
        df = pd.read_csv(file_path)
        df['date'] = date_str

        # 重新计算 average_speed（单位：km/h）
        df['average_speed'] = (df['travel_length'] / df['duration']) * 3.6  # 米/秒 -> km/h
        
        all_dfs.append(df)

# 合并所有数据c
merged_df = pd.concat(all_dfs, ignore_index=True)

# 保存结果
merged_df.to_csv(output_file, index=False)

print(f"已合并并修正 average_speed，保存为 {output_file}")
