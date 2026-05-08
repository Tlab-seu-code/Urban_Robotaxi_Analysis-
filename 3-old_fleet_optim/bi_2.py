# -*- coding: utf-8 -*-
"""
Created on Fri Dec 27 16:49:34 2024

@author: TLab
"""

import networkx as nx
import pickle
import os
import json  # 用于保存最大匹配结果

# 定义读取二部图并计算最大匹配的函数
def calculate_maximum_matching(graph_file, left_set=None):
    """
    读取保存的二部图文件，并计算最大匹配。
    :param graph_file: 二部图文件路径 (.gpickle)
    :param left_set: 左侧节点集合（可选，若未提供将自动推断）
    :return: 最大匹配结果（字典形式）
    """
    # 从文件中加载二部图
    with open(graph_file, "rb") as f:
        G = pickle.load(f)

    # 如果未提供左侧集合，则推断二部图的左、右集合
    if left_set is None:
        # 假设二部图已经指定了 `bipartite` 属性
        left_set = {n for n, d in G.nodes(data=True) if d.get("bipartite") == 0}
    
    # 计算最大匹配
    matching = nx.algorithms.bipartite.matching.maximum_matching(G, top_nodes=left_set)
    
    # 返回匹配结果
    return matching

# 示例：处理文件夹中的多个二部图文件
def process_graphs(folder_path, output_folder):
    """
    处理指定文件夹中的所有二部图文件，计算并保存最大匹配。
    :param folder_path: 存储二部图的文件夹路径
    :param output_folder: 保存最大匹配结果的文件夹路径
    """
    # 获取文件夹中所有 .gpickle 文件
    graph_files = [f for f in os.listdir(folder_path) if f.endswith(".gpickle")]

    # 创建保存结果的文件夹（如果不存在）
    os.makedirs(output_folder, exist_ok=True)

    for graph_file in graph_files:
        # 构建完整路径
        full_path = os.path.join(folder_path, graph_file)
        
        print(f"正在处理文件：{graph_file}...")
        # 计算最大匹配
        matching = calculate_maximum_matching(full_path)

        # 保存匹配结果到文件
        matching_file = os.path.join(output_folder, graph_file.replace(".gpickle", "_matching.json"))
        with open(matching_file, "w", encoding="utf-8") as f:
            # 将字典保存为 JSON 格式
            json.dump(matching, f, ensure_ascii=False, indent=4)

        print(f"文件 {graph_file} 的最大匹配完成，匹配边数：{len(matching) // 2}")
        print(f"匹配结果已保存到 {matching_file}")

# 指定存储二部图的文件夹路径和输出路径
graph_folder = "graph"  # 修改为实际二部图文件夹路径
output_folder = "matching_results"  # 保存最大匹配结果的文件夹

# 计算所有图的最大匹配并保存结果
process_graphs(graph_folder, output_folder)


