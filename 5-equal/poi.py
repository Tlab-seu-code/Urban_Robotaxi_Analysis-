# -*- coding: utf-8 -*-
"""
Created on Sun Jun 22 15:39:08 2025

@author: WuxiTlab
"""

import pandas as pd
import os

# 定义分类映射关系（原始类别 -> 目标类别）
category_mapping = {
    '商务住宅': 'home',
    '公司企业': 'work',
    '政府机构及社会团体': 'work',
    '科教文化服务': 'education',
    '餐饮服务': 'leisure',
    '购物服务': 'leisure',
    '体育休闲服务': 'leisure',
    '风景名胜': 'leisure',
    '医疗保健服务': 'healthcare'
}

# 创建目标目录
output_dir = 'classified_poi'
os.makedirs(output_dir, exist_ok=True)

# 初始化分类数据容器
classified_data = {category: [] for category in ['home', 'work', 'education', 'leisure', 'healthcare']}

# 处理每个原始CSV文件
for filename, category_name in [
    ('武汉市_商务住宅.csv', '商务住宅'),
    ('武汉市_公司企业.csv', '公司企业'),
    ('武汉市_政府机构及社会团体.csv', '政府机构及社会团体'),
    ('武汉市_科教文化服务.csv', '科教文化服务'),
    ('武汉市_餐饮服务.csv', '餐饮服务'),
    ('武汉市_购物服务.csv', '购物服务'),
    ('武汉市_体育休闲服务.csv', '体育休闲服务'),
    ('武汉市_风景名胜.csv', '风景名胜'),
    ('武汉市_医疗保健服务.csv', '医疗保健服务')
]:
    if category_name in category_mapping:
        target_category = category_mapping[category_name]
        try:
            # 读取CSV文件
            df = pd.read_csv(filename)
            # 添加原始类别标记
            df['source_category'] = category_name
            # 添加到对应分类
            classified_data[target_category].append(df)
            print(f"已处理: {filename} -> {target_category}")
        except FileNotFoundError:
            print(f"文件未找到: {filename}, 跳过")
        except Exception as e:
            print(f"处理文件 {filename} 时出错: {str(e)}")

# 合并并保存分类数据
for category, data_list in classified_data.items():
    if data_list:
        combined_df = pd.concat(data_list, ignore_index=True)
        output_path = os.path.join(output_dir, f'{category}.csv')
        combined_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"已创建: {output_path} ({len(combined_df)}条记录)")
    else:
        print(f"警告: {category} 类别无数据")

print("\n分类完成! 结果保存在", output_dir, "目录")