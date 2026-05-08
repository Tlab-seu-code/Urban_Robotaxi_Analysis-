# import csv

# # 假设文件名为'large_file.txt'，这里应该替换为你的实际文件名
# filename = '20240708.txt'

# # 读取文件的第二行（索引从0开始，所以第二行的索引是1）
# with open(filename, 'r', encoding='utf-8') as file:
#     lines = file.readlines()
#     if len(lines) < 2:
#         print("文件中没有足够的行。")
#         exit()
    
#     # 获取第二行的数据，并去掉可能存在的换行符
#     second_line = lines[1].strip()
    
#     # 分割第二行数据，得到每条轨迹记录（以分号分隔）
#     track_records = second_line.split(';')
    
#     # 创建一个CSV文件的写入对象，这里将输出文件命名为'track_data.csv'
#     csv_filename = 'track_data.csv'
#     with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
#         # 写入CSV文件的表头
#         fieldnames = ['ID', 'GPSID', 'Timestamp', 'Longitude', 'Latitude', 'Speed', 'Direction']
#         writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
#         writer.writeheader()
        
#         # 遍历每条轨迹记录，并分割成字段（以逗号分隔）
#         for record in track_records:
#             if record:  # 确保记录不是空字符串
#                 fields = record.split(',')
#                 if len(fields) == 6:  # 确保字段数量正确（有时最后一条记录可能不完整）
#                     # 将字段赋值给一个字典，然后写入CSV文件
#                     track_dict = {
#                         'ID': fields[0].split()[0],  # 假设ID是每条记录开头的部分，直到第一个空格
#                         'GPSID': fields[0].split()[1] if ' ' in fields[0] else '',  # 如果ID中有空格，则提取第二部分作为GPSID（这里可能需要根据你的实际数据格式进行调整）
#                         # 注意：由于你的示例中ID和GPSID实际上是相同的，并且没有明确的空格分隔，
#                         # 所以这里我们简单地假设它们相同，并只使用fields[0]作为ID和GPSID。
#                         # 如果实际情况不同，请相应地调整下面的代码。
#                         'Timestamp': fields[1],
#                         'Longitude': fields[2],
#                         'Latitude': fields[3],
#                         'Speed': fields[4],
#                         'Direction': fields[5]
#                     }
#                     # 但由于你的ID和GPSID字段实际上是合并的，并且看起来是相同的，
#                     # 下面是一个更简单的处理方式，只使用fields[0]作为ID（和GPSID，如果它们相同的话）：
#                     track_dict_simplified = {
#                         'ID': fields[0],  # 这里假设ID就是整个fields[0]
#                         'GPSID': fields[0],  # 如果GPSID和ID相同
#                         'Timestamp': fields[1],
#                         'Longitude': fields[2],
#                         'Latitude': fields[3],
#                         'Speed': fields[4],
#                         'Direction': fields[5]
#                     }
#                     writer.writerow(track_dict_simplified)
#                 else:
#                     print(f"警告：记录 '{record}' 的字段数量不正确，跳过。")
#             else:
#                 print("警告：遇到空记录，跳过。")

# print(f"轨迹数据已成功写入 {csv_filename}")


import pandas as pd
import time

# 设置字体样式
import matplotlib.pyplot as plt
plt.rcParams['font.size'] = 12
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 读取并显示CSV文件的前10行数据
def read_csv_file():
    # 读取CSV文件（仅限前10行）
    df = pd.read_csv("./csv/20240708.csv", encoding='UTF-8', nrows=10)
    print(df)

# 读取并处理TXT文件，将处理后的数据保存为CSV文件
def process_txt_to_csv():
    filename = "./20240708.txt"  # 输入文件路径
    df = pd.read_csv(filename, delimiter='\\t', encoding='UTF-8')
    
    # 用来存储转换后的数据
    rows = []
    
    # 逐行遍历TXT文件中的数据
    for i in range(len(df)):
        s_id = df['ID'][i]  # 获取车辆ID
        traj = df['TRACK'][i].split(';')  # 将轨迹数据分割成单个点
    
        # 遍历每个轨迹点（去掉最后一个点）
        for j in range(len(traj) - 1):
            a = traj[j].split(',')  # 每个点用逗号分割
            rows.append({
                "id": s_id,
                'time': a[0], 
                'lon': a[1], 
                'lat': a[2], 
                'speed': a[3], 
                'state': a[5]
            })
    
    # 创建新的DataFrame
    date = pd.DataFrame(rows, columns=['id', 'time', 'lon', 'lat', 'speed', 'state'])
    
    # 将结果保存到新的CSV文件
    date.to_csv('./20240708.csv', index=0)
    print("数据处理完毕，已保存为 20240908.csv")

if __name__ == '__main__':
    # 执行数据处理函数
    # read_csv_file()  # 可选：读取并展示CSV文件内容
    process_txt_to_csv()  # 处理TXT文件并保存为CSV文件


