# -*- coding: utf-8 -*-
"""
Created on Tue Dec  3 18:38:00 2024

@author: TLab
"""
import pandas as pd

def classify_destination(destination):
    """根据终点描述分类终点类型"""
    # 定义关键词与终点类型的映射
    residential_keywords = ['·', '墨水', '电气','叠翠','小区', '公寓', '社区', '住宅', '苑', '幢', '佳园', '世茂', '碧桂园', '绿地', '兰亭', '水榭', '复地', '保利', '水墨',
                            '花园', '民宿', '住宅', '宿舍', '栋', '万科', '融创']
    industrial_keywords = ['机器人', '研发','创新','供应','钢','铁','工业园', '厂', '生产', '基地', '制造', '公司', '物流', '矿', '办公', '产业', '科技', '创意园', '控股',
                           '大楼', '写字楼', '集团', '大厦', '仓库', '配送']
    commercial_keywords = ['肉','量贩','养护','眼','果','厨','味','万象','商场', '购', '商业', '写字楼', '超市', '商店', '店)', '广场', '餐', '饭', '玩', '食', '面', '电竞', '炒货', '管',
                           '滑雪','小吃', '蛋糕', '糕点', '咖啡', '茶', '酒', '百货', '便利', '家电', '电器', '商铺', '烤', '鱼', '生鲜', '石业',
                           '市场', '通讯', '营业', '售票', '洗衣', '图文', '照相', '房产', '彩票', '宠物', '游乐', '数码', '水暖', '美容', '客房', '客栈', 
                           '美容', '美发', '美甲', '理发', '度假', '影', 'KTV', '剧', '网', '游戏', '洗浴', '集市', '定制', '饰', '装', '旗舰', '婚礼',
                           '按摩', '推拿', '休闲', '健身', '教育', '4S店', 'SPA', '宾馆', "假日", "营销", "大街", "理疗", '用品', '门业', '材', '批发', '窗', '具', '棋牌']
    transportation_keywords = ['地铁站', '公交站', '车站', '机场', '码头', '停车', '路', '道', '停靠', 'A口', 'B口', 'C口', 'D口', 'E口', '渡',
                               '汽车站', '港口', '加油', '服务区', '收费站', '桥', '电站', '站口', '充电', '回程', '线']
    infrastructure_keywords = ['邮局', '物流', '维修', '所', '驿站', '学院', '学校', '客运','校','一中','二中','三中','四中','五中','六中','七中','八中',"九中","十中",
                               '大学', '中学', '小学', '幼儿园'] 
    infrastructure2_keywords = [ '会议', '公园', '物园', '水族馆', "公厕", '景区', '景点', '文化', '法庭', '委', '消防', '博览', '少年', '培训', '就业', "公社", '福利院',
                               '寺', '庙', '博物馆', '术', '科技馆', '图书馆', '园博园', '体', '球', '银行', '信用', '社会', '检察院', '法', '考', '托管',
                               '机构', '广播', '电视', '药', '体检', '疗养', '康', '救', '疾', '医', '政', '门诊', '局', '服务'] 
    residential2_keywords = ['生活', '家', '楼', '城', '湾', '寓', '居', '室', '邸', '府', '云著', '村', '镇', '馆', '境', '江山', '岸', '天地', '庭', '廷', '著']
    commercial2_keywords = ['店']
    
    destination = destination.upper()  # 转为小写，避免大小写问题
    
    # 判断终点类型
    if any(keyword in destination for keyword in residential_keywords):
        return '居住区'
    elif any(keyword in destination for keyword in industrial_keywords):
        return '工业区'
    elif any(keyword in destination for keyword in commercial_keywords):
        return '商业区'
    elif any(keyword in destination for keyword in transportation_keywords):
        return '交通设施'
    elif any(keyword in destination for keyword in infrastructure_keywords):
        return '公共设施-通勤'
    elif any(keyword in destination for keyword in infrastructure2_keywords):
        return '公共设施-服务'
    elif any(keyword in destination for keyword in residential2_keywords):
        return '居住区'
    elif any(keyword in destination for keyword in commercial2_keywords):
        return '商业区'
    else:
        return '其他'

def add_order_nature(df):
    """给数据框添加订单性质列"""
    df['订单起点性质'] = df['呼单起点'].apply(classify_destination)
    df['订单终点性质'] = df['呼单终点'].apply(classify_destination)
    return df

# 示例调用
df = pd.read_csv('v1-vir.csv')  # 假设文件名为 input.csv
df = add_order_nature(df)
df.to_csv('v2-nature.csv', index=False)  # 输出包含“订单性质”的新文件


# 统计“其他”分类的条目
other_count = len(df[df['订单起点性质'] == '其他'])

# 随机选择50条数据
other_data_sample = df[df['订单起点性质'] == '其他'].sample(n=50, random_state=42)

# 输出统计信息和随机抽样的结果
print(f"总共分类为'其他'的条目数: {other_count}")
print("随机输出的50条'其他'分类数据:")
print(other_data_sample[['呼单起点', '订单起点性质']])
