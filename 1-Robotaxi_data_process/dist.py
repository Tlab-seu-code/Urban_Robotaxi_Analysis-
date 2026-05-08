# -*- coding: utf-8 -*-
"""
Created on Wed Dec  4 16:17:31 2024

@author: TLab
"""

import json
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon
import random

# import requests

# # 接口地址
# url = "https://api.map.baidu.com/api_region_search/v1/"

# # 此处填写你在控制台-应用管理-创建应用后获取的AK
# ak = "pt1AifsHEfnUgXE4qkuFvKZJ0JHGU81h"

# params = {
#     "keyword":    "420107",
#     "sub_admin":    "0",
#     "ak":       ak,
#     "boundary":    "1",
# }

# response = requests.get(url=url, params=params)
# if response:
#     print(response.json())


# 配置中文字体为黑体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 或者 'SimHei' 根据安装的字体来选择
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

class DistrictBoundary:
    def __init__(self, json_file):
        # 读取json文件中的边界信息
        self.district_data = self.load_boundary_data(json_file)
        self.polygons = self.create_polygons()

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
        plt.figure(figsize=(10, 8))
        for polygon in self.polygons[district_name]:
            x, y = polygon.exterior.xy
            plt.plot(x, y, label=district_name, color='blue')
            plt.fill(x, y, color='lightblue', alpha=0.5)  # 填充区域

        plt.title(f"{district_name} 边界")
        plt.xlabel("经度")
        plt.ylabel("纬度")
        plt.axis('equal')  # 保持经纬度比例一致
        plt.legend()
        plt.show()

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
        """绘制所有区域的边界，每个区域不同颜色"""
        plt.figure(figsize=(10, 8))

        # 为每个区域选择一个随机颜色
        color_list = ['#%02x%02x%02x' % (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)) for _ in range(len(self.polygons))]

        # 绘制每个区域的多边形
        for idx, (district_name, polygons) in enumerate(self.polygons.items()):
            color = color_list[idx]  # 随机选择的颜色
            for polygon in polygons:
                x, y = polygon.exterior.xy
                plt.fill(x, y, color=color, alpha=0.5, label=district_name)  # 填充区域
                plt.plot(x, y, color=color)  # 绘制边界

        # 设置图形的标题和标签
        plt.title("所有区域边界", fontsize=15)
        plt.xlabel("经度", fontsize=12)
        plt.ylabel("纬度", fontsize=12)
        plt.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=10)  # 显示图例
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

# 定义函数：根据CSV文件中的起点和终点经纬度，添加所属区域列
def add_district_columns(input_csv, output_csv, district_boundary):
    # 读取原始CSV文件
    df = pd.read_csv(input_csv)

    # 初始化新的列
    df['起点所属区'] = None
    df['终点所属区'] = None

    # 遍历每一行，计算起点和终点所属的区
    for index, row in df.iterrows():
        
        if index % 1000 == 0:
            print(index)
        
        # 获取起点经纬度
        start_lon = row['起点经度']
        start_lat = row['起点纬度']
        # 获取终点经纬度
        end_lon = row['终点经度']
        end_lat = row['终点纬度']

        # 使用 find_district 方法查找所属区
        start_district = district_boundary.find_district(start_lon, start_lat)
        end_district = district_boundary.find_district(end_lon, end_lat)

        # 更新数据框中的新列
        df.at[index, '起点所属区'] = start_district
        df.at[index, '终点所属区'] = end_district

    # 将更新后的数据保存为新的CSV文件
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"结果已保存到 {output_csv}")

# 使用示例
boundary = DistrictBoundary("district_boundaries.json")  # 初始化区域边界类
input_csv = "v2-nature.csv"
output_csv = "v3-districts.csv"

# 调用函数，处理数据
add_district_columns(input_csv, output_csv, boundary)


# 使用示例：
# 创建一个 DistrictBoundary 类的实例，并绘制指定区域的边界
boundary = DistrictBoundary("district_boundaries.json")

# # # 查找经纬度所在的区
# lon, lat = 114.0829776, 30.46287465  # 输入你想查找的经纬度
# district = boundary.find_district(lon, lat)
# print(f"经纬度 ({lon}, {lat}) 属于: {district}")


# # 使用示例：
# # 创建一个 DistrictBoundary 类的实例，并绘制指定区域的边界

# boundary.plot_district("江夏区")  # 绘制江夏区的边界
# boundary.plot_district("东西湖区")  # 绘制东西湖区的边界
# boundary.plot_district("汉阳区")  # 绘制江夏区的边界
# boundary.plot_district("武昌区")  # 绘制东西湖区的边界
# boundary.plot_district("洪山区")  # 绘制江夏区的边界
# boundary.plot_district("黄陂区")  # 绘制东西湖区的边界
# boundary.plot_district("江汉区")  # 绘制江夏区的边界
# boundary.plot_district("硚口区")  # 绘制东西湖区的边界
# boundary.plot_district("青山区")  # 绘制江夏区的边界
# boundary.plot_district("江岸区")  # 绘制东西湖区的边界
# boundary.plot_district("蔡甸区")  # 绘制江夏区的边界
# boundary.plot_district("新洲区")  # 绘制东西湖区的边界
# boundary.plot_district("汉南区")  # 绘制东西湖区的边界
# # 使用示例：

boundary.plot_all_districts()  # 绘制所有区域的边界






# class taxi:
#     初始参数：
#     2. 状态（充电、完成订单、接驾（到达用户的起点）、调度、空闲）
#     3. 车辆上已经坐的人数
#     4. 目的地（经纬度）
#     5. 当前位置（经纬度）
#     6. 当前单号
    
#     def 运行（时间步）:
#         按照当前状态运行一个时间步长，更新状态、车辆位置等
        
    
#     def 运行（时间步）:
#         按照当前状态运行一个时间步长

# class simulator:
#     初始参数：
#     1. 当前时间
#     2. 模拟的时间步长
#     3. 乘客需求表
#     4. 车辆表


# encoding:utf-8
# import requests
# import json

# # 接口地址
# url = "https://api.map.baidu.com/api_region_search/v1/"

# # 此处填写你在控制台-应用管理-创建应用后获取的AK
# ak = "pt1AifsHEfnUgXE4qkuFvKZJ0JHGU81h"

# # 需要获取边界信息的区域
# districts = [
#     "江夏区", "东西湖区", "汉阳区", "武昌区", "洪山区", 
#     "黄陂区", "江汉区", "硚口区", "青山区", "江岸区", 
#     "蔡甸区", "新洲区", "汉南区"
# ]

# # 存储结果的列表
# results = []

# # 获取每个区域的边界信息
# for district in districts:
#     params = {
#         "keyword": district,
#         "sub_admin": "0",
#         "ak": ak,
#         "boundary": "1",
#     }

#     response = requests.get(url=url, params=params)
    
#     if response.status_code == 200 and response.json().get('status') == 0:
#         data = response.json()
#         if data['result_size'] > 0:
#             # 获取区域的名称和polygon数据
#             region_data = data['districts'][0]
#             results.append({
#                 "name": region_data['name'],
#                 "polyline": region_data['polyline']
#             })
#         else:
#             print(f"未找到{district}的边界信息")
#     else:
#         print(f"请求{district}时发生错误")

# # 将结果保存到json文件
# with open('district_boundaries.json', 'w', encoding='utf-8') as f:
#     json.dump(results, f, ensure_ascii=False, indent=4)

# print("边界信息已保存至 'district_boundaries.json' 文件")





