# # -*- coding: utf-8 -*-
# """
# Created on Fri Dec 27 20:58:47 2024

# @author: TLab
# """

# import json
# import os

# # 文件路径
# input_folder = "matching_results"  # 最大匹配的JSON文件目录
# output_folder = "order_chains"  # 输出链路的目录
# os.makedirs(output_folder, exist_ok=True)
# car = []

# # 假设我们有一个函数 can_merge(chain1, chain2)，用于检查两个链路是否可以合并
# def can_merge(chain1, chain2):
#     # 检查chain1的末尾是否是chain2的开头，或者chain1的开头是否是chain2的末尾
#     return (chain1[-1] == chain2[0]) or (chain1[0] == chain2[-1])

# # 遍历所有 JSON 文件
# for filename in os.listdir(input_folder):
#     if filename.endswith(".json"):
#         # 读取 JSON 文件
#         input_path = os.path.join(input_folder, filename)
#         with open(input_path, "r", encoding="utf-8") as f:
#             matching = json.load(f)

#         # 过滤并去掉后缀，保留订单A -> 订单B 的方向
#         filtered_edges = []
#         for left, right in matching.items():
#             if left.endswith("_left") and right.endswith("_right"):
#                 left_order = left.replace("_left", "")  # 去掉 _left
#                 right_order = right.replace("_right", "")  # 去掉 _right
#                 filtered_edges.append((left_order, right_order))

#         # 构造订单链路
#         order_chains = []  # 二维列表，存储链路
#         # 初始化每个订单作为一个单独的链路
#         order_chains = [[order[0],order[1]] for order in filtered_edges]  # 去重后的订单列表，并初始化为单独链路
         
#         # 标记是否有合并发生，以便在没有合并时退出循环
#         merged = True
         
#         while merged:
#             merged = False
#             i = -1
#             j = -1
#             # 遍历所有链路的组合
#             while i < (len(order_chains)-1):
#                 i += 1
#                 j = -1
#                 while j < (len(order_chains)-1):
#                     j += 1
#                     if i == j:
#                         continue
                    
#                     chain_i = order_chains[i]
#                     chain_j = order_chains[j]
                    
#                     # 检查两个链路是否可以合并
#                     if can_merge(chain_i, chain_j):
#                         # 确定合并后的新链路
#                         if chain_i[-1] == chain_j[0]:
#                             merged_chain = chain_i + chain_j[1:]
#                         else:  # chain_i[0] == chain_j[-1]
#                             merged_chain = chain_j[:-1] + chain_i
                        
#                         # 更新链表，用合并后的新链路替换旧的两个链路
#                         order_chains[i] = merged_chain
#                         order_chains.pop(j)  # 移除已合并的chain_j
                        
#                         if i > j:
#                             i -= 1
                        
#                         merged = True
#                         break  # 跳出内层循环，继续外层循环检查其他链路组合
 

#         # 保存链路到 JSON 文件
#         output_path = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}_chains.json")
#         with open(output_path, "w", encoding="utf-8") as f:
#             json.dump(order_chains, f, ensure_ascii=False, indent=4)
        
#         car.append(len(order_chains))
#         print(f"需要车辆:{len(order_chains)}")
#         print(f"已处理并保存链路文件：{output_path}")
#         total_length = sum(len(chain) for chain in order_chains)
#         average_length = total_length / len(order_chains) if order_chains else 0
#         count_leq_5 = sum(1 for chain in order_chains if len(chain) <= 5)
#         print("链路的平均长度:", average_length)
#         print("长度<=5的链路数量:", count_leq_5)

# print("所有文件处理完成！")

import json
import os
import pandas as pd
import re  # 用于正则表达式提取日期

# 文件路径
input_folder = "matching_results"  # 最大匹配的JSON文件目录
output_folder = "order_chains"  # 输出链路的目录
os.makedirs(output_folder, exist_ok=True)

# 假设我们有一个函数 can_merge(chain1, chain2)，用于检查两个链路是否可以合并
def can_merge(chain1, chain2):
    # 检查chain1的末尾是否是chain2的开头，或者chain1的开头是否是chain2的末尾
    return (chain1[-1] == chain2[0]) or (chain1[0] == chain2[-1])

# 读取原始的car.csv文件
df = pd.read_csv('car.csv')

# 用于存储额外的统计信息
additional_info = []

# 定义一个正则表达式，用于从文件名中提取日期（格式为YYYY-MM-DD）
date_pattern = r'(\d{4}-\d{2}-\d{2})'

# 遍历所有 JSON 文件
for filename in os.listdir(input_folder):
    if filename.endswith(".json"):
        # 从文件名中提取日期
        date_match = re.search(date_pattern, filename)
        if date_match:
            date_str = date_match.group(1)  # 提取到的日期字符串
        else:
            continue  # 如果没有找到日期，就跳过该文件

        # 读取 JSON 文件
        input_path = os.path.join(input_folder, filename)
        with open(input_path, "r", encoding="utf-8") as f:
            matching = json.load(f)

        # 过滤并去掉后缀，保留订单A -> 订单B 的方向
        filtered_edges = []
        for left, right in matching.items():
            if left.endswith("_left") and right.endswith("_right"):
                left_order = left.replace("_left", "")  # 去掉 _left
                right_order = right.replace("_right", "")  # 去掉 _right
                filtered_edges.append((left_order, right_order))

        # 构造订单链路
        order_chains = []  # 二维列表，存储链路
        # 初始化每个订单作为一个单独的链路
        order_chains = [[order[0], order[1]] for order in filtered_edges]  # 去重后的订单列表，并初始化为单独链路
         
        # 标记是否有合并发生，以便在没有合并时退出循环
        merged = True
         
        while merged:
            merged = False
            i = -1
            j = -1
            # 遍历所有链路的组合
            while i < (len(order_chains) - 1):
                i += 1
                j = -1
                while j < (len(order_chains) - 1):
                    j += 1
                    if i == j:
                        continue
                    
                    chain_i = order_chains[i]
                    chain_j = order_chains[j]
                    
                    # 检查两个链路是否可以合并
                    if can_merge(chain_i, chain_j):
                        # 确定合并后的新链路
                        if chain_i[-1] == chain_j[0]:
                            merged_chain = chain_i + chain_j[1:]
                        else:  # chain_i[0] == chain_j[-1]
                            merged_chain = chain_j[:-1] + chain_i
                        
                        # 更新链表，用合并后的新链路替换旧的两个链路
                        order_chains[i] = merged_chain
                        order_chains.pop(j)  # 移除已合并的chain_j
                        
                        if i > j:
                            i -= 1
                        
                        merged = True
                        break  # 跳出内层循环，继续外层循环检查其他链路组合

        # 保存链路到 JSON 文件
        output_path = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}_chains.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(order_chains, f, ensure_ascii=False, indent=4)

        # 统计信息
        car_count = len(order_chains)
        total_length = sum(len(chain) for chain in order_chains)
        average_length = total_length / car_count if car_count else 0
        count_leq_5 = sum(1 for chain in order_chains if len(chain) <= 5)

        print(f"需要车辆:{car_count}")
        print(f"已处理并保存链路文件：{output_path}")
        print("链路的平均长度:", average_length)
        print("长度<=5的链路数量:", count_leq_5)

        # 将统计信息附加到additional_info列表
        additional_info.append({
            '日期': date_str,  # 从文件名提取的日期
            '需要车辆': car_count,
            '平均行程数': average_length,
            '小于5车辆': count_leq_5
        })

# 将附加的统计信息转换为DataFrame
additional_df = pd.DataFrame(additional_info)

# 将car.csv中的数据和附加的统计信息合并
df = df.set_index('日期')
combined_df = df.join(additional_df.set_index('日期'))

# 将合并后的结果保存到car.csv文件
combined_df.to_csv('car.csv')

print("所有文件处理完成！")

