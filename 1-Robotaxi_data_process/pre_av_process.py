# -*- coding: utf-8 -*-
"""
Created on Thu May  8 20:48:17 2025

@author: TLab
"""

import pandas as pd

# # 读取原始文件
# df = pd.read_csv("v3-districts.csv")

# # 筛选乘客单
# df_passenger = df[
#     (df['订单状态'] == '完成') &
#     (~df['订单来源'].isin(['调度单', '充电单']))
# ].copy()

# # 替换异常或缺失值为0，避免除以0错误
# df_passenger['行程时长'] = pd.to_numeric(df_passenger['行程时长'], errors='coerce').fillna(0)
# df_passenger['行程里程'] = pd.to_numeric(df_passenger['行程里程'], errors='coerce').fillna(0)

# # 仅在行程时长 > 0 时计算平均速度
# df_passenger['average_speed'] = df_passenger.apply(
#     lambda row: (row['行程里程'] / row['行程时长']) * 3600 if row['行程时长'] > 0 else 0,
#     axis=1
# )

# # 保存结果
# df_passenger.to_csv("v4-av.csv", index=False, encoding='utf-8-sig')

# print("已筛选乘客单并计算平均速度，保存为 v3-districts_passenger_with_speed.csv")

# # 读取合并后的HDV文件
# hdv_path = "v1-hdv.csv"
# df_hdv = pd.read_csv(hdv_path)

# # 重算平均速度（km/h）
# df_hdv["average_speed"] = (df_hdv["travel_length"] / df_hdv["duration"]) * 3.6

# # 数据清洗条件
# condition = (
#     (df_hdv["start_lon"] != 0) & (df_hdv["start_lat"] != 0) &
#     (df_hdv["end_lon"] != 0) & (df_hdv["end_lat"] != 0) &
#     (df_hdv["travel_length"] <= 500000) &  # 小于等于500km
#     (df_hdv["travel_length"] >= 50) &      # 大于等于50米
#     (df_hdv["average_speed"] <= 200) &
#     (df_hdv["average_speed"] >= 0.1)
# )

# # 过滤数据
# df_cleaned = df_hdv[condition].copy()
# df_cleaned["start_time"] = pd.to_datetime(df_cleaned["start_time"]).dt.time.astype(str)
# df_cleaned["end_time"] = pd.to_datetime(df_cleaned["end_time"]).dt.time.astype(str)
# # 保存为 v2-hdv.csv
# output_path = "v2-hdv.csv"
# df_cleaned.to_csv(output_path, index=False)

# import pandas as pd
# import numpy as np
# from scipy.stats import ttest_ind
# import matplotlib.pyplot as plt

# # 读取HDV和AV数据
# hdv_df = pd.read_csv("v2-hdv.csv")
# av_df = pd.read_csv("v4-av.csv")

# # 确保时间字段为datetime格式
# hdv_df['start_time'] = pd.to_datetime(hdv_df['start_time'])
# av_df['开始行程时间'] = pd.to_datetime(av_df['开始行程时间'], errors='coerce')

# # 增加小时字段
# hdv_df['hour'] = pd.to_datetime(hdv_df['start_time'], format="%H:%M:%S").dt.hour
# av_df['hour'] = av_df['开始行程时间'].dt.hour

# # 定义时段划分函数
# def get_time_period(hour):
#     if 7 <= hour <= 9:
#         return 'morning'  # 早高峰 
#     elif 9 <= hour <= 16:
#         return 'midday'   # 日间
#     elif 17 <= hour <= 20:
#         return 'evening'  # 晚高峰
#     else: #if hour < 6 or hour >= 22:
#         return 'night'  # 晚高峰
#     # else:
#     #     return 'rest'    # 夜间    

# hdv_df['time_period'] = hdv_df['hour'].apply(get_time_period)
# av_df['time_period'] = av_df['hour'].apply(get_time_period)

# # 各时段的t检验并保存p值
# time_periods = ['morning', 'midday', 'evening', 'night', 'rest']
# p_values = []
# mean_diffs = []

# for period in time_periods:
#     hdv_speeds = hdv_df[hdv_df['time_period'] == period]['average_speed'].dropna()
#     av_speeds = av_df[av_df['time_period'] == period]['average_speed'].dropna()
#     t_stat, p_val = ttest_ind(hdv_speeds, av_speeds, equal_var=False)
#     p_values.append(p_val)
#     mean_diffs.append(hdv_speeds.mean() - av_speeds.mean())
#     print(len(hdv_speeds))
#     print(hdv_speeds.mean())
#     print(len(av_speeds))
#     print(av_speeds.mean())
#     print("---")

# # 绘图：条形图展示每个时段HDV比AV快的平均速度差和显著性
# fig, ax = plt.subplots(figsize=(10, 6))
# bars = ax.bar(time_periods, mean_diffs, color='skyblue', edgecolor='black')
# ax.axhline(0, color='grey', linewidth=0.8, linestyle='--')
# ax.set_ylabel("Speed Difference (HDV - AV) in km/h")
# ax.set_title("Average Speed Difference Between HDV and AV by Time Period")

# # 添加显著性标注
# for i, (bar, p_val) in enumerate(zip(bars, p_values)):
#     height = bar.get_height()
#     signif = 0
#     if p_val < 0.001:
#         signif = p_val
#     elif p_val < 0.01:
#         signif = p_val
#     elif p_val < 0.05:
#         signif = p_val
#     ax.text(bar.get_x() + bar.get_width()/2, height + 0.2, signif,
#             ha='center', va='bottom', fontsize=12)

# plt.tight_layout()
# plt.show()


##### 正态分布

# import pandas as pd
# import numpy as np
# from scipy.stats import ttest_ind
# import matplotlib.pyplot as plt

# # 读取数据
# hdv_df = pd.read_csv("v10-hdv.csv")
# av_df = pd.read_csv("v4-av.csv")

# # 统一时间格式
# hdv_df['start_time'] = pd.to_datetime(hdv_df['start_time'])
# av_df['开始行程时间'] = pd.to_datetime(av_df['开始行程时间'], errors='coerce')

# # 提取小时信息
# hdv_df['hour'] = hdv_df['start_time'].dt.hour
# av_df['hour'] = av_df['开始行程时间'].dt.hour

# # 定义时段
# def get_time_period(hour):
#     if 7 <= hour <= 9:
#         return 'morning'  # 早高峰 
#     elif 9 <= hour <= 16:
#         return 'midday'   # 日间
#     elif 17 <= hour <= 20:
#         return 'evening'  # 晚高峰
#     else: #if hour < 6 or hour >= 22:
#         return 'night'  # 晚高峰
#     # else:
#     #     return 'rest'    # 夜间   

# hdv_df['time_period'] = hdv_df['hour'].apply(get_time_period)
# av_df['time_period'] = av_df['hour'].apply(get_time_period)

# # 时段列表
# time_periods = ['morning', 'midday', 'evening', 'night']

# # 保存分析结果
# results = []

# for period in time_periods:
#     hdv_speeds = hdv_df[hdv_df['time_period'] == period]['average_speed'].dropna()
#     av_speeds = av_df[av_df['time_period'] == period]['average_speed'].dropna()
    
#     # t 检验（Welch's t-test 不假设方差齐性）
#     t_stat, p_val_two_tailed = ttest_ind(hdv_speeds, av_speeds, equal_var=False)
    
#     # 单尾检验：H0: HDV <= AV, H1: HDV > AV
#     if t_stat > 0:
#         p_val = p_val_two_tailed / 2
#     else:
#         p_val = 1 - p_val_two_tailed / 2
    
#     # 自由度计算（Welch–Satterthwaite equation）
#     s1, s2 = np.var(hdv_speeds, ddof=1), np.var(av_speeds, ddof=1)
#     n1, n2 = len(hdv_speeds), len(av_speeds)
#     df = (s1/n1 + s2/n2)**2 / ((s1**2)/(n1**2*(n1-1)) + (s2**2)/(n2**2*(n2-1)))
    
#     # 置信区间（95%），计算差的 CI
#     mean_diff = hdv_speeds.mean() - av_speeds.mean()
#     se = np.sqrt(s1/n1 + s2/n2)
#     ci_low = mean_diff - 1.96 * se
#     ci_high = mean_diff + 1.96 * se

#     # 保存结果
#     results.append({
#         'Period': period,
#         'HDV Mean': hdv_speeds.mean(),
#         'AV Mean': av_speeds.mean(),
#         'HDV Std': np.std(hdv_speeds, ddof=1),
#         'AV Std': np.std(av_speeds, ddof=1),
#         'HDV N': n1,
#         'AV N': n2,
#         'Mean Diff': mean_diff,
#         'T-Stat': t_stat,
#         'DF': df,
#         'CI Lower': ci_low,
#         'CI Upper': ci_high,
#         'P-Value (one-tailed)': p_val
#     })

# # 转换为 DataFrame 并打印
# result_df = pd.DataFrame(results)
# print(result_df.round(4))

# # 绘图展示平均速度差（HDV - AV）
# fig, ax = plt.subplots(figsize=(10, 6))
# bars = ax.bar(result_df['Period'], result_df['Mean Diff'], color='skyblue', edgecolor='black')
# ax.axhline(0, color='grey', linewidth=0.8, linestyle='--')
# ax.set_ylabel("Mean Speed Difference (HDV - AV) [km/h]")
# ax.set_title("Speed Advantage of HDV over AV in Different Time Periods")

# # 添加 p 值注释
# for i, row in result_df.iterrows():
#     height = row['Mean Diff']
#     signif_text = f"p={row['P-Value (one-tailed)']:.3f}"
#     ax.text(i, height + 0.2 if height >= 0 else height - 0.4, signif_text,
#             ha='center', va='bottom', fontsize=11, color='red' if row['P-Value (one-tailed)'] < 0.05 else 'black')

# plt.tight_layout()
# plt.show()


# import pandas as pd

# def merge_additional_fields(base_csv="v5_traj.csv", info_csv="v4-av.csv", output_csv="v5_traj_updated.csv"):
#     # 1. 读取两个文件
#     df_base = pd.read_csv(base_csv)
#     df_info = pd.read_csv(info_csv)

#     # 2. 保留info中我们需要的字段
#     fields_to_keep = ['订单号', '服务人次', '订单来源', '车辆id', '订单状态']
#     df_info = df_info[fields_to_keep]

#     # 3. 合并两个表：左连接，保留v5_traj中的所有数据
#     df_merged = pd.merge(df_base, df_info, on="订单号", how="left")

#     # 4. 保存结果
#     df_merged.to_csv(output_csv, index=False)
#     print(f"[完成] 已合并字段并保存为：{output_csv}")

# merge_additional_fields(
#     base_csv="v5_traj.csv",
#     info_csv="v4-av.csv",
#     output_csv="v6_traj .csv"
# )
# import pandas as pd

# 保持原始网格参数和函数不变
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

# 定义数据处理管道
def process_data(df):
    """完全基于原始函数的数据处理流程"""
    # 处理起点坐标
    df['start_grid'] = df.apply(
        lambda r: get_grid_xy(r['起点经度'], r['起点纬度']),
        axis=1
    )
    # 处理终点坐标
    df['end_grid'] = df.apply(
        lambda r: get_grid_xy(r['终点经度'], r['终点纬度']),
        axis=1
    )
    
    # 拆分网格坐标
    df[['grid_x_start', 'grid_y_start']] = pd.DataFrame(
        df['start_grid'].tolist(),
        index=df.index
    )
    df[['grid_x_end', 'grid_y_end']] = pd.DataFrame(
        df['end_grid'].tolist(),
        index=df.index
    )
    
    # 清理中间列
    return df.drop(columns=['start_grid', 'end_grid'])

# 执行处理
# df = pd.read_csv("v3-districts.csv")
# df_processed = process_data(df)

# # 验证结果格式
# print(df_processed[['grid_x_start', 'grid_y_start', 'grid_x_end', 'grid_y_end']].head(2))

# 保存结果
# df_processed.to_csv("v3-districts.csv", index=False, encoding='utf_8_sig')


# HDV加grid

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
#         lambda r: get_grid_xy(r['start_lon'], r['start_lat']),
#         axis=1
#     )
#     # 处理终点坐标
#     df['end_grid'] = df.apply(
#         lambda r: get_grid_xy(r['end_lon'], r['end_lat']),
#         axis=1
#     )
    
#     # 拆分网格坐标
#     df[['grid_x_start', 'grid_y_start']] = pd.DataFrame(
#         df['start_grid'].tolist(),
#         index=df.index
#     )
#     df[['grid_x_end', 'grid_y_end']] = pd.DataFrame(
#         df['end_grid'].tolist(),
#         index=df.index
#     )
    
#     # 清理中间列
#     return df.drop(columns=['start_grid', 'end_grid'])

# # 执行处理
# df = pd.read_csv("v2-hdv.csv")
# df_processed = process_data(df)

# # 验证结果格式
# print(df_processed[['grid_x_start', 'grid_y_start', 'grid_x_end', 'grid_y_end']].head(2))

# # 保存结果
# df_processed.to_csv("v9-hdv.csv", index=False, encoding='utf_8_sig')


# import pandas as pd  
  
# # 读取v7-av.csv文件  
# v7_df = pd.read_csv('v7-av.csv')  
  
# # 读取v3-districts.csv文件  
# v3_df = pd.read_csv('v3-districts.csv')  
  
# # 检查两个DataFrame中的订单号列名是否一致，如果不一致需要进行重命名  
# # 假设v7-av.csv中的订单号列名为'订单号'，v3-districts.csv中的订单号列名也为'订单号'  
  
# # 使用merge函数根据订单号合并两个DataFrame，这里使用左连接，以v7_df为基础  
# merged_df = pd.merge(v7_df, v3_df[['订单号', '车辆id', '用户id']], on='订单号', how='left')  
  
# # 检查合并后的DataFrame  
# print(merged_df.head())  
  
# # 如果需要，可以将合并后的DataFrame保存到新的CSV文件中  
# merged_df.to_csv('v8_av.csv', index=False, encoding='utf_8_sig')

# grid统计

import pandas as pd
import numpy as np
from datetime import datetime

# 时间分桶函数（符合GB/T 7408-2005 数据元和交换格式）
def time_to_period(timestamp: pd.Series) -> pd.Series:
    """将时间序列转换为半小时时段编号"""
    return (timestamp.dt.hour * 2 + timestamp.dt.minute // 30).astype('int')

# 预处理流程
def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """兼容多日期格式的预处理"""
    # 统一处理前导/后导空格
    df['呼单时间'] = df['呼单时间'].str.strip()
    df['到达目的地时间'] = df['到达目的地时间'].str.strip()

    # 精确解析呼单时间（格式：2024/11/12 0:03:00）
    df['呼单时间'] = pd.to_datetime(
        df['呼单时间'],
        format='%Y/%m/%d %H:%M:%S',
        errors='coerce'
    )
    
    # 精确解析到达时间（格式：11/12/2024 0:22）
    df['到达目的地时间'] = pd.to_datetime(
        df['到达目的地时间'],
        format='%m/%d/%Y %H:%M',
        errors='coerce'
    )
    
    # 生成日期和时段（过滤无效时间）
    valid_start = df['呼单时间'].notna()
    valid_end = df['到达目的地时间'].notna()
    
    df['日期'] = df['呼单时间'].dt.normalize()
    df.loc[valid_start, 'start_period'] = time_to_period(df.loc[valid_start, '呼单时间'])
    df.loc[valid_end, 'end_period'] = time_to_period(df.loc[valid_end, '到达目的地时间'])
    
    return df

# 统计起点订单（带车辆id去重）
def count_start_orders(df: pd.DataFrame) -> pd.DataFrame:
    """统计各网格起点订单量（排除取消订单）"""
    # 添加订单状态过滤条件（假设状态列为'订单状态'，取消状态为'取消'）
    start_df = df[
        (df['grid_x_start'] >= 0) &
        (df['订单状态'] == '取消')  # 新增状态过滤条件
    ].copy()
    
    return start_df.groupby(
        ['日期', 'start_period', 'grid_x_start', 'grid_y_start']
    ).agg(
        起点订单总数量=('车辆id', 'nunique')  # 按车辆id去重计数
    ).reset_index()

# 统计终点订单（带车辆id去重）
def count_end_orders(df: pd.DataFrame) -> pd.DataFrame:
    """统计各网格终点完成单量"""
    end_df = df[(df['grid_x_end'] >= 0) & (df['订单状态'] == '完成')].copy()
    
    return end_df.groupby(
        ['日期', 'end_period', 'grid_x_end', 'grid_y_end']
    ).agg(
        终点订单总数量=('车辆id', 'nunique')  # 按车辆id去重计数
    ).reset_index()

# 主处理流程
def process_orders(df: pd.DataFrame) -> pd.DataFrame:
    # 预处理
    df = preprocess(df)
    
    # 分别统计起点和终点
    start_stats = count_start_orders(df).rename(columns={
        'start_period': '时间段',
        'grid_x_start': 'grid_x',
        'grid_y_start': 'grid_y'
    })
    
    end_stats = count_end_orders(df).rename(columns={
        'end_period': '时间段',
        'grid_x_end': 'grid_x',
        'grid_y_end': 'grid_y'
    })
    
    # 合并结果（全外连接）
    merged = pd.merge(
        start_stats,
        end_stats,
        on=['日期', '时间段', 'grid_x', 'grid_y'],
        how='outer'
    ).fillna(0)
    
    # 规范数据类型
    merged[['起点订单总数量', '终点订单总数量']] = merged[['起点订单总数量', '终点订单总数量']].astype('int32')
    
    return merged

# 执行分析
# if __name__ == "__main__":
#     df = pd.read_csv("v8-av.csv")
    
#     result = process_orders(df)
    
#     # 输出示例
#     print(result[(result['grid_x']==42)&(result['grid_y']==35)].head())
    
#     # 保存结果
#     result.to_csv("spatio-temporal-stats-cancel.csv", index=False, encoding='utf_8_sig')

# import pandas as pd
# import numpy as np
# from datetime import datetime

# # 时间分桶函数（符合GB/T 7408-2005 数据元和交换格式）
# def time_to_period(timestamp: pd.Series) -> pd.Series:
#     """将时间序列转换为半小时时段编号"""
#     return (timestamp.dt.hour * 2 + timestamp.dt.minute // 30).astype('int')

# # 预处理流程
# def preprocess(df: pd.DataFrame) -> pd.DataFrame:
#     """兼容多日期格式的预处理"""
#     # 统一处理前导/后导空格
#     df['start_time'] = df['start_time'].str.strip()
#     df['end_time'] = df['end_time'].str.strip()

#     # 精确解析start_time（格式：2024/11/12 0:03:00）
#     df['start_time'] = pd.to_datetime(
#         df['start_time'],
#         format='%Y-%m-%d %H:%M:%S',
#         errors='coerce'
#     )
    
#     # 精确解析到达时间（格式：11/12/2024 0:22）
#     df['end_time'] = pd.to_datetime(
#         df['end_time'],
#         format='%Y-%m-%d %H:%M:%S',
#         errors='coerce'
#     )
    
#     # 生成日期和时段（过滤无效时间）
#     valid_start = df['start_time'].notna()
#     valid_end = df['end_time'].notna()
    
#     df['日期'] = df['date']
#     df.loc[valid_start, 'start_period'] = time_to_period(df.loc[valid_start, 'start_time'])
#     df.loc[valid_end, 'end_period'] = time_to_period(df.loc[valid_end, 'end_time'])
    
#     return df

# # 统计起点订单（带车辆id去重）
# def count_start_orders(df: pd.DataFrame) -> pd.DataFrame:
#     """统计各网格起点订单量（排除取消订单）"""
#     # 添加订单状态过滤条件（假设状态列为'订单状态'，取消状态为'取消'）
#     start_df = df[
#         (df['grid_x_start'] >= 0) #&
#         #(df['订单状态'] != '取消')  # 新增状态过滤条件
#     ].copy()
    
#     return start_df.groupby(
#         ['日期', 'start_period', 'grid_x_start', 'grid_y_start']
#     ).agg(
#         起点订单总数量=('vehicle_id', 'nunique')  # 按车辆id去重计数
#     ).reset_index()

# # 统计终点订单（带车辆id去重）
# def count_end_orders(df: pd.DataFrame) -> pd.DataFrame:
#     """统计各网格终点完成单量"""
#     end_df = df[(df['grid_x_end'] >= 0)].copy()
    
#     return end_df.groupby(
#         ['日期', 'end_period', 'grid_x_end', 'grid_y_end']
#     ).agg(
#         终点订单总数量=('vehicle_id', 'nunique')  # 按车辆id去重计数
#     ).reset_index()

# # 主处理流程
# def process_orders(df: pd.DataFrame) -> pd.DataFrame:
#     # 预处理
#     df = preprocess(df)
    
#     # 分别统计起点和终点
#     start_stats = count_start_orders(df).rename(columns={
#         'start_period': '时间段',
#         'grid_x_start': 'grid_x',
#         'grid_y_start': 'grid_y'
#     })
    
#     end_stats = count_end_orders(df).rename(columns={
#         'end_period': '时间段',
#         'grid_x_end': 'grid_x',
#         'grid_y_end': 'grid_y'
#     })
    
#     # 合并结果（全外连接）
#     merged = pd.merge(
#         start_stats,
#         end_stats,
#         on=['日期', '时间段', 'grid_x', 'grid_y'],
#         how='outer'
#     ).fillna(0)
    
#     # 规范数据类型
#     merged[['起点订单总数量', '终点订单总数量']] = merged[['起点订单总数量', '终点订单总数量']].astype('int32')
    
#     return merged

# # 执行分析
# if __name__ == "__main__":
#     df = pd.read_csv("v9-hdv.csv")
    
#     result = process_orders(df)
    
#     # 输出示例
#     print(result[(result['grid_x']==42)&(result['grid_y']==35)].head())
    
#     # 保存结果
#     result.to_csv("spatio-temporal-stats-hdv.csv", index=False, encoding='utf_8_sig')



###################### 天气分析

import pandas as pd

# # 读取数据
# df = pd.read_csv('v8-av.csv', parse_dates=['呼单时间'])

# # 提取日期和区域（按网格）
# df['日期'] = df['呼单时间'].dt.date
# df['区域'] = df[['grid_x_start', 'grid_y_start']].astype(str).agg('_'.join, axis=1)

# # 筛选雨天记录（降水量 > 0）
# rain_days = df[df['降水量'] > 0][['日期', '区域', '呼单时间']]

# # 检查转晴记录
# results = []
# for index, rain_row in rain_days.iterrows():
#     date = rain_row['日期']
#     area = rain_row['区域']
#     rain_time = rain_row['呼单时间']
    
#     # 同一区域当天后续的非雨天记录
#     clear_mask = (
#         (df['日期'] == date) & 
#         (df['区域'] == area) & 
#         (df['呼单时间'] > rain_time) & 
#         (df['降水量'] == 0) & 
#         (~df['天气状态'].isin(['雨', '雷阵雨']))  # 根据实际天气状态调整
#     )
#     clear_after = df[clear_mask]
    
#     if not clear_after.empty:
#         results.append({
#             '日期': date,
#             '区域': area,
#             '转晴时间': clear_after['呼单时间'].min().strftime('%H:%M'),
#             '雨天时间': rain_time.strftime('%H:%M')
#         })

# # 输出结果
# if results:
#     result_df = pd.DataFrame(results).drop_duplicates()
#     print("存在雨天转晴的日期及区域：")
#     print(result_df)
# else:
#     print("无符合条件的雨天转晴记录。")


##################差异分析

# import pandas as pd

# # 读取数据并解析时间
# df = pd.read_csv("v8-av.csv", parse_dates=["呼单时间"])

# # 生成30分钟时间窗口和日期
# df["时间窗口"] = df["呼单时间"].dt.floor("30min")
# df["日期"] = df["呼单时间"].dt.date

# # 按时间窗口和行政区分组，统计天气指标
# weather_analysis = df.groupby(["日期", "时间窗口", "起点所属区"]).agg(
#     平均降水量=("降水量", "mean"),
#     主要天气状态=("天气状态", lambda x: x.mode()[0] if not x.empty else None),
#     订单量=("订单号", "count")
# ).reset_index()

# # 按时间窗口分析差异
# results = []
# for (date, window), group in weather_analysis.groupby(["日期", "时间窗口"]):
#     if len(group) > 1:  # 仅统计有多个区域的窗口
#         precip_diff = group["平均降水量"].max() - group["平均降水量"].min()
#         unique_states = group["主要天气状态"].unique()
#         results.append({
#             "日期": date,
#             "时间窗口": window,
#             "区域数量": len(group),
#             "最大降水量差(mm)": precip_diff,
#             "不同天气类型数": len(unique_states),
#             "天气类型示例": "/".join(unique_states)
#         })

# # 输出结果
# result_df = pd.DataFrame(results).to_csv("Weather.csv", index=False, encoding='utf_8_sig')
# # print(result_df.head())

# import pandas as pd
# import matplotlib.pyplot as plt
# import matplotlib.dates as mdates

# # Load data (original Chinese column names preserved)
# df = pd.read_csv("v8-av.csv", parse_dates=["呼单时间"])

# # Process hourly data
# df["Hour"] = df["呼单时间"].dt.floor("h")
# hourly_data = df.groupby("Hour").agg(
#     Temperature=("温度", "mean"),
#     Precipitation=("降水量", "mean"),
#     Dominant_Weather=("天气状态", lambda x: x.mode()[0] if not x.empty else "Unknown")
# ).reset_index()

# # Translate weather states to English
# weather_translation = {
#     "晴": "Clear",
#     "雨": "Rain",
#     "阴": "Cloudy",
#     "雾": "Fog",
#     "Unknown": "Unknown"
# }
# hourly_data["Weather_State"] = hourly_data["Dominant_Weather"].map(weather_translation)

# # Configure Nature-style plot
# plt.rcParams.update({
#     'font.size': 10,
#     'font.sans-serif': 'Arial',
#     'axes.labelsize': 11,
#     'axes.titlesize': 12,
#     'xtick.labelsize': 9,
#     'ytick.labelsize': 9,
#     'axes.linewidth': 0.8,
#     'xtick.major.width': 0.8,
#     'ytick.major.width': 0.8
# })

# # Create figure
# fig, ax1 = plt.subplots(figsize=(9, 3))

# # Temperature line plot
# ax1.plot(
#     hourly_data["Hour"], hourly_data["Temperature"],
#     color="#E69F00", linewidth=1.5,
#     label="Temperature (°C)"
# )

# # Precipitation bars
# ax2 = ax1.twinx()
# ax2.bar(
#     hourly_data["Hour"], hourly_data["Precipitation"],
#     color="#56B4E9", alpha=0.4, width=0.08,
#     label="Precipitation (mm)"
# )

# # Weather status markers
# weather_colors = {
#     "Clear": "#D55E00",
#     "Rain": "#0072B2",
#     "Cloudy": "#F0E442",
#     "Fog": "#999999",
#     "Unknown": "k"
# }
# for idx, row in hourly_data.iterrows():
#     ax1.plot(
#         row["Hour"], row["Temperature"],
#         marker='o', markersize=4,
#         color=weather_colors[row["Weather_State"]],
#         markeredgecolor="none"
#     )

# # Customize x-axis
# ax1.xaxis.set_major_locator(mdates.DayLocator(interval=5))
# ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
# plt.xticks(rotation=45, ha='right')

# # Set labels
# ax1.set_xlabel("Time slice (per hour)", labelpad=10)
# ax1.set_ylabel("Temperature (°C)", color="#E69F00")
# ax2.set_ylabel("Precipitation (mm)", color="#56B4E9")

# # Create legend
# lines = [
#     plt.Line2D([0], [0], color="#E69F00", lw=1.5, label="Temperature"),
#     plt.Rectangle((0,0),1,1, color="#56B4E9", alpha=0.6, label="Precipitation")
# ]
# weather_markers = [
#     plt.Line2D([0], [0], marker='o', color=color, label=weather,
#                markersize=6, linestyle="None")
#     for weather, color in weather_colors.items()
# ]

# ax1.legend(
#     handles=lines + weather_markers,
#     loc="upper center",
#     bbox_to_anchor=(0.5, -0.3),
#     ncol=5,
#     frameon=False
# )

# plt.tight_layout()
# plt.savefig("weather_analysis.svg", dpi=300, bbox_inches="tight")

# 天气+等待时间
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load data
df = pd.read_csv("v8-av.csv", 
                parse_dates=["到达起点时间", "接单时间"])

# Data processing
df = df[df["订单状态"] != "取消"]
df["处理时间"] = (df["到达起点时间"] - df["接单时间"]).dt.total_seconds() / 60
weather_translation = {"晴": "Clear", "雨": "Rain", "阴": "Cloudy", "雾": "Fog"}
df["天气状态"] = df["天气状态"].map(weather_translation).fillna("Unknown")

weather_palette = {
    "Clear": "#FFD700",  # 阳光金
    "Cloudy": "#C0C0C0", # 银灰
    "Rain": "#006994"    # 海洋蓝
}

# Configure Nature style
plt.rcParams.update({
    'font.size': 7,
    'font.sans-serif': 'Arial',
    'axes.labelsize': 8,
    'axes.titlesize': 9,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'axes.linewidth': 0.6,
    'xtick.major.width': 0.6,
    'ytick.major.width': 0.6
})

# Create horizontal boxplot
fig, ax = plt.subplots(figsize=(3.5, 1.5))  # 5x2 inch size

# Nature color palette (muted blue, steel blue, slate gray)
palette = ["#4575b4", "#74add1", "#636363"]

# Enhanced boxplot styling
boxprops = dict(linewidth=0.6, color='#2b8cbe', facecolor=palette[0])
whiskerprops = dict(linewidth=0.6, color='#969696', linestyle='-')
medianprops = dict(linewidth=0.8, color='#d73027')

# 在箱线图中应用新配色
sns.boxplot(
    y="天气状态",
    x="处理时间",
    data=df[df["天气状态"].isin(["Clear", "Cloudy", "Rain"])],
    order=["Clear", "Cloudy", "Rain"],
    palette=[weather_palette[w] for w in ["Clear", "Cloudy", "Rain"]],
    width=0.5,
    linewidth=0.6,
    showfliers=False,
    orient='h',
    whiskerprops=dict(
        linewidth=0.6,
        color='#333333'       # 须线颜色
    ),
    medianprops=dict(
        linewidth=0.8,
        color='#333333'       # 中位线颜色
    ),
    capprops=dict(            # 新增须线端帽样式
        linewidth=0.6,
        color='#333333'
    )
)


# Axis labels
ax.set_xlabel("Waiting Time (minutes)", labelpad=1)
ax.set_ylabel("Weather Condition", labelpad=1)

# Nature-style grid
ax.xaxis.grid(True, linestyle='--', alpha=0.3, linewidth=0.5)
# ax.spines[['top', 'right']].set_visible(False)

# Adjust tick parameters
ax.tick_params(axis='both', which='major', pad=1)

# Set axis limits
ax.set_xlim(left=0)

plt.tight_layout(pad=0.5)
plt.savefig("weather_boxplot_horizontal.svg", dpi=600, bbox_inches="tight")