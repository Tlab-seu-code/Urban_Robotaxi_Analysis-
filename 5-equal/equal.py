# -*- coding: utf-8 -*-
"""
Created on Fri Jun  6 20:26:52 2025

@author: WuxiTlab
"""

import pandas as pd
import matplotlib.pyplot as plt

import pandas as pd

def filter_top_20percent(csv_path: str) -> pd.DataFrame:
    """处理时空统计数据，保留起点订单量前20%的时空单元"""
    # 读取原始数据
    df = pd.read_csv(csv_path)
    
    # 阶段1：按时空索引聚合
    grouped = df.groupby(['时间段', 'grid_x', 'grid_y'])['起点订单总数量'].agg(
        total_starts='sum',
        record_count='count'
    ).reset_index()
    
    # 阶段2：筛选前20%的时空单元
    # 按订单总量降序排序
    sorted_groups = grouped.sort_values('total_starts', ascending=False)
    
    # 计算要保留的组数量（向上取整）
    keep_count = int(len(sorted_groups) * 0.005) + 1
    
    # 获取关键时空索引
    key_groups = sorted_groups[['时间段', 'grid_x', 'grid_y']].head(keep_count)
    
    # 阶段3：过滤原始数据
    filtered_df = pd.merge(
        df,
        key_groups,
        on=['时间段', 'grid_x', 'grid_y'],
        how='inner'
    )
    
    return filtered_df

# 使用示例
# filtered_data = filter_top_20percent("spatio-temporal-stats.csv")
# print(f"过滤后数据量: {len(filtered_data)} 条")
# filtered_data.to_csv(
#     'patio-temporal-stat2.csv', 
#     index=False,
#     encoding='utf-8-sig'
# )


# def plot_correlation(target_date: str):
#     # 读取时空统计数据（保持原始中文列名）
#     spatio_df = pd.read_csv("patio-temporal-stat2.csv", parse_dates=['日期'])
    
#     # 过滤目标日期并删除终点订单为0的记录
#     filtered = spatio_df[
#         (spatio_df['日期'] == target_date) &
#         (spatio_df['终点订单总数量'] > 0)
#     ].copy()
    
#     # 读取小时级数据（保持原始英文列名）
#     hourly_df = pd.read_csv(".\\grid_v4\\hourly_20240708.csv")
    
#     # 合并数据集（精确匹配时空坐标和时间段）
#     merged = pd.merge(
#         filtered,
#         hourly_df,
#         left_on=['时间段', 'grid_x', 'grid_y'],  # 中文列名
#         right_on=['hour', 'x', 'y'],           # 英文列名
#         how='inner'
#     )
    
#     merged[['起点订单总数量', 'non_run_ratio']].to_csv(
#         f'xy_data_{target_date}.csv', 
#         index=False,
#         encoding='utf-8-sig'
#     )
    
#     # 创建画布
#     plt.figure(figsize=(12, 8), dpi=120)
    
#     # 绘制散点图（使用原始字段名）
#     plt.scatter(
#         x=merged['起点订单总数量'],  # 中文列名
#         y=merged['non_run_ratio'],  # 英文列名
#         alpha=0.6,
#         edgecolors='w',
#         s=80
#     )
    
#     # 添加英文标注
#     plt.title(f"Demand-Supply Relationship ({target_date})\n"
#              f"Correlation: {merged['起点订单总数量'].corr(merged['non_run_ratio']):.2f} | "
#              f"Points: {len(merged)}")
#     plt.xlabel('Pickup Orders (Demand)')
#     plt.ylabel('Vehicle Shortage Ratio')
    
#     # 辅助元素
#     plt.grid(True, alpha=0.3, linestyle='--')
    
#     # 保存输出
#     plt.tight_layout()
#     plt.savefig(f'scatter_{target_date}.png')
#     plt.show()

def plot_correlation(target_date: str):
    # 读取时空统计数据（保持原始中文列名）
    spatio_df = pd.read_csv("patio-temporal-stat2.csv", parse_dates=['日期'])
    
    # 过滤目标日期并删除终点订单为0的记录
    filtered = spatio_df[
        (spatio_df['日期'] == target_date) &
        (spatio_df['终点订单总数量'] > 0)
    ].copy()
    
    # 读取小时级数据（保持原始英文列名）
    hourly_df = pd.read_csv(".\\grid_v4\\hourly_20240708.csv")
    
    # 合并数据集（精确匹配时空坐标和时间段）
    merged = pd.merge(
        filtered,
        hourly_df,
        left_on=['时间段', 'grid_x', 'grid_y'],  # 中文列名
        right_on=['hour', 'x', 'y'],           # 英文列名
        how='inner'
    )
    
    merged[['起点订单总数量', 'non_run_ratio']].to_csv(
        f'xy_data_{target_date}.csv', 
        index=False,
        encoding='utf-8-sig'
    )
    
    # 创建画布
    plt.figure(figsize=(12, 8), dpi=120)
    
    # 绘制散点图（使用原始字段名）
    plt.scatter(
        x=merged['起点订单总数量'],  # 中文列名
        y=merged['non_run_ratio'],  # 英文列名
        alpha=0.6,
        edgecolors='w',
        s=80
    )
    
    # 添加英文标注
    plt.title(f"Demand-Supply Relationship ({target_date})\n"
             f"Correlation: {merged['起点订单总数量'].corr(merged['non_run_ratio']):.2f} | "
             f"Points: {len(merged)}")
    plt.xlabel('Pickup Orders (Demand)')
    plt.ylabel('Vehicle Shortage Ratio')
    
    # 辅助元素
    plt.grid(True, alpha=0.3, linestyle='--')
    
    # 保存输出
    plt.tight_layout()
    plt.savefig(f'scatter_{target_date}.png')
    plt.show()
    
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def plot_analysis(target_date: str):
    # 数据读取与预处理
    spatio_df = pd.read_csv('patio-temporal-stat2.csv', parse_dates=['日期'])
    filtered = spatio_df[(spatio_df['日期'] == target_date) & 
                        (spatio_df['终点订单总数量'] > 0)]
    
    hourly_df = pd.read_csv("hourly_20240708.csv")
    
    merged = pd.merge(
        filtered,
        hourly_df,
        left_on=['时间段', 'grid_x', 'grid_y'],
        right_on=['hour', 'x', 'y'],
        how='inner'
    )
    
    # 保存原始数据
    merged[['起点订单总数量', 'non_run_ratio']].to_csv(
        f'xy_data_{target_date}.csv', 
        index=False,
        encoding='utf-8-sig'
    )
    
    # 离散化处理（按车辆数分箱）
    df = merged.copy()
    df['demand_bin'] = pd.cut(
        df['起点订单总数量'],
        bins=np.arange(
            start=0, 
            stop=df['起点订单总数量'].max(), 
            step=2
        ),
        right=False
    ).astype(str)
    
    # 创建画布
    plt.figure(figsize=(20, 20))
    
    # 箱线图绘制
    plt.subplot(1, 2, 1)
    df.boxplot(
        column='non_run_ratio',
        by='demand_bin',
        grid=False,
        vert=False,
        flierprops={'marker': 'o', 'markersize': 3}
    )
    plt.title(f"Distribution by Demand Level\n({target_date})")
    plt.xlabel('Vehicle Shortage Ratio')
    plt.ylabel('Demand Bin (Pickup Orders)')
    plt.suptitle('')  # 移除自动生成的标题
    
    # 添加辅助分析
    plt.subplot(1, 2, 2)
    bin_counts = df.groupby('demand_bin').size()
    plt.barh(
        y=bin_counts.index.astype(str), 
        width=bin_counts.values,
        alpha=0.6
    )
    plt.title('Sample Distribution')
    plt.xlabel('Data Points Count')
    plt.tight_layout()
    
    plt.savefig(f'boxplot_analysis_{target_date}.png', dpi=120)
    plt.show()

# 执行示例
# plot_analysis('2024-11-21')

# 使用示例（假设目标日期为2024-07-08）
# plot_correlation('2024-11-21')

import pandas as pd
import matplotlib.pyplot as plt

def plot_vertical_boxplots(target_date: str):
    # 直接读取已保存数据
    df = pd.read_csv(f'combined_analysis.csv')
    
    # 创建长画布（宽度根据分箱数量自动调整）
    bin_count = df['起点订单总数量'].nunique()
    plt.figure(figsize=(max(20, bin_count*0.5), 8))
    
    # 生成整数分箱标签
    bins = sorted(df['起点订单总数量'].unique())
    df['demand_bin'] = pd.Categorical(
        df['起点订单总数量'], 
        categories=bins,
        ordered=True
    )
    
    # 绘制垂直箱线图
    df.boxplot(
        column='non_run_ratio',
        by='demand_bin',
        vert=True,  # 垂直显示
        grid=False,
        patch_artist=True,
        boxprops=dict(facecolor='lightblue'),
        flierprops=dict(marker='o', markersize=3)
    )
    
    # 优化显示
    plt.title(f"Vehicle Shortage Ratio Distribution (1-unit bins)\nDate: {target_date}")
    plt.xlabel('Pickup Orders (Discrete Values)')
    plt.ylabel('Vehicle Shortage Ratio')
    plt.xticks(rotation=90, fontsize=8)
    plt.gca().get_figure().suptitle('')  # 移除默认副标题
    plt.grid(axis='y', alpha=0.3)
    
    # 智能缩放
    plt.xlim(-0.5, len(bins)-0.5)  # 精确控制x轴范围
    if len(bins) > 50:
        plt.xticks(ticks=range(0, len(bins), 5))  # 间隔显示标签
    
    # 保存输出
    plt.tight_layout()
    plt.savefig(f'vertical_boxes_{target_date}.png', dpi=150, bbox_inches='tight')
    plt.show()

# 执行示例
plot_vertical_boxplots('2024-11-21')



import pandas as pd
import os
from glob import glob

def process_all_dates():
    """聚合多日期分析结果到单个文件"""
    # 路径配置
    spatio_path = "spatio-temporal-stats.csv"
    grid_dir = ".\\grid_v4"
    output_path = "combined_analysis.csv"  # 统一输出文件
    
    # 读取时空数据并排序
    spatio_df = pd.read_csv(spatio_path, parse_dates=['日期'])
    sorted_dates = spatio_df['日期'].sort_values().unique()[2:23]
    
    # 获取小时文件列表
    hourly_files = sorted(glob(os.path.join(grid_dir, "hourly_*.csv")))
    
    # 数据一致性校验
    if len(sorted_dates) != len(hourly_files):
        raise ValueError(f"日期数量({len(sorted_dates)})与文件数量({len(hourly_files)})不匹配")

    # 初始化结果容器
    full_results = []

    # 循环处理每个日期
    for date_obj, hourly_path in zip(sorted_dates, hourly_files):
        # 时空数据过滤
        daily_data = spatio_df[
            (spatio_df['日期'] == date_obj) & 
            (spatio_df['起点订单总数量'] >= 10)& 
            (spatio_df['终点订单总数量'] > 0)
        ].copy()
        
        # 小时数据读取
        hourly_data = pd.read_csv(hourly_path)
        
        # 数据关联
        merged = pd.merge(
            daily_data,
            hourly_data,
            left_on=['时间段', 'grid_x', 'grid_y'],
            right_on=['hour', 'x', 'y'],
            how='inner'
        )
        
        # 添加日期标识列
        merged['分析日期'] = pd.Timestamp(date_obj).strftime("%Y-%m-%d")
        
        # 抽取关键指标
        full_results.append(
            merged[['分析日期', '时间段', 'grid_x', 'grid_y',
                   '起点订单总数量', 'non_run_ratio']]
        )

    # 整合结果并保存
    if full_results:
        full_results = pd.concat(full_results, ignore_index=True)
        full_results.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"已整合{len(full_results)}天数据到 {output_path}")
    else:
        print("警告：没有产生任何合并数据")
        
    # 创建画布
    plt.figure(figsize=(12, 8), dpi=120)
   
    # 绘制散点图（使用原始字段名）
    plt.scatter(
        x=full_results['起点订单总数量'],  # 中文列名
        y=full_results['non_run_ratio'],  # 英文列名
        alpha=0.6,
        edgecolors='w',
        s=80
    )
   
    # 添加英文标注
    plt.title(f"Demand-Supply Relationship)\n"
             f"Correlation: {full_results['起点订单总数量'].corr(full_results['non_run_ratio']):.2f} | "
             f"Points: {len(full_results)}")
    plt.xlabel('Pickup Orders (Demand)')
    plt.ylabel('Vehicle Shortage Ratio')
   
    # 辅助元素
    plt.grid(True, alpha=0.3, linestyle='--')
   
    # 保存输出
    plt.tight_layout()
    plt.savefig(f'scatter.png')
    plt.show()   

# if __name__ == "__main__":
#     process_all_dates()

# 最新双密度计算

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

def nature_style_plot():
    """Set matplotlib parameters for Nature style"""
    plt.rcParams.update({
        'font.size': 8,
        'axes.titlesize': 8,
        'axes.labelsize': 8,
        'xtick.labelsize': 7,
        'ytick.labelsize': 7,
        'legend.fontsize': 7,
        'font.sans-serif': 'Arial',
        'pdf.fonttype': 42,
        'axes.linewidth': 0.5,
        'lines.linewidth': 0.75,
        'xtick.major.width': 0.5,
        'ytick.major.width': 0.5,
        'xtick.major.size': 2,
        'ytick.major.size': 2,
        'axes.facecolor': 'white',
        'savefig.dpi': 300
    })

def process_and_plot(file1_path, file2_path):
    
    """处理两个文件并绘制散点图"""
    # 读取数据
    df1 = pd.read_csv(file1_path, parse_dates=['日期'])
    df2 = pd.read_csv(file2_path, parse_dates=['日期'])
    
    # 按日期排序
    df1 = df1.sort_values('日期')
    df2 = df2.sort_values('日期')
    
    # 获取日期列表
    dates1 = df1['日期'].unique()
    dates2 = df2['日期'].unique()
    
    # 数据校验
    if len(dates1) != len(dates2):
        print(f"警告：文件日期数量不同（{len(dates1)} vs {len(dates2)}），将处理最小数量")
    
    all_pairs = []
    
    # 遍历每一天
    for date1, date2 in zip(dates1, dates2):
        # 过滤当日数据
        daily1 = df1[df1['日期'] == date1]
        daily2 = df2[df2['日期'] == date2]
        
        # 合并数据
        merged = pd.merge(
            daily1,
            daily2,
            on=['时间段', 'grid_x', 'grid_y'],
            suffixes=('_x', '_y'),
            how='inner'
        )
        
        # 收集有效数据
        if not merged.empty:
            all_pairs.append(merged[['起点订单总数量_x', '起点订单总数量_y']])
    
    # 合并所有数据
    if not all_pairs:
        print("错误：没有匹配到有效数据")
        return
    
    combined = pd.concat(all_pairs)
        
    
    # combined = combined[combined['起点订单总数量_x'] >= 10].copy()

    
    # Initialize Nature style
    nature_style_plot()
    sns.set_style("white")
    
    # (Data processing部分保持相同，与中文版一致) 
    # ... [省略数据处理代码，与先前实现相同] ...

    # Create figure with proper dimensions
    fig, ax = plt.subplots(figsize=(3.5, 3.5))  # Nature单栏常用宽度
    
    # Scatter plot with refined parameters
    scatter = ax.scatter(
        combined['起点订单总数量_x'],
        combined['起点订单总数量_y'],
        c='#2c7bb6',  # Nature风格蓝色
        s=12,
        edgecolors='w',
        linewidth=0.3,
        alpha=0.8,
        # rasterized=True  # 优化PDF文件大小
    )
    
    # 添加统计标注
    slope, intercept, r_value, p_value, _ = stats.linregress(
        combined['起点订单总数量_x'],
        combined['起点订单总数量_y']
    )
    
    
    
    # --- 新增包络线计算代码 ---
    # 按x分组取最大y值
    envelope = combined.groupby('起点订单总数量_x')['起点订单总数量_y'].max().reset_index()
    
    # 二次函数拟合
    coeffs = np.polyfit(envelope['起点订单总数量_x'], envelope['起点订单总数量_y'], deg=4)
    poly_func = np.poly1d(coeffs)
    
    # 生成平滑曲线数据
    x_fit = np.linspace(envelope['起点订单总数量_x'].min(), 
                       envelope['起点订单总数量_x'].max(), 
                       100)
    y_fit = poly_func(x_fit)
    
    
    
    # 添加包络线到图表
    ax.plot(x_fit, y_fit, 
           color='#d7191c',  # Nature风格红色
           # linestyle='--',
           linewidth=1.2)
            # label=f'Envelope: y={coeffs[0]:.2f}x²{coeffs[1]:+.2f}x{coeffs[2]:+.1f}')
    
    # 可选：标注拟合公式
    # ax.text(0.05, 0.95, 
    #        f'y = {coeffs[0]:.2f}x² + {coeffs[1]:.2f}x + {coeffs[2]:.2f}',
    #        transform=ax.transAxes,
    #        fontsize=6,
    #    verticalalignment='top')
    
    # 设置坐标轴
    ax.set_xlabel('Origin orders (CAV)', labelpad=2)
    ax.set_ylabel('Origin orders (HDV)', labelpad=2)
    ax.set_title('Cross-validation of Order Counts', pad=8)
    
    # 设置刻度范围
    min_val = min(ax.get_xlim()[0], ax.get_ylim()[0])
    max_val = max(ax.get_xlim()[1], ax.get_ylim()[1])
    ax.set_xlim(-1, 15)
    ax.set_ylim(-4, max_val)

    # 添加对角线参考线
    # ax.plot([min_val, max_val], [min_val, max_val], 
    #        ls='--', c='#7f7f7f', lw=0.8, alpha=0.5)
    
    # 优化布局
    ax.legend(frameon=False, loc='upper left', bbox_to_anchor=(0.18, 0.98))
    # sns.despine(offset=2, trim=True)
    
    # 保存图片（符合期刊要求）
    plt.savefig('scatter_nature_style.pdf', bbox_inches='tight')
    plt.show()


# 使用示例
process_and_plot('spatio-temporal-stats-cancel.csv', 'spatio-temporal-stats-hdv.csv')


