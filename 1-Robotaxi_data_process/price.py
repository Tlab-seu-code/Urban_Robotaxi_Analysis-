import pandas as pd
from datetime import datetime, time

def is_rest_day(date_str):
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    return date_obj.weekday() >= 5  # 周六或周日为休息日

def get_fee(time_obj, time_ranges):
    for tr in time_ranges:
        start = datetime.strptime(tr['start'], '%H:%M').time()
        end = datetime.strptime(tr['end'], '%H:%M').time()
        if (start <= time_obj <= end) if start <= end else (time_obj >= start or time_obj <= end):
            return tr['fee']
    raise ValueError(f"Time {time_obj} 未匹配到时段")

# 工作日起步费时段
start_fee_workday = [
    {'start': '00:00', 'end': '07:00', 'fee': 15.0},
    {'start': '07:00', 'end': '09:00', 'fee': 16.0},
    {'start': '09:00', 'end': '17:00', 'fee': 15.0},
    {'start': '17:00', 'end': '21:00', 'fee': 16.0},
    {'start': '21:00', 'end': '00:00', 'fee': 15.0},
]

# 工作日里程费时段
mileage_fee_workday = [
    {'start': '00:00', 'end': '06:00', 'fee': 3.5},
    {'start': '06:00', 'end': '07:00', 'fee': 2.6},
    {'start': '07:00', 'end': '09:00', 'fee': 2.9},
    {'start': '09:00', 'end': '17:00', 'fee': 2.4},
    {'start': '17:00', 'end': '21:00', 'fee': 2.9},
    {'start': '21:00', 'end': '23:00', 'fee': 2.6},
    {'start': '23:00', 'end': '00:00', 'fee': 3.5},
]

# 休息日里程费时段
mileage_fee_rest = [
    {'start': '00:00', 'end': '06:00', 'fee': 3.5},
    {'start': '06:00', 'end': '10:00', 'fee': 2.6},
    {'start': '10:00', 'end': '16:00', 'fee': 2.9},
    {'start': '16:00', 'end': '20:00', 'fee': 2.6},
    {'start': '20:00', 'end': '22:00', 'fee': 2.9},
    {'start': '22:00', 'end': '23:00', 'fee': 2.6},
    {'start': '23:00', 'end': '00:00', 'fee': 3.5},
]

# 工作时长费时段
duration_fee_workday = [
    {'start': '00:00', 'end': '07:00', 'fee': 0.2},
    {'start': '07:00', 'end': '09:00', 'fee': 0.4},
    {'start': '09:00', 'end': '17:00', 'fee': 0.2},
    {'start': '17:00', 'end': '21:00', 'fee': 0.4},
    {'start': '21:00', 'end': '00:00', 'fee': 0.2},
]

def calculate_price(row):
    try:
        date_str = row['日期']
        call_time = datetime.strptime(row['呼单时间'], '%Y-%m-%d %H:%M:%S').time()
    except:
        return 0.0
    
    is_rest = is_rest_day(date_str)
    
    # 起步费
    if is_rest:
        start_fee = 15.0
    else:
        start_fee = get_fee(call_time, start_fee_workday)
    
    # 里程费
    mileage = float(row.get('行程里程', 0.0))
    beyond_mileage = max(0.0, mileage - 1.0)
    
    if is_rest:
        mileage_rate = get_fee(call_time, mileage_fee_rest)
    else:
        mileage_rate = get_fee(call_time, mileage_fee_workday)
    mileage_fee = round(beyond_mileage * mileage_rate, 2)
    
    # 时长费（秒转分钟）
    duration_seconds = float(row.get('行程时长', 0.0))
    duration_minutes = duration_seconds / 60.0
    beyond_duration = max(0.0, duration_minutes - 2.0)
    
    if is_rest:
        duration_rate = 0.2
    else:
        duration_rate = get_fee(call_time, duration_fee_workday)
    duration_fee = round(beyond_duration * duration_rate, 2)
    
    # 远途费（修正逻辑：无论是否休息日）
    long_distance_fee = 0.0
    if mileage > 8.0:
        part1 = max(0.0, min(mileage, 12.0) - 8.0)
        part2 = max(0.0, mileage - 12.0)
        long_distance_fee = part1 * 1.5 + part2 * 2.5
    
    total = round(start_fee + mileage_fee + duration_fee + long_distance_fee, 2)
    return total

# 应用并保存
df = pd.read_csv('v3-districts.csv')
df['价格'] = df.apply(calculate_price, axis=1)
df.to_csv('v4-districts-with-price.csv', index=False)