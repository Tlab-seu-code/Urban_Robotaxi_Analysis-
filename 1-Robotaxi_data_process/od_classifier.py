import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.preprocessing import LabelEncoder
from tqdm import tqdm
import argparse
import os
import math
import numpy as np

tqdm.pandas()

# ---------- 辅助函数 ----------
def get_time_category(dt):
    total_minutes = dt.hour * 60 + dt.minute
    if 300 <= total_minutes <= 540:
        return "清晨"
    elif 541 <= total_minutes <= 690:
        return "上午"
    elif 691 <= total_minutes <= 750:
        return "中午"
    elif 751 <= total_minutes <= 1050:
        return "下午"
    elif 1051 <= total_minutes <= 1140:
        return "傍晚"
    elif 1141 <= total_minutes <= 1380:
        return "晚上"
    elif total_minutes >= 1381 or total_minutes <= 60:
        return "午夜"
    elif 61 <= total_minutes <= 299:
        return "凌晨"
    else:
        return "未知"

def haversine_distance(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    R = 6371.0 * 1000
    return R * c

# ---------- 模块 1: 数据加载和初步过滤 ----------
def load_and_filter_data(input_file):
    print("Step 1: 读取数据并初步过滤")
    df = pd.read_csv(input_file, low_memory=False)
    df = df[df['订单状态'] == '取消']
    df = df[df['用户id'] != 'virtual_schedule']
    print("初步过滤后数据行数:", len(df))
    return df

# ---------- 模块 2: 按呼单时间过滤 ----------
def filter_by_call_time(df):
    print("Step 2: 按呼单时间过滤数据 (小于5分钟的只保留最后一条记录)")
    df['呼单时间'] = pd.to_datetime(df['呼单时间'])
    df = df.sort_values(by=['用户id','呼单时间']).reset_index(drop=True)
    
    keep_indices = []
    for user_id, group in df.groupby('用户id'):
        group = group.sort_values(by='呼单时间').reset_index()  # 保存原索引
        candidate_index = group.loc[0, 'index']
        candidate_time = group.loc[0, '呼单时间']
        for i in range(1, len(group)):
            current_time = group.loc[i, '呼单时间']
            diff_minutes = (current_time - candidate_time).total_seconds()/60
            if diff_minutes < 5:
                candidate_index = group.loc[i, 'index']
                candidate_time = current_time
            else:
                keep_indices.append(candidate_index)
                candidate_index = group.loc[i, 'index']
                candidate_time = current_time
        keep_indices.append(candidate_index)
    df = df.loc[keep_indices].sort_values(by=['用户id','呼单时间'])
    print("时间过滤后数据行数:", len(df))
    return df

# ---------- 模块 3: 地址分类预测 ----------
def address_classification(df, model_path='fine_tuned_address_model'):
    print("Step 3: 地址分类预测")
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    le = LabelEncoder()
    le.fit([
        '居住区','工业/产业区','商业区','交通枢纽','通勤支持设施',
        '教育科研机构','医疗卫生设施','政务/基础服务与社区服务','企业办公/写字楼',
        '文旅文化/展览区','体育设施','金融设施','其他'
    ])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    def predict(text):
        if not isinstance(text, str):
            text = str(text)
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=128)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs)
        logits = outputs.logits
        pred_idx = torch.argmax(logits, dim=1).item()
        return le.inverse_transform([pred_idx])[0]
    start_col_idx = df.columns.get_loc('呼单起点')
    df.insert(start_col_idx+1, '起点类型', df['呼单起点'].progress_apply(predict))
    end_col_idx = df.columns.get_loc('呼单终点')
    df.insert(end_col_idx+1, '终点类型', df['呼单终点'].progress_apply(predict))
    return df

# ---------- 模块 4: 计算行程直线距离和接驾距离 ----------
def calc_distance_and_pickup_distance(df):
    print("Step 4: 计算行程直线距离和接驾距离")
    time_cols = ["呼单时间", "取消时间", "出发接驾时间", "接单时间"]
    for col in time_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    df["总等待时间"] = (df["取消时间"] - df["呼单时间"]).dt.total_seconds()
    df["等待接单时间"] = (df["出发接驾时间"] - df["呼单时间"]).dt.total_seconds()
    df.loc[df["接单时间"].isna(), "等待接单时间"] = df["总等待时间"]
    df = df[df["总等待时间"] != 0]
    # 计算行程直线距离
    distance_series = df.apply(lambda row: haversine_distance(
        row["起点经度"], row["起点纬度"],
        row["终点经度"], row["终点纬度"]), axis=1)
    end_lat_index = df.columns.get_loc("终点纬度")
    if "行程直线总长（米）" in df.columns:
        df["行程直线总长（米）"] = distance_series
    else:
        df.insert(end_lat_index+1, "行程直线总长（米）", distance_series)
    # 处理接驾距离
    df = process_pickup_distance(df)
    return df

# ---------- 模块 5: 日期处理 ----------
def process_date_only(df):
    print("Step 5: 日期处理")
    df["日期"] = pd.to_datetime(df["日期"], format='%m/%d/%Y', errors='coerce')
    df["工作日"] = df["日期"].dt.weekday.apply(lambda x: 1 if x < 5 else 0)
    return df

# ---------- 模块 6: 基础时间段、高峰标记与接单时长 ----------
def process_basic_time_features(df):
    print("Step 6: 处理基础时间段、高峰标记与接单时长")
    # 基础时间段：使用原有粗粒度方法
    df["基础时间段"] = df["呼单时间"].apply(get_time_category)
    # 高峰标记
    def is_peak_time(dt):
        if pd.isnull(dt):
            return 0
        total_minutes = dt.hour * 60 + dt.minute
        return int((450 <= total_minutes <= 570) or (1050 <= total_minutes <= 1110) or (1200 <= total_minutes <= 1260))
    df["高峰"] = df["呼单时间"].apply(is_peak_time)
    # 接单时长
    df = process_pickup_duration(df)
    return df

# ---------- 模块 7: 时间特征处理升级 ----------
def process_time_features_upgrade(df, retain_time_segment):
    print("Step 7: 处理时间特征升级")
    # 提取累计分钟数
    df["total_minutes"] = df["呼单时间"].dt.hour * 60 + df["呼单时间"].dt.minute
    # 半小时分箱：0~47
    df["half_hour_bin"] = (df["total_minutes"] // 30).astype(int)
    # 循环特征
    df["sin_time"] = np.sin(2 * np.pi * df["total_minutes"] / 1440)
    df["cos_time"] = np.cos(2 * np.pi * df["total_minutes"] / 1440)
    # 聚合特征：每个半小时箱内的平均总等待时间
    avg_wait = df.groupby("half_hour_bin")["总等待时间"].mean().rename("avg_wait_by_half_hour")
    df = df.merge(avg_wait, on="half_hour_bin", how="left")
    # 判断是否保留原有基础时间段
    if not retain_time_segment:
        if "基础时间段" in df.columns:
            df.drop(columns=["基础时间段"], inplace=True)
    return df

# ---------- 模块 8: 交互特征 ----------
def process_interaction_features(df):
    print("Step 8: 构造交互特征")
    df["交互_起点所属区_高峰"] = df["起点所属区"].astype(str) + "_" + df["高峰"].astype(str)
    df["交互_直线距离_高峰"] = df["行程直线总长（米）"] * df["高峰"]
    return df

# ---------- 模块 6.5: 处理接单时长 ----------
def process_pickup_duration(df):
    print("Step 6.5: 处理接单时长")
    def classify_pickup(row):
        if pd.isnull(row["接单时间"]):
            return "未成功接单"
        diff_minutes = (row["接单时间"] - row["呼单时间"]).total_seconds() / 60.0
        if diff_minutes <= 1:
            return "立即接单"
        elif diff_minutes <= 5:
            return "5分钟内接单"
        else:
            return "5分钟以上接单"
    df["接单时长"] = df.apply(classify_pickup, axis=1)
    return df

# ---------- 模块 7.5: 处理接驾距离 ----------
def process_pickup_distance(df):
    print("Step 7.5: 处理接驾距离")
    def classify_distance(x):
        if pd.isna(x) or x == 0:
            return "未开始接驾"
        elif 0 < x < 3:
            return "距离较近"
        elif 3 <= x < 5:
            return "距离中等"
        elif x >= 5:
            return "距离较远"
        else:
            return "未知"
    df["接驾距离"] = df["接驾里程"].apply(classify_distance)
    return df

# ---------- 模块 9: 筛选指定列 ----------
def filter_final_columns(df):
    print("Step 9: 筛选指定列")
    columns_to_keep = [
        "订单来源", "起点类型", "终点类型", "行程直线总长（米）",
        "half_hour_bin", "sin_time", "cos_time", "avg_wait_by_half_hour",
        "基础时间段", "高峰", "交互_直线距离_高峰", "交互_起点所属区_高峰",
        "工作日", "接单时长", "接驾距离", "起点所属区", "终点所属区", "总等待时间"
    ]
    missing = [c for c in columns_to_keep if c not in df.columns]
    if missing:
        print("警告：下列列在数据中未找到，会忽略它们：", missing)
    df_filtered = df[[c for c in columns_to_keep if c in df.columns]]
    return df_filtered

# ---------- 主函数 ----------
def main(args):
    df = load_and_filter_data(args.input)
    
    if args.filter_time:
        df = filter_by_call_time(df)
        df.to_csv("independent_time.csv", index=False, encoding='utf-8-sig')
        
    if args.address_pred:
        df = address_classification(df, model_path=args.model_path)
        df.to_csv("address.csv", index=False, encoding='utf-8-sig')
    
    if args.calc_wait:
        df = calc_distance_and_pickup_distance(df)
        df.to_csv("distance.csv", index=False, encoding='utf-8-sig')
    
    if args.date_process:
        df = process_date_only(df)
        df.to_csv("date.csv", index=False, encoding='utf-8-sig')
    
    if args.basic_time:
        df = process_basic_time_features(df)
        df.to_csv("time.csv", index=False, encoding='utf-8-sig')
    
    if args.time_upgrade:
        df = process_time_features_upgrade(df, retain_time_segment=args.retain_time_segment)
        df.to_csv("time_upgrade.csv", index=False, encoding='utf-8-sig')
    
    if args.interaction:
        df = process_interaction_features(df)
        df.to_csv("interaction.csv", index=False, encoding='utf-8-sig')
    
    # 保存最终完整结果
    df.to_csv(args.output, index=False, encoding='utf-8-sig')
    print(f"所有处理完成，结果已保存到 {args.output}")
    
    if args.filter_columns:
        df_filtered = filter_final_columns(df)
        df_filtered.to_csv("washed_filtered.csv", index=False, encoding='utf-8-sig')
        print("列筛选完成，结果已保存到 washed_filtered.csv")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="数据处理流水线")
    parser.add_argument('--input', type=str, default='v3-districts.csv', help='输入 CSV 文件路径')
    parser.add_argument('--output', type=str, default='washed.csv', help='输出 CSV 文件路径')
    
    parser.add_argument('--filter_time', action='store_true', default=True, help='是否执行呼单时间过滤')
    parser.add_argument('--calc_wait', action='store_true', default=True, help='是否计算等待时间、行程距离和接驾距离')
    parser.add_argument('--address_pred', action='store_true', default=True, help='是否执行地址分类预测')
    parser.add_argument('--date_process', action='store_true', default=True, help='是否进行日期处理')
    parser.add_argument('--basic_time', action='store_true', default=True, help='是否处理基础时间段、高峰标记与接单时长')
    parser.add_argument('--time_upgrade', action='store_true', default=True, help='是否进行时间特征处理升级')
    parser.add_argument('--retain_time_segment', action='store_true', default=False, help='是否保留基础时间段变量；若False则删除并替换')
    parser.add_argument('--interaction', action='store_true', default=True, help='是否构造交互特征')
    parser.add_argument('--filter_columns', action='store_true', default=True, help='是否筛选指定的列')
    parser.add_argument('--model_path', type=str, default='fine_tuned_address_model', help='地址分类模型路径')
    
    args = parser.parse_args()
    main(args)
