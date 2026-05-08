# -*- coding: utf-8 -*-
"""
Created on Mon Dec 16 14:41:36 2024

@author: TLab
"""

import pandas as pd

# 读取两个 Excel 文件
df1 = pd.read_excel('11.xlsx')
df2 = pd.read_excel('12.xlsx')

# 合并数据（假设两文件字段完全相同，直接上下合并）
df_combined = pd.concat([df1, df2], ignore_index=True)

# 保存合并后的结果为 CSV 文件
df_combined.to_csv('original.csv', index=False)

print("文件已成功合并并保存为 original.csv")
