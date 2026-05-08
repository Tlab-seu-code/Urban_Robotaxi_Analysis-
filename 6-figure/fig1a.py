# -*- coding: utf-8 -*-
"""
Created on Tue Jun  3 14:23:54 2025

@author: TLab
"""

import json
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon
import pandas as pd
from pypinyin import pinyin, Style  # 用于中文转拼音
from matplotlib.colors import LinearSegmentedColormap

# 配置中文字体为黑体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 或者 'SimHei' 根据安装的字体来选择
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

class DistrictBoundary:
    def __init__(self, json_file):
        # 读取json文件中的边界信息
        self.district_data = self.load_boundary_data(json_file)
        self.polygons = self.create_polygons()
        # 创建中文到拼音的映射
        self.name_to_pinyin = self.create_pinyin_mapping()
        

    def create_pinyin_mapping(self):
        """创建中文名称到拼音的映射"""
        pinyin_mapping = {}
        for district in self.district_data:
            name = district['name']
            name = name[:-1] if name.endswith('区') else name
            # 将中文转换为拼音（不带声调）
            py = ''.join([item[0] for item in pinyin(name, style=Style.NORMAL)])
            pinyin_mapping[name] = py
        return pinyin_mapping

    def load_boundary_data(self, json_file):
        """读取json文件，返回包含区域边界的列表"""
        try:
            with open(json_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
                return data
        except FileNotFoundError:
            print(f"文件 {json_file} 未找到。")
            return []
        except json.JSONDecodeError:
            print(f"文件 {json_file} 格式错误。")
            return []

    def plot_district(self, district_name):
        """绘制指定区域的边界"""
        if district_name not in self.polygons:
            print(f"未找到名为 '{district_name}' 的区域数据。")
            return

        # 绘制每个多边形
        plt.figure(figsize=(10, 12))  # 修改图片大小为10x12英寸
        for polygon in self.polygons[district_name]:
            x, y = polygon.exterior.xy
            plt.plot(x, y, color='black')  # 边界使用黑色
            plt.fill(x, y, color='white')  # 填充白色
            
        # 添加拼音标签
        centroid = self.get_district_centroid(district_name)
        if centroid:
            py_name = self.name_to_pinyin.get(district_name, district_name)
            plt.text(centroid.x, centroid.y, py_name, 
                     fontsize=12, ha='center', va='center',
                     bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

        plt.title(f"{district_name} 边界")
        plt.xlabel("经度")
        plt.ylabel("纬度")
        plt.axis('equal')  # 保持经纬度比例一致
        plt.show()

    def get_distroid_centroid(self, district_name):
        """获取区域的中心点"""
        if district_name in self.polygons and self.polygons[district_name]:
            # 返回第一个多边形的中心点
            return self.polygons[district_name][0].centroid
        return None
    
    def get_district_centroid(self, district_name):
        """获取区域的中心点"""
        if district_name in self.polygons and self.polygons[district_name]:
            # 返回第一个多边形的中心点
            return self.polygons[district_name][0].centroid
        return None

    def create_polygons(self):
        """根据边界信息创建多边形对象"""
        polygons = {}
        for district in self.district_data:
            name = district['name']
            polyline_str = district['polyline']
            polygons[name] = []
            # 解析polyline字符串，得到经纬度坐标
            polygons_list = self.parse_polyline(polyline_str)
            for polygon in polygons_list:
                polygons[name].append(Polygon(polygon))
        return polygons

    def parse_polyline(self, polyline_str):
        """解析MULTIPOLYGON或POLYGON格式的字符串，返回多边形列表"""
        if polyline_str.startswith("MULTIPOLYGON"):
            # MULTIPOLYGON处理: 去掉 'MULTIPOLYGON' 和多余的括号
            polyline_str = polyline_str.replace('MULTIPOLYGON (((', '').replace(')))', '')
            # 分割为各个POLYGON字符串
            raw_polygons = polyline_str.split(")), ((")
            polygons = []
            for raw_polygon in raw_polygons:
                # 对每个POLYGON进一步展平
                sub_polygons = raw_polygon.split("), (")
                polygons.extend(self.parse_single_polygon(sub) for sub in sub_polygons)
            return polygons
        elif polyline_str.startswith("POLYGON"):
            # POLYGON处理: 去掉 'POLYGON' 和多余的括号
            polyline_str = polyline_str.replace('POLYGON ((', '').replace('))', '')
            # 处理POLYGON中的多个内嵌多边形
            sub_polygons = polyline_str.split("), (")
            return [self.parse_single_polygon(sub) for sub in sub_polygons]
        else:
            raise ValueError(f"未知的边界格式: {polyline_str}")

    def parse_single_polygon(self, polygon_str):
        """解析单个POLYGON或MULTIPOLYGON子多边形的坐标"""
        # 移除多余空格，并将字符串解析为点列表
        points = [
            tuple(map(float, point.strip().split())) 
            for point in polygon_str.split(',')
        ]
        return points

    def plot_all_districts(self):
        """绘制所有区域的边界，使用黑色边界和白色填充"""
        plt.figure(figsize=(10, 12))  # 修改图片大小为10x12英寸

        # 绘制每个区域的多边形
        for district_name, polygons in self.polygons.items():
            for polygon in polygons:
                x, y = polygon.exterior.xy
                plt.fill(x, y, color='white')  # 填充白色
                plt.plot(x, y, color='black')  # 边界使用黑色
                
            # 添加拼音标签
            centroid = self.get_distroid_centroid(district_name)
            if centroid:
                py_name = self.name_to_pinyin.get(district_name, district_name)
                plt.text(centroid.x, centroid.y, py_name, 
                         fontsize=10, ha='center', va='center',
                         bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

        # 设置图形的标题和标签
        plt.title("", fontsize=15)
        plt.xlabel("Lon", fontsize=12)
        plt.ylabel("Lat", fontsize=12)
        plt.axis('equal')  
        plt.tight_layout()
        plt.show()

    def find_district(self, lon, lat):
        """根据经纬度查找点所在的区域"""
        point = Point(lon, lat)
        
        for district_name, polygons in self.polygons.items():
            for polygon in polygons:
                if polygon.contains(point):
                    return district_name
        
        return "都不是"

# 定义函数：根据CSV文件中的起点和终点经纬度，添加所属区域列
def add_district_columns(input_csv, output_csv, district_boundary):
    # 读取原始CSV文件
    df = pd.read_csv(input_csv)

    # 初始化新的列
    df['start_zone'] = None
    df['end_zone'] = None

    # 遍历每一行，计算起点和终点所属的区
    for index, row in df.iterrows():
        # 获取起点经纬度
        start_lon = row['start_lon']
        start_lat = row['start_lat']
        # 获取终点经纬度
        end_lon = row['end_lon']
        end_lat = row['end_lat']

        # 使用 find_district 方法查找所属区
        start_district = district_boundary.find_district(start_lon, start_lat)
        end_district = district_boundary.find_district(end_lon, end_lat)

        # 更新数据框中的新列
        df.at[index, 'start_zone'] = start_district
        df.at[index, 'end_zone'] = end_district

    # 将更新后的数据保存为新的CSV文件
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"结果已保存到 {output_csv}")

# 使用示例
boundary = DistrictBoundary("district_boundaries.json")  # 初始化区域边界类
input_csv = "..\\dataV3\\v1-hdv.csv"
output_csv = "..\\dataV3\\v2-hdv.csv"

# # 调用函数，处理数据
# add_district_columns(input_csv, output_csv, boundary)

# 绘制所有区域
# boundary.plot_all_districts()

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.cm import ScalarMappable
import matplotlib.colors as mcolors
from adjustText import adjust_text  # 用于避免标签重叠

def remove_district_suffix(name):
    """移除区域名称中的'区'字"""
    if name.endswith('区'):
        return name[:-1]
    return name

def plot_heatmap_by_district(csv_file, boundary):
    """
    Plot heatmap of order counts by starting district
    
    Parameters:
    csv_file -- path to the CSV file containing order data
    boundary -- DistrictBoundary object containing district boundary information
    """
    # 1. Read CSV file
    df = pd.read_csv(csv_file)
    
    # 2. Count orders per district
    district_counts = df['start_zone'].value_counts().to_dict()
    
    # 3. Get centroids and pinyin names for all districts
    centroids = {}
    pinyin_names = {}
    texts = []  # 用于存储文本对象，以便调整位置
    
    for district_name in boundary.polygons.keys():
        centroid = boundary.get_distroid_centroid(district_name)
        if centroid:
            centroids[district_name] = (centroid.x, centroid.y)
            # Remove '区' suffix and get pinyin
            short_name = remove_district_suffix(district_name)
            pinyin_names[district_name] = boundary.name_to_pinyin.get(short_name, short_name)
    
    # 4. Prepare data for plotting
    max_count = max(district_counts.values()) if district_counts else 1
    min_count = min(district_counts.values()) if district_counts else 0
    
    # 5. Create custom color map (light to dark red)
    colors = ["#FFF5F0", "#FEE0D2", "#FCBBA1", "#FC9272", "#FB6A4A", "#EF3B2C", "#CB181D", "#A50F15", "#67000D"]
    cmap = LinearSegmentedColormap.from_list("custom_reds", colors)
    norm = mcolors.Normalize(vmin=min_count, vmax=max_count)
    
    # 6. Plot the map
    plt.figure(figsize=(12, 9))  # 增大图像尺寸
    
    # Plot district polygons with color based on order count
    for district_name, polygons in boundary.polygons.items():
        # Get order count for this district, default to 0 if not found
        count = district_counts.get(district_name, 0)
        color = cmap(norm(count))
        
        for polygon in polygons:
            x, y = polygon.exterior.xy
            plt.fill(x, y, color=color)  # Fill with color based on order count
            plt.plot(x, y, color='black', linewidth=0.8)  # District boundaries in black
    
    # 7. Add district labels with adjusted positions
    for district_name, (x, y) in centroids.items():
        py_name = pinyin_names[district_name]
        
        # 为市中心区域设置不同的位置偏移
        offset_x, offset_y = 0, 0
        
        # 市中心区域列表
        downtown_districts = ["江汉区", "江岸区", "硚口区", "武昌区", "汉阳区"]
        short_name = remove_district_suffix(district_name)
        
        if district_name == "江汉区":
            offset_x, offset_y = 0.01, -0.01
        elif district_name == "江岸区":
            offset_x, offset_y = 0.02, 0.01
        elif district_name == "硚口区":
            offset_x, offset_y = -0.02, 0.01
        elif district_name == "武昌区":
            offset_x, offset_y = 0.01, -0.02
        elif district_name == "汉阳区":
            offset_x, offset_y = -0.02, -0.01
        
        # 创建文本对象并添加到列表
        text = plt.text(x + offset_x, y + offset_y, py_name, 
                        fontsize=14, ha='center', va='center',  # 增大字号
                        bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=2))
        texts.append(text)
    
    # 使用adjustText自动调整标签位置避免重叠
    adjust_text(texts, 
                arrowprops=dict(arrowstyle='->', color='gray', lw=0.5),
                expand_points=(1.2, 1.2), 
                expand_text=(1.2, 1.2),
                force_points=0.2,
                force_text=0.2)
    
    # 8. Add color bar with larger font
    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, fraction=0.03, pad=0.04)
    cbar.set_label('Order Count', fontsize=24)  # 增大字号
    cbar.ax.tick_params(labelsize=22)  # 增大刻度字号
    
    # 9. Add title and labels with larger fonts
    # plt.title("Order Count Heatmap by Starting District", fontsize=18)  # 增大标题字号
    plt.xlabel("Longitude", fontsize=24)
    plt.ylabel("Latitude", fontsize=24)
    
    # 10. Set tick font size
    plt.xticks(fontsize=22)
    plt.yticks(fontsize=22)
    
    plt.axis('equal')
    plt.tight_layout()
    plt.show()


boundary = DistrictBoundary("district_boundaries.json")
    
# csv_file = "..\\dataV3\\v4-av.csv"  # 替换为实际文件路径
csv_file = "..\\dataV3\\v2-hdv.csv"  # 替换为实际文件路径
# plot_heatmap_by_district(csv_file, boundary)


import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.cm as cm

def plot_trip_scatter(csv_file, boundary, sample_fraction=0.1):
    """
    Plot scatter points for trip origins and destinations
    
    Parameters:
    csv_file -- path to the CSV file containing trip data
    boundary -- DistrictBoundary object containing district boundary information
    sample_fraction -- fraction of data to sample (0-1) for visualization
    """
    # 1. Read CSV file
    print(f"Reading data from {csv_file}...")
    df = pd.read_csv(csv_file)
    
    # 2. Sample a fraction of the data to reduce density
    if sample_fraction < 1.0:
        df = df.sample(frac=sample_fraction, random_state=42)
        print(f"Sampled {len(df)} trips ({sample_fraction*100:.1f}% of total)")
    
    # 3. Prepare data
    origins = df[['起点经度', '起点纬度']].values
    destinations = df[['终点经度', '终点纬度']].values
    
    # 4. Create figure and axis
    plt.figure(figsize=(9, 9))
    ax = plt.gca()
    
    # 5. Plot district boundaries
    print("Plotting district boundaries...")
    for district_name, polygons in boundary.polygons.items():
        for polygon in polygons:
            x, y = polygon.exterior.xy
            ax.plot(x, y, color='black', linewidth=0.8)  # District boundaries


    
    # 6. Plot origin points (blue)
    print("Plotting origin points...")
    ax.scatter(
        origins[:, 0], origins[:, 1], 
        s=12,  # Very small point size
        alpha=0.2,  # Low transparency to show density
        c='blue',
        label='Origin Points'
    )
    
    # 7. Plot destination points (red)
    print("Plotting destination points...")
    ax.scatter(
        destinations[:, 0], destinations[:, 1], 
        s=12,  # Very small point size
        alpha=0.02,  # Low transparency to show density
        c='red',
        label='Destination Points'
    )
    
    # 8. Add legend with larger font
    plt.legend(loc='upper right', fontsize=22, markerscale=5)
    
    # 9. Add title and labels
    # plt.title("Trip Origins and Destinations", fontsize=18)
    plt.xlabel("Longitude", fontsize=24)
    plt.ylabel("Latitude", fontsize=24)
    
    # 10. Set tick font size
    plt.xticks(fontsize=22)
    plt.yticks(fontsize=22)
    
    # 11. Add grid for better reference
    plt.grid(True, linestyle='--', alpha=0.3)
    
    plt.axis('equal')
    plt.tight_layout()
    
    # 12. Save and show
    plt.savefig('trip_scatter_plot.png', dpi=300, bbox_inches='tight')
    print("Plot saved as 'trip_scatter_plot.png'")
    plt.show()

# # 使用示例
# if __name__ == "__main__":
#     # Initialize district boundaries
#     boundary = DistrictBoundary("district_boundaries.json")
    
#     # Plot scatter
#     csv_file = "..\\dataV3\\v4-av.csv"  # 替换为实际文件路径
#     plot_trip_scatter(csv_file, boundary, sample_fraction=0.1)  # 使用10%的数据样本

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
import matplotlib.cm as cm

def plot_trip_lines(csv_file, boundary, sample_fraction=0.01, line_alpha=0.01):
    """
    Plot lines connecting trip origins and destinations
    
    Parameters:
    csv_file -- path to the CSV file containing trip data
    boundary -- DistrictBoundary object containing district boundary information
    sample_fraction -- fraction of data to sample (0-1) for visualization
    line_alpha -- transparency of lines (0-1)
    """
    # 1. Read CSV file
    print(f"Reading data from {csv_file}...")
    df = pd.read_csv(csv_file)
    
    # 2. Sample a fraction of the data to reduce density
    if sample_fraction < 1.0:
        df = df.sample(frac=sample_fraction, random_state=42)
        print(f"Sampled {len(df)} trips ({sample_fraction*100:.1f}% of total)")
    
    df = df[(df['start_zone'] != "都不是") & (df['end_zone'] != "都不是")]
    
    # 3. Prepare data
    origins = df[["start_lon","start_lat"]].values
    destinations = df[['end_lon', "end_lat"]].values
    
    # 4. Create figure and axis
    plt.figure(figsize=(9, 9))
    ax = plt.gca()
    
    # 5. Plot district boundaries
    print("Plotting district boundaries...")
    for district_name, polygons in boundary.polygons.items():
        for polygon in polygons:
            x, y = polygon.exterior.xy
            ax.plot(x, y, color='black', linewidth=0.8)  # District boundaries
    
    # 6. Create line segments
    print("Creating line segments...")
    segments = np.array([(origins[i], destinations[i]) for i in range(len(df))])
    
    # 7. Create LineCollection for efficient rendering
    print("Rendering lines...")
    # lc = LineCollection(
    #     segments, 
    #     linewidths=3,  # Very thin lines
    #     alpha=line_alpha,  # Low transparency
    #     colors='purple',  # Purple color for lines
    #     zorder=1  # Ensure lines are below other elements
    # )
    # ax.add_collection(lc)
    
    # 8. Add origin and destination markers for reference
    ax.scatter(
        origins[:, 0], origins[:, 1], 
        s=12, alpha=0.2, c='blue', label='Origin Points'
    )
    ax.scatter(
        destinations[:, 0], destinations[:, 1], 
        s=12, alpha=0.02, c='red', label='Destination Points'
    )
    
    # 9. Add legend
    plt.legend(loc='upper right', fontsize=22, markerscale=5)
    
    # 10. Add title and labels
    # plt.title("Trip Origins, Destinations and Routes", fontsize=18)
    plt.xlabel("Longitude", fontsize=24)
    plt.ylabel("Latitude", fontsize=24)
    
    # 11. Set tick font size
    plt.xticks(fontsize=22)
    plt.yticks(fontsize=22)
    
    # 12. Add grid
    plt.grid(True, linestyle='--', alpha=0.3)
    
    plt.axis('equal')
    plt.tight_layout()
    
    # 13. Save and show
    plt.savefig('trip_line_plot.png', dpi=300, bbox_inches='tight')
    print("Plot saved as 'trip_line_plot.png'")
    plt.show()

# # 使用示例
# if __name__ == "__main__":
#     # Initialize district boundaries
#     boundary = DistrictBoundary("district_boundaries.json")
    
#     # Plot trip lines
#     csv_file = "..\\dataV3\\v2-hdv.csv"  # 替换为实际文件路径
#     plot_trip_lines(csv_file, boundary, sample_fraction=0.005, line_alpha=0.1)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, LinearSegmentedColormap
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
from shapely.geometry import Polygon, box
from shapely.ops import clip_by_rect

def plot_vehicle_heatmap_english(csv_file, boundary):
    """
    Plot vehicle distribution heatmap (grid-based) with Wuhan administrative districts
    
    Parameters:
    csv_file -- path to the CSV file containing vehicle position data
    boundary -- DistrictBoundary object containing district boundary information
    """
    # 1. Define grid parameters
    min_lon = 113.942617
    max_lon = 114.629031
    min_lat = 30.255898
    max_lat = 30.742468
    lon_step = 0.0103997242944
    lat_step = 0.0089831117499
    
    # Calculate grid dimensions
    num_cols = int(round((max_lon - min_lon) / lon_step))
    num_rows = int(round((max_lat - min_lat) / lat_step))
    
    # 2. Read CSV file
    print(f"Reading data file: {csv_file}")
    df = pd.read_csv(csv_file)
    print(f"Total records: {len(df)}")
    
    # 3. Filter valid data (start points within Wuhan area)
    valid_df = df[(df['起点经度'] >= min_lon) & (df['起点经度'] < max_lon) &
                  (df['起点纬度'] >= min_lat) & (df['起点纬度'] < max_lat) #&
                  # (df['订单来源'] == '调度单') & (df['订单状态'] == '完成')
                  ]
    # valid_df = df[(df['start_lon'] >= min_lon) & (df['start_lon'] < max_lon) &
    #              (df['start_lat'] >= min_lat) & (df['start_lat'] < max_lat)]
    print(f"Valid records: {len(valid_df)} (removed {len(df)-len(valid_df)} invalid points)")
    
    # 4. Initialize grid count matrix
    grid_counts = np.zeros((num_rows, num_cols), dtype=int)
    
    # 5. Calculate grid positions and count vehicles
    def get_grid_xy(lon, lat):
        """Calculate grid column (x) and row (y) for given longitude and latitude"""
        if pd.isna(lon) or pd.isna(lat):
            return (-1, -1)
        # Calculate column and row
        x = int((lon - min_lon) / lon_step)
        y = int((lat - min_lat) / lat_step)
        # Boundary check
        if 0 <= x < num_cols and 0 <= y < num_rows:
            return (x, y)
        return (-1, -1)
    
    # Iterate over all valid starting points
    for _, row in valid_df.iterrows():
        x, y = get_grid_xy(row['起点经度'], row['起点纬度'])
        # x, y = get_grid_xy(row['start_lon'], row['start_lat'])
        if x != -1 and y != -1:
            grid_counts[y, x] += 1
    
    # 6. Create map and heatmap
    plt.figure(figsize=(12, 12))
    ax = plt.gca()
    
    # 7. Create a bounding box for clipping
    wuhan_bbox = box(min_lon, min_lat, max_lon, max_lat)
    
    # 8. Plot district boundaries (outlines only)
    print("Plotting Wuhan administrative district boundaries...")
    for district, polygons in boundary.polygons.items():
        for polygon in polygons:
            # Clip polygon to Wuhan bounding box
            clipped_poly = clip_by_rect(polygon, min_lon, min_lat, max_lon, max_lat)
            
            # Plot only if it's a Polygon (could be MultiPolygon after clipping)
            if isinstance(clipped_poly, Polygon):
                x, y = clipped_poly.exterior.xy
                ax.plot(x, y, color='black', linewidth=0.8, alpha=0.5)
            elif hasattr(clipped_poly, 'geoms'):  # MultiPolygon
                for poly_part in clipped_poly.geoms:
                    x, y = poly_part.exterior.xy
                    ax.plot(x, y, color='black', linewidth=0.8, alpha=0.5)
    
    # 9. Create heatmap
    print("Creating vehicle heatmap...")
    
    # Create custom color map (light yellow to dark red)
    heatmap_colors = ["#FFFFCC", "#FFEDA0", "#FED976", "#FEB24C", "#FD8D3C", 
                      "#FC4E2A", "#E31A1C", "#BD0026", "#800026"]
    heatmap_cmap = LinearSegmentedColormap.from_list("vehicle_heatmap", heatmap_colors)
    
    # Use logarithmic normalization (due to large count variations)
    norm = LogNorm(vmin=max(1, grid_counts.min()), vmax=grid_counts.max())
    
    # Calculate grid coordinates
    lon_edges = np.linspace(min_lon, max_lon, num_cols + 1)
    lat_edges = np.linspace(min_lat, max_lat, num_rows + 1)
    
    # Plot heatmap using pcolormesh for precise geolocation
    heatmap = ax.pcolormesh(
        lon_edges, 
        lat_edges, 
        grid_counts, 
        cmap=heatmap_cmap,
        norm=norm,
        alpha=0.9,  # Mostly opaque
        shading='auto'
    )
    
    texts = []
    # 10. Add district labels (pinyin)
    for district in boundary.polygons.keys():
        # Get district centroid
        centroid = boundary.get_district_centroid(district)
        if centroid:
            # Only plot if centroid is within bounds
            if min_lon <= centroid.x <= max_lon and min_lat <= centroid.y <= max_lat:
                district = remove_district_suffix(district)
                py_name = boundary.name_to_pinyin.get(district, district)
                text = plt.text(centroid.x, centroid.y, py_name, 
                         fontsize=20, ha='center', va='center',
                         bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
                texts.append(text)

    
    # 使用adjustText自动调整标签位置避免重叠
    adjust_text(texts, 
                arrowprops=dict(arrowstyle='->', color='gray', lw=0.5),
                expand_points=(1.2, 1.2), 
                expand_text=(1.2, 1.2),
                force_points=0.2,
                force_text=0.2)
    
    # 11. Add color bar
    cbar = plt.colorbar(heatmap, fraction=0.03, pad=0.04)
    cbar.set_label('Order Count (log scale)', fontsize=20)
    cbar.ax.tick_params(labelsize=22)
    
    plt.xticks(fontsize=22)
    plt.yticks(fontsize=22)
    
    # 12. Add title and labels
    # plt.title("Vehicle Distribution Heatmap in Wuhan (Grid-Based)", fontsize=18)
    plt.xlabel("Longitude", fontsize=24)
    plt.ylabel("Latitude", fontsize=24)
    
    # 13. Add grid information
    grid_info = f"Grid size: {num_cols}×{num_rows} (columns×rows)\nCell size: {lon_step:.6f}°×{lat_step:.6f}°"
    plt.text(0.98, 0.02, grid_info, 
             transform=ax.transAxes, fontsize=20,
             horizontalalignment='right', verticalalignment='bottom',
             bbox=dict(facecolor='white', alpha=0.7))
    
    # 14. Set coordinate range and aspect ratio
    plt.xlim(min_lon, max_lon)
    plt.ylim(min_lat, max_lat)
    ax.set_aspect('equal')
    
    # 15. Add grid lines for reference
    plt.grid(True, linestyle=':', color='gray', alpha=0.3)
    
    plt.tight_layout()
    
    # 16. Save and display
    plt.savefig('vehicle_heatmap_av.svg', dpi=300, bbox_inches='tight')
    print("Heatmap saved as 'vehicle_heatmap_english.png'")
    plt.show()

# # Example usage
if __name__ == "__main__":
    # Initialize district boundaries
    boundary = DistrictBoundary("district_boundaries.json")
    
    # Plot vehicle heatmap
    # csv_file = "..\\dataV3\\v3-districts.csv"  # Replace with actual file path
    csv_file = "..\\dataV3\\v6-av.csv"  # Replace with actual file path
    plot_vehicle_heatmap_english(csv_file, boundary)


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib as mpl
from shapely.geometry import Polygon
from adjustText import adjust_text
import matplotlib.patheffects as patheffects  # 新增路径效果模块
def plot_time_period_bars(csv_file, boundary):
    
    # 数据加载和处理（保持不变）
    df = pd.read_csv(csv_file)
    df['呼单时间'] = pd.to_datetime(df['呼单时间'])
    df['小时'] = df['呼单时间'].dt.hour
    
    # 时段定义（包含持续小时数）
    time_periods = {
        "Morning": {"start": 7, "end": 9},    # 持续时间2小时
        "Noon": {"start": 9, "end": 17},    # 8小时
        "Evening": {"start": 17, "end": 20},  # 3小时 
        "Night": {"start": 20, "end": 24}     # 4小时
    }

    # 处理跨天时段（示例）
    # time_periods["凌晨"] = {"start": 0, "end": 5}  # 5小时
    
    # 加载数据
    df = pd.read_csv(csv_file)
    df['呼单时间'] = pd.to_datetime(df['呼单时间'])
    df['小时'] = df['呼单时间'].dt.hour

    # 统计逻辑
    district_stats = {}
    for district in boundary.polygons.keys():
        district_data = df[df['起点所属区'] == district]
        period_counts = {}
        
        for period, time_range in time_periods.items():
            start = time_range['start']
            end = time_range['end']
            
            # 计算持续时间
            if start < end:
                duration = end - start
                mask = (district_data['小时'] >= start) & (district_data['小时'] < end)
            else:  # 处理跨天时段
                duration = (24 - start) + end
                mask = (district_data['小时'] >= start) | (district_data['小时'] < end)
            
            # 计算小时平均
            total_orders = mask.sum()
            period_counts[period] = total_orders / duration if duration > 0 else 0
        
        district_stats[district] = period_counts
    """Modified visualization function with: 
    1. English labels
    2. Nature-style formatting
    3. Height-normalized bars"""
    
    # 样式配置
    plt.style.use('default')
    plt.rcParams.update({
        'font.sans-serif': 'Arial',
        'axes.labelsize': 10,
        'axes.titlesize': 12,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'axes.edgecolor': 'black',
        'axes.linewidth': 0.8,
        'legend.fontsize': 9,
        'legend.title_fontsize': 10
    })

    # 时段定义和颜色
    time_periods = {
        "Morning": (7, 9),  
        "Noon": (9, 17),  
        "Evening": (17, 20),
        "Night": (20, 24)
    }

    period_colors = {
    "Morning": "#FF6B6B",  # 亮珊瑚色
    "Noon": "#4ECDC4",    # 青蓝色
    "Evening": "#45B7D1",  # 天蓝色
    "Night": "#FF9F43"     # 橙色
}




    # 创建画布
    fig, ax = plt.subplots(figsize=(6, 5), dpi=300)
    
    # # 绘制区域边界
    # for district, polygons in boundary.polygons.items():
    #     for polygon in polygons:
    #         x, y = polygon.exterior.xy
    #         ax.plot(x, y, color='black', linewidth=0.6, zorder=1)
            
            
    # 计算各区域内部通勤比例
    intra_ratios = {}
    for district in boundary.polygons.keys():
        # 筛选本区出发的订单
        departures = df[df['起点所属区'] == district]
        
        if len(departures) == 0:
            intra_ratios[district] = 0
            continue
            
        # 计算区内出行比例
        intra_commute = departures[departures['终点所属区'] == district]
        intra_ratios[district] = len(intra_commute) / len(departures)

    # 设置颜色映射（区内通勤比例越高颜色越深）
    colors = ["white", "#909090"]
    cmap = LinearSegmentedColormap.from_list("white_gray", colors)
    norm = plt.Normalize(vmin=0, vmax=1)
    color_mapper = {district: cmap(norm(ratio)) 
                    for district, ratio in intra_ratios.items()}

    # 在原绘图逻辑中添加颜色设置
    # plt.figure(figsize=(15, 10))
    # ax = plt.gca()
    
    # 绘制行政区域（新增颜色填充）
    for district, polygons in boundary.polygons.items():
        # 使用区内通勤比例确定填充颜色
        for polygon in polygons:
            plt.fill(*polygon.exterior.xy, 
                    color=color_mapper[district], 
                    alpha=1,  # 透明度可调
                    edgecolor='black',
                    linewidth=0.5)

    # 添加颜色图例
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, shrink=0.8)
    cbar.set_label("Ratio for in-zone trip", fontsize=12)
        
            
            
            

    # 自动缩放控制
    all_points = np.concatenate([polygon.exterior.coords for polygons in boundary.polygons.values() for polygon in polygons])
    x_center, y_center = np.mean(all_points, axis=0)
    max_span = max(np.ptp(all_points[:,0]), np.ptp(all_points[:,1])) * 0.6
    
    # 智能高度缩放
    max_count = max([max(d.values()) for d in district_stats.values()]) or 1
    height_scale = (max_span * 0.15) / max_count  # 控制最大高度为区域跨度的15%
    ax.set_xlim(113.8, 114.8)  # min_lon, max_lon
    ax.set_ylim(30.0, 30.9)    # min_lat, max_lat
    ax.set_aspect('equal', adjustable='box')  # 保持纵横比
    # 绘制柱状图
    texts = []
    for district, counts in district_stats.items():
        centroid = boundary.get_district_centroid(district)
        if not centroid:
            continue

        base_x = centroid.x - (len(time_periods)*0.008)/2
        base_y = centroid.y
        
        # 绘制柱状图
        for i, (period, count) in enumerate(counts.items()):
            rect = Rectangle(
                (base_x + i*0.02, base_y), 
                0.02, 
                count * height_scale,
                color=period_colors[period],
                alpha=0.8,
                edgecolor='black',
                linewidth=0.01,
                zorder=2, path_effects=[patheffects.withStroke(linewidth=1, foreground='black')]
            )
            ax.add_patch(rect)

        # 添加区域标签
        district = remove_district_suffix(district)
        py_name = boundary.name_to_pinyin.get(district, district)
        # text = ax.text(
        #     centroid.x,
        #     base_y - max_span*0.02,  # 动态偏移
        #     py_name,
        #     fontsize=8,
        #     ha='center',
        #     va='top',
        #     bbox=dict(facecolor='white', alpha=0.9, pad=1, edgecolor='none')
        # )
        # texts.append(text)
    


    # 使用adjustText自动调整标签位置避免重叠
    # adjust_text(texts, 
    #             arrowprops=dict(arrowstyle='->', color='gray', lw=0.5),
    #             expand_points=(1.2, 1.2), 
    #             expand_text=(1.2, 1.2),
    #             force_points=0.2,
    #             force_text=0.2)

    # 坐标轴设置
    # ax.set_xlim(x_center - max_span, x_center + max_span)
    # ax.set_ylim(y_center - max_span, y_center + max_span)
    ax.set_xlabel("Longitude", labelpad=5)
    ax.set_ylabel("Latitude", labelpad=5)
    ax.set_title("Spatial-Temporal Order Distribution", pad=15)

    # Nature-style图例
    legend_elements = [Patch(facecolor=color, edgecolor='black', label=label) 
                      for label, color in period_colors.items()]
    ax.legend(
        handles=legend_elements,
        loc='lower right',
        frameon=True,
        title="Time Periods",
        borderpad=1,
        title_fontproperties={'weight':'semibold'}
    )
    
    

    # 保存输出
    plt.savefig('order_distribution.svg', format='svg', bbox_inches='tight')
    plt.close()
# # 使用示例
# if __name__ == "__main__":
#     # 初始化区域边界
#     boundary = DistrictBoundary("district_boundaries.json")
    
#     # 绘制时段分布柱状图
#     csv_file = "..\\dataV3\\v6-av.csv"  # 替换为实际文件路径
#     plot_time_period_bars(csv_file, boundary)
