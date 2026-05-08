# -*- coding: utf-8 -*-
"""
Created on Mon Jun  9 17:33:34 2025

@author: WuxiTlab
"""

# # 能耗因子

import csv
import tempfile
import shutil

CARBON_FACTOR = 522 # 670.77  # 电网碳排放系数 (g/kWh)

# def update_co2_emissions(input_file):
#     # 创建临时文件
#     temp_path = tempfile.mktemp()
    
#     with open(input_file, 'r') as infile, \
#          open(temp_path, 'w', newline='') as outfile:
        
#         reader = csv.DictReader(infile)
#         writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
#         writer.writeheader()

#         for row in reader:
#             # 判断电动车类型（根据实际数据模式调整条件）
#             is_electric = any(kw in row['VehicleType'].lower() 
#                             for kw in {'bev', 'hev_e', 'fox'})
            
#             # 仅处理电动车辆
#             if is_electric and row['Electricity(kWh)'] not in ('-', ''):
#                 try:
#                     # 计算间接排放
#                     electricity = float(row['Electricity(kWh)'])
#                     row['CO2(g)'] = f"{electricity * CARBON_FACTOR:.2f}"
#                 except ValueError:
#                     pass
                    
#             # 保持其他数据不变
#             writer.writerow(row)
    
#     # 用处理后的文件替换原文件
#     shutil.move(temp_path, input_file)

# # 使用示例（直接覆盖原文件）
# update_co2_emissions('vehicle_stats_detail_av.csv')

# ##### 增加所属grid

# import pandas as pd

# # 保持原始网格参数和函数不变
# min_lon = 113.942617
# max_lon = 114.629031
# min_lat = 30.255898
# max_lat = 30.742468
# lon_step = 0.0103997242944
# lat_step = 0.0089831117499

# num_cols = int(round((max_lon - min_lon) / lon_step))
# num_rows = int(round((max_lat - min_lat) / lat_step))

# def get_grid_xy(lon, lat):
#     """严格保持用户原始函数逻辑"""
#     if pd.isna(lon) or pd.isna(lat):
#         return (-1, -1)
#     if not (min_lon <= lon < max_lon and min_lat <= lat < max_lat):
#         return (-1, -1)
    
#     x = int((lon - min_lon) / lon_step)
#     y = int((lat - min_lat) / lat_step)
    
#     if x < 0 or x >= num_cols or y < 0 or y >= num_rows:
#         return (-1, -1)
    
#     return (x, y)

# # 定义数据处理管道
# def process_data(df):
#     """完全基于原始函数的数据处理流程"""
#     # 处理起点坐标
#     df['start_grid'] = df.apply(
#         lambda r: get_grid_xy(r['Longitude'], r['Latitude']),
#         axis=1
#     )
    
#     # 拆分网格坐标
#     df[['grid_x', 'grid_y']] = pd.DataFrame(
#         df['start_grid'].tolist(),
#         index=df.index
#     )

    
#     # 清理中间列
#     return df.drop(columns=['start_grid'])

# # 执行处理
# df = pd.read_csv("vehicle_stats_detail_av.csv")
# df_processed = process_data(df)

# # 验证结果格式
# print(df_processed[['grid_x', 'grid_y']].head(2))

# # 保存结果
# df_processed.to_csv("vehicle_stats_detail_av_v2.csv", index=False, encoding='utf_8_sig')

import csv
import tempfile
import shutil
import os
from collections import defaultdict
from datetime import datetime
import time
import pandas as pd

# 原始网格参数（保持用户给定值）
min_lon = 113.942617
max_lon = 114.629031
min_lat = 30.255898
max_lat = 30.742468
lon_step = 0.0103997242944
lat_step = 0.0089831117499

num_cols = int(round((max_lon - min_lon) / lon_step))
num_rows = int(round((max_lat - min_lat) / lat_step))


def get_grid_xy(lon, lat):
    """严格保持用户原始函数逻辑"""
    if pd.isna(lon) or pd.isna(lat):
        return (-1, -1)
    if not (min_lon <= lon < max_lon and min_lat <= lat < max_lat):
        return (-1, -1)
    
    x = int((lon - min_lon) / lon_step)
    y = int((lat - min_lat) / lat_step)
    
    if x < 0 or x >= num_cols or y < 0 or y >= num_rows:
        return (-1, -1)
    
    return (x, y)

class EnhancedProcessor:
    def __init__(self, input_file):
        self.input_file = input_file
        self.grid_stats = defaultdict(float)
        # self.total_rows = self._count_total_rows()
        self.processed = 0
        self.start_time = datetime.now()

    def _count_total_rows(self):
        """高效行数统计"""
        with open(self.input_file, 'r') as f:
            next(f)  # 跳过标题行
            return sum(1 for _ in f)

    def _print_progress(self, t):
        """智能进度显示"""
        elapsed = datetime.now() - self.start_time
        # percent = self.processed / self.total_rows * 100
        speed = self.processed / elapsed.total_seconds() if elapsed.seconds > 0 else 0
        msg = (f"已处理: {t}| "
               f"已处理: {self.processed}| "
               f"速度: {speed:.1f}行/秒 | "
               f"有效网格: {len(self.grid_stats)}")
        print(f"\r{msg}", end='', flush=True)

    def process(self, output_csv):
        temp_path = tempfile.mktemp()
        last_print = 0
        
        with open(self.input_file, 'r') as infile, \
             open(temp_path, 'w', newline='') as outfile:

            reader = csv.DictReader(infile)
            writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
            writer.writeheader()

            for row in reader:
                # 原CO2计算逻辑
                co2 = 0.0
                is_electric = any(kw in row['VehicleType'].lower() 
                                for kw in {'bev', 'hev_e', 'fox'})
                if is_electric and row['Electricity(kWh)'] not in ('-', ''):
                    try:
                        electricity = float(row['Electricity(kWh)'])
                        co2 = electricity * CARBON_FACTOR
                        row['CO2(g)'] = f"{co2:.2f}"
                    except ValueError:
                        pass

                # 网格统计
                try:
                    lon = float(row['Longitude'])
                    lat = float(row['Latitude'])
                    grid_x, grid_y = get_grid_xy(lon, lat)
                    if grid_x != -1 and grid_y != -1:
                        self.grid_stats[(grid_x, grid_y)] += co2
                except (ValueError, KeyError):
                    pass

                writer.writerow(row)
                self.processed += 1

                # 动态更新进度（每1%或每秒更新）
                if time.time() - last_print > 10:
                    self._print_progress(row['Timestamp(s)'])
                    last_print = time.time()

        # 完成处理
        shutil.move(temp_path, self.input_file)
        self._save_grid_stats(output_csv)
        print(f"\n总用时: {datetime.now() - self.start_time}")

    def _save_grid_stats(self, output_csv):
        with open(output_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['grid_x', 'grid_y', 'CO2(g)'])
            for (x, y), total in sorted(self.grid_stats.items()):
                writer.writerow([x, y, round(total, 2)])

def update_co2_emissions(input_file, output_csv='grid_co2_stats.csv'):
    processor = EnhancedProcessor(input_file)
    print(f"开始处理 {os.path.basename(input_file)}")
    processor.process(output_csv)

# 使用示例
update_co2_emissions('vehicle_stats_detail_hdv.csv')