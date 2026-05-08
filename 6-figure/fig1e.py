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
    # valid_df = df[(df['起点经度'] >= min_lon) & (df['起点经度'] < max_lon) &
    #              (df['起点纬度'] >= min_lat) & (df['起点纬度'] < max_lat)]
    valid_df = df[(df['Longitude'] >= min_lon) & (df['Longitude'] < max_lon) &
                 (df['Latitude'] >= min_lat) & (df['Latitude'] < max_lat)]
    print(f"Valid records: {len(valid_df)} (removed {len(df)-len(valid_df)} invalid points)")
    
    # 4. Initialize grid count matrix
    grid_counts = np.zeros((num_rows, num_cols), dtype=float)
    
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
        # x, y = get_grid_xy(row['起点经度'], row['起点纬度'])
        x, y = get_grid_xy(row['Longitude'], row['Latitude'])
        if x != -1 and y != -1:
            grid_counts[y, x] += row['CO2(g)']
    
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
    heatmap_colors = [
    "#FFFFFF",  # 纯白 (最低值)
    "#E6F5FF",  # 冰蓝
    "#B3E0FF",  # 浅海水
    "#66C2FF",  # 中等海水
    "#3399FF",  # 标准蓝
    "#0066CC",  # 深海蓝
    "#004C99",  # 午夜蓝
    "#003366",  # 深渊蓝
    "#000033"   # 近黑 (最高值)
    ]
    heatmap_cmap = LinearSegmentedColormap.from_list("CO2 Heatmap", heatmap_colors)
    
    # Use logarithmic normalization (due to large count variations)
    vmin = np.percentile(grid_counts, 70)  # 去掉最小5%极小值
    vmax = np.percentile(grid_counts, 99) # 去掉最大5%极大值
    
    print(vmin)
    print(vmax)
    norm = LogNorm(vmin=max(1, vmin), vmax=vmax)
    
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
    cbar.set_label('CO2(g) (log scale)', fontsize=20)
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
    plt.savefig('fig1e.svg', dpi=300, bbox_inches='tight')
    print("Heatmap saved as 'vehicle_heatmap_english.png'")
    plt.show()

def plot_vehicle_heatmap_english2(csv_file, boundary):
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
    # valid_df = df[(df['起点经度'] >= min_lon) & (df['起点经度'] < max_lon) &
    #              (df['起点纬度'] >= min_lat) & (df['起点纬度'] < max_lat)]
    # valid_df = df[(df['Longitude'] >= min_lon) & (df['Longitude'] < max_lon) &
    #              (df['Latitude'] >= min_lat) & (df['Latitude'] < max_lat)]
    # print(f"Valid records: {len(valid_df)} (removed {len(df)-len(valid_df)} invalid points)")
    
    # 4. Initialize grid count matrix
    grid_counts = np.zeros((num_rows, num_cols), dtype=float)
    
    # # 5. Calculate grid positions and count vehicles
    # def get_grid_xy(lon, lat):
    #     """Calculate grid column (x) and row (y) for given longitude and latitude"""
    #     if pd.isna(lon) or pd.isna(lat):
    #         return (-1, -1)
    #     # Calculate column and row
    #     x = int((lon - min_lon) / lon_step)
    #     y = int((lat - min_lat) / lat_step)
    #     # Boundary check
    #     if 0 <= x < num_cols and 0 <= y < num_rows:
    #         return (x, y)
    #     return (-1, -1)
    
    # # Iterate over all valid starting points
    # for _, row in valid_df.iterrows():
    #     # x, y = get_grid_xy(row['起点经度'], row['起点纬度'])
    #     x, y = get_grid_xy(row['Longitude'], row['Latitude'])
    #     if x != -1 and y != -1:
    #         grid_counts[y, x] += row['CO2(g)']
    
    ### HDV
    
    for _, row in df.iterrows():
        x = int(row['grid_x'])
        y = int(row['grid_y'])
        if x != -1 and y != -1:
            grid_counts[y, x] += row['CO2(g)']
    
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
    heatmap_colors = [
    "#FFFFFF",  # 纯白 (最低值)
    "#E6F5FF",  # 冰蓝
    "#B3E0FF",  # 浅海水
    "#66C2FF",  # 中等海水
    "#3399FF",  # 标准蓝
    "#0066CC",  # 深海蓝
    "#004C99",  # 午夜蓝
    "#003366",  # 深渊蓝
    "#000033"   # 近黑 (最高值)
    ]
    heatmap_cmap = LinearSegmentedColormap.from_list("CO2 Heatmap", heatmap_colors)
    vmin = np.percentile(grid_counts, 50)  # 去掉最小5%极小值
    vmax = np.percentile(grid_counts, 95) # 去掉最大5%极大值
    
    print(vmin)
    print(vmax)
    norm = LogNorm(vmin=max(1, vmin), vmax=vmax)
    # Use logarithmic normalization (due to large count variations)
    # norm = LogNorm(vmin=max(1, grid_counts.min()), vmax=grid_counts.max())
    
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
    cbar.set_label('CO2(g) (log scale)', fontsize=20)
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
    plt.savefig('fig1f.svg', dpi=300, bbox_inches='tight')
    print("Heatmap saved as 'vehicle_heatmap_english.png'")
    plt.show()

# Example usage
if __name__ == "__main__":
    # Initialize district boundaries
    boundary = DistrictBoundary("district_boundaries.json")
    
    # Plot vehicle heatmap
    # csv_file = "..\\dataV3\\v4-av.csv"  # Replace with actual file path
    csv_file = "vehicle_stats_detail_av_v2.csv"  # Replace with actual file path
    # csv_file = "grid_co2_stats.csv"
    plot_vehicle_heatmap_english(csv_file, boundary)


