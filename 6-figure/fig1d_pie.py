import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. 读取数据
csv_path = 'shap_long.csv'
df = pd.read_csv(csv_path)

# 过滤掉 'SuccessRate30min' 特征 - 使用布尔索引筛选[6,7](@ref)
df_filtered = df[df['name'] != 'SuccessRate30min']

# 2. 计算百分比并排序 (基于过滤后的数据)
feature_importance = df_filtered.groupby('name')['importance'].first()
total_importance = feature_importance.sum()
feature_percentage = (feature_importance / total_importance) * 100
feature_percentage = feature_percentage.sort_values(ascending=False)
labels = feature_percentage.index.tolist()
sizes = feature_percentage.values.tolist()

# 3. 按"实际百分比数值"映射颜色（蓝=高，红=低）
colors = [(0.12, 0.47, 0.71),   # 蓝
          (0.55, 0.14, 0.78),   # 紫
          (0.89, 0.10, 0.11)]   # 红 
cmap = plt.cm.colors.LinearSegmentedColormap.from_list('blue_purple_red', colors, N=256)

# 用百分比本身做归一化
norm = plt.Normalize(vmin=min(sizes), vmax=max(sizes))
color_list = [cmap(norm(value)) for value in sizes]  # 直接使用百分比值映射颜色

# 4. 创建图形和轴
fig, ax = plt.subplots(figsize=(12, 9))

# 5. 绘制饼图，设置白色边框
wedges, texts = ax.pie(sizes, colors=color_list, startangle=90, counterclock=False,
                       wedgeprops={'edgecolor': 'white', 'linewidth': 1.5})  # 白色边框

# 6. 设置引导线属性
label_props = {'arrowstyle': '-', 'color': 'gray', 'linewidth': 0.8}
bbox_props = {'boxstyle': "round,pad=0.3", 'facecolor': 'none', 'alpha': 0.9,
              'edgecolor': 'none', 'linewidth': 0.5}

# 7. 遍历每个扇区，添加外部百分比标签和引导线（只显示比例，不显示变量名）
for i, (wedge, size) in enumerate(zip(wedges, sizes)):
    # 计算扇区中心点的角度 (弧度制)
    angle_rad = np.radians((wedge.theta2 + wedge.theta1) / 2)

    # 计算饼图边缘点的坐标 (引导线起点)
    x_in = 1 * np.cos(angle_rad)
    y_in = 1 * np.sin(angle_rad)

    # 计算标签位置的坐标 (引导线终点)
    x_out = 1.2 * np.cos(angle_rad)
    y_out = 1.2 * np.sin(angle_rad)

    # 根据扇区位置决定文本对齐方式
    horizontal_alignment = 'left' if x_out >= 0 else 'right'

    # 绘制引导线
    ax.plot([x_in, x_out], [y_in, y_out], color='black', linewidth=0.8, alpha=0.7)

    # 添加文本标签（只显示百分比，不显示变量名）
    ax.text(x_out, y_out, f'{size:.1f}%',  # 只显示百分比
            horizontalalignment=horizontal_alignment, verticalalignment='center',
            bbox=bbox_props, fontsize=30, fontfamily='Arial')

# 8. 确保饼图是圆形并设置标题
ax.axis('equal')
plt.title('Feature Importance Distribution (Excluding SuccessRate30min)', pad=20, fontsize=24, fontweight='bold', fontfamily='Arial')

# 9. 添加图例（可选，如果仍需显示变量名信息）
# ax.legend(wedges, labels, title="Features", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

# 10. 调整布局并显示
plt.tight_layout()
plt.savefig('pie_chart_percentage_only.pdf', dpi=300, bbox_inches='tight', facecolor='white')
plt.show()