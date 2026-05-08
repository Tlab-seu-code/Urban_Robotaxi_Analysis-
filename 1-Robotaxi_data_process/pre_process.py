import pandas as pd

def process_taxi_orders(file_path, output_path):
    # 读取数据
    df = pd.read_csv(file_path)
    
    # 新建 index 列并标注虚拟单
    #df['虚拟单合并数'] = 1  # 正常单标注为 0
    #df.loc[(df['订单来源'] == '调度单'), '虚拟单合并数'] = 1  # 虚拟单标注为 1

    # 初始化取消次数列
    #df['取消次数'] = 0

    # 按车辆代号和订单创建时间排序
    #df.sort_values(by=['车辆id', '呼单时间'], inplace=True)

    # 初始化结果列表
    results = []
    temp_virtuals = []  # 临时存储连续虚拟单的列表
    
    
    # 遍历数据，识别和合并连续虚拟单
    #for _, row in df.iterrows():
    #    if _ % 10000 == 0:
    #        print(_)
        
    #    if row['虚拟单合并数'] == 1:  # 如果是虚拟单
            # 检查是否属于同一连续虚拟单
    #        if temp_virtuals and temp_virtuals[-1]['呼单终点'] != row['呼单起点']:
                # 如果连续性中断，合并前面的虚拟单
    #            merged = merge_virtual_orders(temp_virtuals)
    #            results.append(merged)
    #            temp_virtuals = []
    #        temp_virtuals.append(row)
    #    else:
            # 如果是正常单，先处理已有的虚拟单
    #        if temp_virtuals:
    #            merged = merge_virtual_orders(temp_virtuals)
    #            results.append(merged)
    #            temp_virtuals = []
    #        results.append(row)
    
    # 处理最后剩余的虚拟单
    #if temp_virtuals:
    #    merged = merge_virtual_orders(temp_virtuals)
    #    results.append(merged)
    
    # 转换为 DataFrame，处理取消单合并
    # result_df = pd.DataFrame(results)
    df = merge_canceled_orders(df)

    # 保存结果
    df.to_csv(output_path, index=False)

def merge_virtual_orders(orders):
    """合并连续的虚拟单"""
    # 初始化合并结果为第一个订单的副本
    merged_order = orders[0].copy()
    
    # 更新订单号、时间字段
    merged_order['订单号'] = orders[0]['订单号']
    merged_order['呼单时间'] = orders[0]['呼单时间']
    merged_order['接单时间'] = orders[0]['接单时间']
    merged_order['出发接驾时间'] = orders[0]['出发接驾时间']
    merged_order['到达起点时间'] = orders[0]['到达起点时间']
    
    # 更新起点字段：使用第一个订单
    merged_order['呼单起点'] = orders[0]['呼单起点']
    merged_order['起点经度'] = orders[0]['起点经度']
    merged_order['起点纬度'] = orders[0]['起点纬度']
    
    # 更新终点字段：使用最后一个订单
    merged_order['呼单终点'] = orders[-1]['呼单终点']
    merged_order['终点经度'] = orders[-1]['终点经度']
    merged_order['终点纬度'] = orders[-1]['终点纬度']
    
    # 更新累计字段
    merged_order['接驾时长'] = sum(order['接驾时长'] for order in orders)
    merged_order['接驾里程'] = sum(order['接驾里程'] for order in orders)
    merged_order['行程时长'] = sum(order['行程时长'] for order in orders)
    merged_order['行程里程'] = sum(order['行程里程'] for order in orders)
    
    # 标注虚拟单合并数量
    merged_order['虚拟单合并数'] = len(orders)
    
    return merged_order

def merge_canceled_orders(df):
    """合并取消单到完成单"""
    canceled_orders = df[df['订单状态'] == '取消']
    completed_orders = df[df['订单状态'] == '完成']
    completed_orders = completed_orders[completed_orders['订单来源'] != '调度单']
    completed_orders = completed_orders[completed_orders['订单来源'] != '充电单']
    completed_orders = completed_orders[completed_orders['用户id'] != 'virtual_schedule']

    print(len(completed_orders))

    count = 0
    # 遍历每个完成单，检查其之前的取消单
    for idx, completed in completed_orders.iterrows():
        count += 1
        if count % 10 == 0:
            print(count)
        vehicle_id = completed['车辆id']
        vehicl_id = completed['用户id']
        completed_time = completed['呼单时间']
        start_point = completed['呼单起点']
        end_point = completed['呼单终点']

        # 查找同一车辆之前的取消单
        candidates = canceled_orders[
            (canceled_orders['车辆id'] == vehicle_id) &
            (canceled_orders['用户id'] == vehicl_id) &
            (canceled_orders['呼单时间'] < completed_time) &
            ((canceled_orders['呼单起点'] == start_point) | (canceled_orders['呼单终点'] == end_point))
        ]
                
        # 合并取消单
        if not candidates.empty:
            # 确保只删除存在的索引
            valid_indices = candidates.index.intersection(df.index)
            df.drop(valid_indices, inplace=True)

            # 累计取消次数
            df.at[idx, '取消次数'] += len(candidates)
            # print("删除！")

    return df


# 示例调用
process_taxi_orders('v1-vir.csv', 'v1-vir-cancel.csv')
