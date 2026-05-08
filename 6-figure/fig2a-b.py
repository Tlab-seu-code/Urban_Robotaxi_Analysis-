# -*- coding: utf-8 -*-
"""
Created on Thu Jun  5 15:09:27 2025

@author: TLab
"""

# import pandas as pd

# # 读取数据
# df = pd.read_csv(r'..\dataV3\v5-av.csv')

# # 筛选订单来源不是充电单和调度单
# df = df[~df['订单来源'].isin(['充电单', '调度单'])]

# # 定义经纬度范围
# min_lon = 113.942617
# max_lon = 114.629031
# min_lat = 30.255898
# max_lat = 30.742468

# # 筛选起终点在范围内的数据
# geo_condition = (
#     (df['起点经度'].between(min_lon, max_lon)) &
#     (df['起点纬度'].between(min_lat, max_lat)) &
#     (df['终点经度'].between(min_lon, max_lon)) &
#     (df['终点纬度'].between(min_lat, max_lat))
# )

# df = df[geo_condition]

# # 保存结果
# df.to_csv(r'..\dataV3\v6-av.csv', index=False, encoding='utf_8_sig')

print("数据处理完成，结果已保存至v6-av.csv")
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as patheffects  # 新增路径效果模块
# Configure nature-style formatting
plt.style.use('default')
plt.rcParams.update({
    'font.sans-serif': 'Arial',
    'axes.labelsize': 10,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'axes.edgecolor': 'black',
    'axes.linewidth': 0.8,
    'grid.color': '#e0e0e0',
    'grid.linestyle': '--',
    'grid.linewidth': 0.5
})

# Load and prepare data
df = pd.read_csv(r'..\dataV3\v6-av.csv', parse_dates=['日期'])
df['Day_of_Week'] = df['日期'].dt.day_name().str[:3]
df['Day_of_Week'] = pd.Categorical(df['Day_of_Week'], 
                                  categories=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                                  ordered=True)

# Calculate metrics
weekly_stats = df.groupby('Day_of_Week', observed=True).agg(
    Total_Orders=('订单状态', 'size'),
Completed_Orders=('订单状态', lambda x: (x == '完成').sum()),
Days=('日期', lambda x: x.nunique())
)
weekly_stats['Success_Rate'] = (weekly_stats['Completed_Orders'] / 
                                weekly_stats['Total_Orders'] * 100).round(1)
weekly_stats['Success_Rate2'] = (weekly_stats['Completed_Orders'] / 
                                weekly_stats['Days']).round(1)

# Create nature-style visualization
fig, ax1 = plt.subplots(figsize=(5, 2))  # Nature-friendly dimensions

# Bar plot for order volume
bar_color = '#2C5C8A'  # Nature-style blue
bars = ax1.bar(weekly_stats.index, weekly_stats['Success_Rate2'],
                color=bar_color, width=0.7, linewidth=0.7,
                edgecolor=bar_color, alpha=0.9)

# Line plot for success rate
line_color = '#CC4C0E'  # Nature-style orange
ax2 = ax1.twinx()
line = ax2.plot(weekly_stats.index, weekly_stats['Success_Rate'],
                color=line_color, marker='o', markersize=5,
                linewidth=1.5, linestyle='-', mec='white', mew=0.8)

# Axis customization
ax1.set_ylabel('Order Volume', color=bar_color, labelpad=0)
ax1.tick_params(axis='y', colors=bar_color)
ax1.set_ylim(0, 10500)#weekly_stats['Success_Rate2'].max()*1)

ax2.set_ylabel('Success Rate (%)', color=line_color, labelpad=0)
ax2.tick_params(axis='y', colors=line_color)
ax2.set_ylim(0, 100)

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2, height*0.52,
              f'{height}', ha='center', va='bottom',
              color=bar_color, size=8, path_effects=[patheffects.withStroke(linewidth=3, foreground='white')])


for x, y in zip(weekly_stats.index, weekly_stats['Success_Rate']):
    ax2.text(x, y+3, f'{y}%', ha='center', va='bottom',
            color=line_color, size=8, path_effects=[patheffects.withStroke(linewidth=3, foreground='white')])

# Final touches
# plt.title('Weekly Order Performance', pad=15, fontsize=12)
fig.tight_layout()
plt.savefig('weekly_performance.svg', format='svg', bbox_inches='tight')
plt.show()


# import pandas as pd
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots
# from datetime import time

# # 区域类型映射
# TYPE_MAP = {
#     '居住区': 'Residential zone',
#     '商业区': 'Commercial zone',
#     '交通设施': 'Traffic facility',
#     '工业区': 'Industrial zone',
#     '文旅相关区域': 'Tourist attraction',
#     '政教服务区域': 'Infrastructure',
# }

# # 配色映射
# color_map = {
#     'Residential zone': '#5B84B1',  # 自然蓝（主色调）
#     'Commercial zone': '#F5B041',   # 琥珀色（对比色）
#     'Traffic facility': '#7C9D7F',  # 灰绿色（中性色）
#     'Industrial zone': '#A45C52',   # 陶土红（低饱和度）
#     'Tourist attraction': '#8B6FA8',# 薰衣草紫（辅助色） 
#     'Infrastructure': '#6C757D'     # 中性灰（背景色）
# }
# # 读取数据
# df = pd.read_csv('..\\dataV3\\v11-av.csv')

# # 时间字段转换
# df['呼单时间'] = pd.to_datetime(df['呼单时间'])
# df['呼单时刻'] = df['呼单时间'].dt.time

# # 时间段分类函数
# def classify_time(t):
#     if time(7, 0) <= t < time(9, 0):
#         return '早高峰'
#     elif time(9, 0) <= t < time(17, 0):
#         return '午间'
#     elif time(17, 0) <= t < time(20, 0):
#         return '晚高峰'
#     else:
#         return '夜间'

# df['时间段'] = df['呼单时刻'].apply(classify_time)

# # 映射OD类型编码
# df['source_code'] = df['起点类型'].map(TYPE_MAP)
# df['target_code'] = df['终点类型'].map(TYPE_MAP)
# df = df.dropna(subset=['source_code', 'target_code'])

# # 所有节点构造
# unique_codes = list(TYPE_MAP.values())
# source_nodes = ['S_' + c for c in unique_codes]
# target_nodes = ['T_' + c for c in unique_codes]
# all_nodes = source_nodes + target_nodes
# node_indices = {node: i for i, node in enumerate(all_nodes)}
# labels = [n[2:] for n in all_nodes]
# print(labels)
# colors = [color_map.get(label, '#BAB0AC') for label in labels]
# print(colors)
# # 构建子图
# fig = make_subplots(
#     rows=1, cols=4,
#     subplot_titles=['Morining', 'Noon', 'Evening', 'Night'],
#     specs=[[{'type': 'domain'}, {'type': 'domain'},
#            {'type': 'domain'}, {'type': 'domain'}]]
# )

# time_slots = ['早高峰', '午间', '晚高峰', '夜间']
# positions = [(1, 1), (1, 2), (1, 3), (1, 4)]


#     # 辅助函数：将 hex 转为 rgba 字符串
# def hex_to_rgba(hex_color, alpha=0.4):
#     hex_color = hex_color.lstrip('#')
#     r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
#     return f'rgba({r},{g},{b},{alpha})'

# for slot, pos in zip(time_slots, positions):
#     sub_df = df[df['时间段'] == slot].copy()
#     sub_df['source_node'] = 'S_' + sub_df['source_code']
#     sub_df['target_node'] = 'T_' + sub_df['target_code']
#     flow_counts = sub_df.groupby(['source_node', 'target_node']).size().reset_index(name='count')

#     sources = [node_indices[s] for s in flow_counts['source_node']]
#     targets = [node_indices[t] for t in flow_counts['target_node']]
#     values = flow_counts['count']


    
#     # 替代原来的 link_colors 构建逻辑
#     link_colors = [
#         hex_to_rgba(color_map.get(src.replace('S_', ''), '#BAB0AC'), alpha=0.4)
#         for src in flow_counts['source_node']
#     ]


#     sankey = go.Sankey(
#         domain=dict(row=pos[0] - 1, column=pos[1] - 1),
#         node=dict(
#             pad=20,
#             thickness=20,
#             line=dict(color="black", width=0.5),
#             label=labels,
#             color=colors,
#         ),
#         link=dict(
#             source=sources,
#             target=targets,
#             value=values,
#             color=link_colors
#         )
#     )

#     fig.add_trace(sankey, row=pos[0], col=pos[1])

# # 图形布局
# fig.update_layout(
#     height=400,
#     width=1200,
#     font_size=10,
#     # title_text="OD类型流向 · 不同时段对比",
#     title_font_size=10,
#     margin=dict(t=50, l=0, r=0, b=0),
#     paper_bgcolor='white'
# )

# # 输出并展示
# fig.write_image("time_sankey_comparison.svg", scale=3)
# fig.show()
