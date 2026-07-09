import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from statannotations.Annotator import Annotator
import numpy as np
import math  # 提前导入math，避免后续报错

# ---------------- 核心参数与常量定义 (更新为3类数据配置，新增反转时段顺序) ----------------
# 武汉经纬度范围与网格步长
LON_MIN, LON_MAX = 113.942617, 114.629031
LAT_MIN, LAT_MAX = 30.255898, 30.742468
dx = 0.0103997242944  # 1km网格经度步长
dy = 0.0089831117499  # 1km网格纬度步长

period_order = ['Peak hour (Morning)', 'Day', 'Peak hour (Evening)', 'Night']
# 新增：反转后的时段顺序（与Y轴视觉展示一致，核心修复错位关键）
period_order_reversed = period_order[::-1]
BOOTSTRAP_N = 1000  # 重采样次数
CONFIDENCE_LEVEL = 0.95  # 置信水平
ALPHA = 1 - CONFIDENCE_LEVEL  # 新增：显著性水平（与目标代码对齐）

# 设置多个随机种子以确保一致性
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
import random
random.seed(RANDOM_SEED)

# 颜色定义（更新为3类数据）
AV_COLOR = '#FF8C74'  # AV颜色（浅红）
HV_OTHER_COLOR = '#41B1F1'  # Human-driven (other) 颜色（原HV浅蓝）
HV_ELECTRIC_COLOR = '#1E5B99'  # Human-driven (electric) 颜色（深蓝色系）
# 对应浅色调（用于小提琴图/箱线图填充）
AV_LIGHT_COLOR = '#E8ADA0'
HV_OTHER_LIGHT_COLOR = '#66C2F6'
HV_ELECTRIC_LIGHT_COLOR = '#4A7FB8'
# 对应超浅色调（备用）
AV_EXTRA_LIGHT = '#F8E6E2'
HV_OTHER_EXTRA_LIGHT = '#D0ECFC'
HV_ELECTRIC_EXTRA_LIGHT = '#B3C7E6'

# 车辆类型顺序（固定，确保绘图时顺序一致）
VEHICLE_ORDER = ['AV', 'Human-driven (electric)', 'Human-driven (other)']

# 数据文件路径（更新为新的指定路径）
AV_FILE_PATH = r"F:\Research_Group\City_Grading\0927data\v4-av.csv"
HV_FILE_PATH = r"F:\Research_Group\City_Grading\0927data\v10-hdv.csv"

# ---------------- 新增：全局检验结果存储列表（与目标代码对齐，保证随机相关流程完整） ----------------
statistical_test_results = []

# ---------------- 核心工具函数 (适配3类数据) ----------------
def calculate_distance(lon1, lat1, lon2, lat2):
    """新增：计算两点间直线距离（米），用于HV数据补充"""
    R = 6371000  # 地球半径（米）
    lon1_rad = math.radians(lon1)
    lat1_rad = math.radians(lat1)
    lon2_rad = math.radians(lon2)
    lat2_rad = math.radians(lat2)

    delta_lon = lon2_rad - lon1_rad
    delta_lat = lat2_rad - lat1_rad

    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_grid_id(lon, lat):
    """计算网格ID"""
    gx = np.floor((lon - LON_MIN) / dx).astype(int)
    gy = np.floor((lat - LAT_MIN) / dy).astype(int)
    gx = np.clip(gx, 0, int(np.ceil((LON_MAX - LON_MIN) / dx)))
    gy = np.clip(gy, 0, int(np.ceil((LAT_MAX - LAT_MIN) / dy)))
    return gx, gy


def get_all_grid_ids():
    """生成研究范围内的所有网格ID（包含无数据网格）"""
    max_gx = int(np.ceil((LON_MAX - LON_MIN) / dx))
    max_gy = int(np.ceil((LAT_MAX - LAT_MIN) / dy))
    all_grids = []
    for gx in range(max_gx + 1):
        for gy in range(max_gy + 1):
            all_grids.append((gx, gy))
    return all_grids


def classify_time(h):
    """时间时段分类"""
    if 7 <= h < 9:
        return 'Peak hour (Morning)'
    elif 9 <= h < 17:
        return 'Day'
    elif 17 <= h < 20:
        return 'Peak hour (Evening)'
    else:
        return 'Night'


def min_max_normalize(data_series):
    """Min-Max归一化：将数据映射到0~1区间（包含0值网格）"""
    data_array = np.array(list(data_series.values()))
    min_x = data_array.min()
    max_x = data_array.max()

    # 处理所有值相同的情况
    if max_x - min_x < 1e-6:
        return {grid: 0.5 for grid in data_series.keys()}

    # 正常归一化
    normalized_dict = {}
    for grid, x in data_series.items():
        normalized = (x - min_x) / (max_x - min_x)
        normalized_dict[grid] = np.clip(normalized, 0, 1)
    return normalized_dict


def calculate_fairness_index(data):
    """计算公平性指数"""
    data_clean = data[~np.isnan(data)]
    if len(data_clean) < 2:
        return np.nan
    mu = np.mean(data_clean)
    sigma = np.std(data_clean)
    if mu <= 1e-6 or mu >= 1 - 1e-6:
        return np.nan
    fairness = sigma / np.sqrt(mu * (1 - mu))
    return fairness


def align_av_hv_dates(av_data, hv_data):
    """AV与HV数据日期对齐"""
    av_data['date'] = av_data['呼单时间'].dt.date
    av_unique_dates = sorted(av_data['date'].unique())
    hv_data['date'] = hv_data['start_time'].dt.date
    hv_unique_dates = sorted(hv_data['date'].unique())

    common_days_count = min(len(av_unique_dates), len(hv_unique_dates))
    print(f"=== 日期对齐统计 ===")
    print(f"AV数据：覆盖{len(av_unique_dates)}天，共{len(av_data)}条记录")
    print(f"HV数据：覆盖{len(hv_unique_dates)}天，共{len(hv_data)}条记录")
    print(f"日期对齐后：保留{common_days_count}天的匹配数据")

    if common_days_count == 0:
        raise SystemExit(">>> 无可用的共同日期进行匹配，程序终止！")

    av_aligned_dates = av_unique_dates[:common_days_count]
    av_data_aligned = av_data[av_data['date'].isin(av_aligned_dates)].copy()
    hv_aligned_dates = hv_unique_dates[:common_days_count]
    hv_data_aligned = hv_data[hv_data['date'].isin(hv_aligned_dates)].copy()

    av_data_aligned = av_data_aligned.drop(columns=['date'])
    hv_data_aligned = hv_data_aligned.drop(columns=['date'])

    print(f"日期对齐后：AV数据{len(av_data_aligned)}条，HV数据{len(hv_data_aligned)}条")
    return av_data_aligned, hv_data_aligned


def classify_hv_vehicle_type(vehicle_id_series):
    """根据vehicle_id分类HV车辆类型：鄂AD开头为Human-driven (electric)，其他为Human-driven (other)"""
    # 先处理空值，转为字符串
    vehicle_id_str = vehicle_id_series.astype(str).fillna('')
    # 分类（优化为元组匹配，与目标代码对齐，不影响随机性）
    return vehicle_id_str.apply(lambda x: 'Human-driven (electric)' if x.startswith(
        ('鄂AD', '鄂AA', '鄂AF', '鄂AG', '鄂AH', '鄂AJ', '鄂AK')) else 'Human-driven (other)')


def load_and_process_fairness_data():
    """加载并处理公平性数据（适配3类数据格式）"""
    # 读取并清洗AV数据（使用新路径和格式）
    print('读取并清洗AV数据...')
    CHUNK_SZ = 200_000
    av_chunks = []
    for chunk in pd.read_csv(AV_FILE_PATH, chunksize=CHUNK_SZ):
        # 保留关键列并去重、去空
        chunk = chunk.drop_duplicates(subset=['订单号'], keep='first')
        chunk = chunk.dropna(subset=['呼单时间', '起点经度', '起点纬度'])
        # 过滤经纬度范围
        chunk = chunk[(chunk['起点经度'] >= LON_MIN) & (chunk['起点经度'] <= LON_MAX) &
                      (chunk['起点纬度'] >= LAT_MIN) & (chunk['起点纬度'] <= LAT_MAX)]
        # 转换时间格式
        chunk['呼单时间'] = pd.to_datetime(chunk['呼单时间'], errors='coerce')
        chunk = chunk.dropna(subset=['呼单时间'])
        av_chunks.append(chunk)
    av_data = pd.concat(av_chunks, ignore_index=True)
    if len(av_data) == 0:
        raise ValueError("AV数据清洗后为空")

    # 读取并清洗HV数据（使用新路径和格式，增加车辆类型分类）
    print('读取并清洗HV数据...')
    hv_chunks = []
    for chunk in pd.read_csv(HV_FILE_PATH, chunksize=CHUNK_SZ):
        # 保留关键列（新增vehicle_id）并去空
        chunk = chunk.dropna(
            subset=['start_time', 'start_lon', 'start_lat', 'end_time', 'end_lon', 'end_lat', 'vehicle_id'])
        # 过滤经纬度范围
        chunk = chunk[(chunk['start_lon'] >= LON_MIN) & (chunk['start_lon'] <= LON_MAX) &
                      (chunk['start_lat'] >= LAT_MIN) & (chunk['start_lat'] <= LAT_MAX) &
                      (chunk['end_lon'] >= LON_MIN) & (chunk['end_lon'] <= LON_MAX) &
                      (chunk['end_lat'] >= LAT_MIN) & (chunk['end_lat'] <= LAT_MAX)]
        # 转换时间格式
        chunk['start_time'] = pd.to_datetime(chunk['start_time'], errors='coerce')
        chunk['end_time'] = pd.to_datetime(chunk['end_time'], errors='coerce')
        chunk = chunk.dropna(subset=['start_time', 'end_time'])
        hv_chunks.append(chunk)
    hv_data = pd.concat(hv_chunks, ignore_index=True)
    if len(hv_data) == 0:
        raise ValueError("HV数据清洗后为空")

    # 日期对齐
    av_data_aligned, hv_data_aligned = align_av_hv_dates(av_data, hv_data)

    # 对HV数据进行车辆类型分类
    hv_data_aligned['vehicle_type'] = classify_hv_vehicle_type(hv_data_aligned['vehicle_id'])
    print(f"\nHV数据分类统计：")
    print(hv_data_aligned['vehicle_type'].value_counts())

    # 生成所有网格ID
    all_grid_ids = get_all_grid_ids()

    # 处理AV数据
    av_data_aligned['hour'] = av_data_aligned['呼单时间'].dt.hour
    av_data_aligned['period'] = av_data_aligned['hour'].apply(classify_time)
    av_gx, av_gy = get_grid_id(av_data_aligned['起点经度'], av_data_aligned['起点纬度'])
    av_data_aligned['grid_id'] = list(zip(av_gx, av_gy))
    av_data_aligned['vehicle_type'] = 'AV'  # 标记AV车辆类型

    # 处理HV数据（已提前分类vehicle_type）
    hv_data_aligned['hour'] = hv_data_aligned['start_time'].dt.hour
    hv_data_aligned['period'] = hv_data_aligned['hour'].apply(classify_time)
    hv_gx, hv_gy = get_grid_id(hv_data_aligned['start_lon'], hv_data_aligned['start_lat'])
    hv_data_aligned['grid_id'] = list(zip(hv_gx, hv_gy))

    # 合并AV和HV数据（3类）
    combined_data = pd.concat([av_data_aligned, hv_data_aligned], ignore_index=True)
    # 固定车辆类型和时段的分类顺序
    combined_data['vehicle_type'] = pd.Categorical(combined_data['vehicle_type'], categories=VEHICLE_ORDER,
                                                   ordered=True)
    combined_data['period'] = pd.Categorical(combined_data['period'], categories=period_order, ordered=True)

    # 计算各时段、各车辆类型的公平性指数（带重采样）
    fairness_samples = []
    for period in period_order:
        for vehicle_type in VEHICLE_ORDER:
            # 筛选对应时段和车辆类型的数据
            period_vehicle_data = combined_data[(combined_data['period'] == period) &
                                                (combined_data['vehicle_type'] == vehicle_type)]
            if period_vehicle_data.empty:
                print(f"警告：{period} - {vehicle_type} 无数据，跳过公平性计算")
                continue

            # 统计网格订单数（包含无数据网格）
            grid_counts = {grid: 0 for grid in all_grid_ids}
            for grid, count in period_vehicle_data['grid_id'].value_counts().items():
                if grid in grid_counts:
                    grid_counts[grid] = count

            # 归一化
            norm_grid_counts = min_max_normalize(grid_counts)
            norm_array = np.array(list(norm_grid_counts.values()))

            # 重采样计算公平性指数分布（固定随机种子，与目标代码保持一致的随机性）
            for _ in range(BOOTSTRAP_N):
                # 继承全局numpy随机种子，保证重采样结果可复现（与目标代码对齐）
                sample = np.random.choice(norm_array, size=len(norm_array), replace=True)
                fair_index = calculate_fairness_index(sample)
                if not np.isnan(fair_index):
                    fairness_samples.append({
                        'period': period,
                        'vehicle_type': vehicle_type,
                        'fairness': fair_index
                    })

    fairness_df = pd.DataFrame(fairness_samples)
    fairness_df['vehicle_type'] = pd.Categorical(fairness_df['vehicle_type'], categories=VEHICLE_ORDER, ordered=True)
    fairness_df['period'] = pd.Categorical(fairness_df['period'], categories=period_order, ordered=True)
    return fairness_df


def load_av_hv_travel_data():
    """加载AV和HV的行程数据（适配3类数据格式）"""
    # 加载AV数据并提取行程信息（使用新格式）
    print("\n读取AV行程数据...")
    av_df = pd.read_csv(AV_FILE_PATH)
    # 保留关键列并去空（利用已有行程字段）
    av_df = av_df.dropna(
        subset=['呼单时间', '开始行程时间', '到达目的地时间', '起点经度', '起点纬度', '终点经度', '终点纬度',
                '行程时长', '行程里程'])
    # 转换时间格式
    av_df['呼单时间'] = pd.to_datetime(av_df['呼单时间'], errors='coerce')
    av_df['开始行程时间'] = pd.to_datetime(av_df['开始行程时间'], errors='coerce')
    av_df['到达目的地时间'] = pd.to_datetime(av_df['到达目的地时间'], errors='coerce')
    av_df = av_df.dropna(subset=['呼单时间', '开始行程时间', '到达目的地时间'])
    # 行程时长（秒，直接使用已有字段，避免重复计算）
    av_df['duration'] = av_df['行程时长']
    # 行程距离（米，直接使用已有里程转换）
    av_df['distance'] = av_df['行程里程'] * 1000  # 行程里程单位是km，转为米
    # 提取时段
    av_df['hour'] = av_df['呼单时间'].dt.hour
    av_df['period'] = av_df['hour'].apply(classify_time)
    # 添加车辆类型
    av_df['vehicle_type'] = 'AV'

    # 加载HV数据并提取行程信息（使用新格式，增加车辆类型分类）
    print("\n读取HV行程数据...")
    hv_df = pd.read_csv(HV_FILE_PATH)
    # 保留关键列（新增vehicle_id）并去空（利用已有行程字段）
    hv_df = hv_df.dropna(subset=['start_time', 'end_time', 'start_lon', 'start_lat', 'end_lon', 'end_lat',
                                 'duration', 'travel_length', 'vehicle_id'])
    # 转换时间格式
    hv_df['start_time'] = pd.to_datetime(hv_df['start_time'], errors='coerce')
    hv_df['end_time'] = pd.to_datetime(hv_df['end_time'], errors='coerce')
    hv_df = hv_df.dropna(subset=['start_time', 'end_time'])
    # 行程时长（秒，直接使用已有字段）
    hv_df['duration'] = hv_df['duration']
    # 行程距离（米，直接使用已有行程长度）
    hv_df['distance'] = hv_df['travel_length']
    # 提取时段
    hv_df['hour'] = hv_df['start_time'].dt.hour
    hv_df['period'] = hv_df['hour'].apply(classify_time)
    # 分类HV车辆类型
    hv_df['vehicle_type'] = classify_hv_vehicle_type(hv_df['vehicle_id'])
    print(f"\nHV行程数据分类统计：")
    print(hv_df['vehicle_type'].value_counts())

    # 合并AV和HV数据，只保留需要的列
    common_cols = ['duration', 'distance', 'period', 'vehicle_type']
    combined_df = pd.concat([
        av_df[common_cols],
        hv_df[common_cols]
    ], ignore_index=True)

    # 数据清洗（过滤无效数据）
    combined_df = combined_df.dropna(how="any")
    combined_df = combined_df[(combined_df['duration'] > 60) & (combined_df['duration'] < 7200)]
    combined_df = combined_df[combined_df['distance'] > 0]

    # 计算速度（km/h）
    combined_df["speed_kmh"] = (combined_df["distance"] / 1000) / (combined_df["duration"] / 3600)
    # 转换距离为km、时长为分钟（用于绘图）
    combined_df["distance_km"] = combined_df["distance"] / 1000
    combined_df["duration_min"] = combined_df["duration"] / 60

    # 固定分类顺序
    combined_df['vehicle_type'] = pd.Categorical(combined_df['vehicle_type'], categories=VEHICLE_ORDER, ordered=True)
    combined_df['period'] = pd.Categorical(combined_df['period'], categories=period_order, ordered=True)

    return combined_df


def plot_box_with_stats():
    """绘制包含公平性子图的2×2布局云雨图（仅优化第4个子图，前3个保持原样）"""
    # 加载行程数据（适配3类数据）
    df = load_av_hv_travel_data()

    # 加载公平性数据
    fairness_df = load_and_process_fairness_data()

    # 过滤无效数据
    df = df.dropna(subset=['period', 'vehicle_type'])
    fairness_df = fairness_df.dropna(subset=['period', 'vehicle_type'])

    # 绘图样式设置
    plt.rcParams.update({
        'font.family': 'Calibri',
        'font.size': 24,  # 原来是 12
        'axes.labelsize': 24,  # 原来是 12
        'axes.titlesize': 28,  # 原来是 14
        'xtick.labelsize': 22,  # 原来是 11
        'ytick.labelsize': 22,  # 原来是 11
        'legend.fontsize': 24,  # 原来是 12
        'legend.title_fontsize': 24,  # 原来是 12
        'axes.linewidth': 1,
        'lines.linewidth': 1,
        'xtick.major.width': 1,
        'ytick.major.width': 1,
        'xtick.major.size': 4,
        'ytick.major.size': 4
    })

    # 拓宽画布，适配3类数据的展示
    fig, axes = plt.subplots(2, 2, figsize=(18, 14), dpi=300)
    axes = axes.flatten()  # 转换为一维数组便于索引

    # 颜色映射
    color_map = {
        'AV': AV_COLOR,
        'Human-driven (electric)': HV_ELECTRIC_COLOR,
        'Human-driven (other)': HV_OTHER_COLOR
    }
    light_color_map = {
        'AV': AV_LIGHT_COLOR,
        'Human-driven (electric)': HV_ELECTRIC_LIGHT_COLOR,
        'Human-driven (other)': HV_OTHER_LIGHT_COLOR
    }
    extra_light_color_map = {
        'AV': AV_EXTRA_LIGHT,
        'Human-driven (electric)': HV_ELECTRIC_EXTRA_LIGHT,
        'Human-driven (other)': HV_OTHER_EXTRA_LIGHT
    }

    # 辅助函数：绘制普通子图（完全保留原始样式，修复错位问题）
    def plot_original_chart(ax, data, x_var, x_label, start_from_zero=False):
        """绘制行程数据子图，保留原始样式，修复显著性标注与终端输出错位"""
        # 关键修改1：使用反转后的时段顺序生成Y轴坐标，无需手动反转
        y_positions = np.arange(len(period_order_reversed))
        group_width = 0.8  # 原始组宽度
        hue_dodge = group_width / len(VEHICLE_ORDER)  # 原始间距分配

        # 关键修改2：直接遍历反转后的时段顺序，无需reversed()
        for y_pos, period in zip(y_positions, period_order_reversed):
            for i, vehicle_type in enumerate(VEHICLE_ORDER):
                # 简化center_y计算，与Annotator的dodge参数对齐
                center_y = y_pos + (i - (len(VEHICLE_ORDER) - 1) / 2) * hue_dodge
                # 筛选对应数据
                data_series = data[(data['period'] == period) & (data['vehicle_type'] == vehicle_type)][x_var].dropna()
                if data_series.empty:
                    print(f"警告：{period} - {vehicle_type} 无{x_var}数据，跳过绘图")
                    continue

                # 绘制“云”（半小提琴图，原始参数）
                violin_parts = ax.violinplot(
                    data_series, positions=[center_y], widths=0.3, vert=False,
                    showmeans=False, showmedians=False, showextrema=False
                )
                body = violin_parts['bodies'][0]
                body.set_facecolor(light_color_map[vehicle_type])
                body.set_edgecolor(color_map[vehicle_type])
                body.set_linewidth(1)

                # 手动分割小提琴（原始逻辑）
                path = body.get_paths()[0]
                vertices = path.vertices
                violin_center_y = vertices[:, 1].mean()
                if vehicle_type == 'AV':
                    vertices[:, 1] = np.where(vertices[:, 1] <= violin_center_y + 0.05, vertices[:, 1],
                                              violin_center_y + 0.05)
                elif vehicle_type == 'Human-driven (electric)':
                    vertices = vertices
                else:
                    vertices[:, 1] = np.where(vertices[:, 1] >= violin_center_y - 0.05, vertices[:, 1],
                                              violin_center_y - 0.05)

                # 绘制箱线图总结（原始参数）
                box_y = violin_center_y
                bp = ax.boxplot(
                    data_series, positions=[box_y], widths=0.15, vert=False,
                    patch_artist=True, showfliers=False
                )
                plt.setp(bp['boxes'], facecolor=light_color_map[vehicle_type], edgecolor='black', linewidth=1)
                plt.setp(bp['medians'], color='black', linewidth=2)
                plt.setp(bp['whiskers'], color=color_map[vehicle_type], linewidth=1)
                plt.setp(bp['caps'], color=color_map[vehicle_type], linewidth=1)

                # 绘制“雨点”（随机采样散点，固定随机种子保证一致性）
                def sample_points_without_outliers(series, n_points=15):
                    """移除离群值后采样（固定随机种子，与目标代码对齐）"""
                    Q1 = series.quantile(0.25)
                    Q3 = series.quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR
                    non_outliers = series[(series >= lower_bound) & (series <= upper_bound)]
                    if len(non_outliers) < n_points:
                        return non_outliers
                    # 固定随机种子RANDOM_SEED，保证采样结果可复现
                    return non_outliers.sample(n=n_points, random_state=RANDOM_SEED)

                sampled_series = sample_points_without_outliers(data_series, n_points=15)
                # 固定抖动种子，使用独立随机数生成器
                rng = np.random.default_rng(seed=RANDOM_SEED)
                y_jit = rng.normal(box_y, 0.02, size=len(sampled_series))
                ax.scatter(
                    sampled_series, y_jit, color=color_map[vehicle_type], s=12,
                    edgecolor='white', linewidth=0.5, zorder=5
                )

        # 关键修改3：按反转后的时段顺序构建统计对比对，匹配终端输出与图像
        pairs = []
        for p in period_order_reversed:
            for i in range(len(VEHICLE_ORDER)):
                for j in range(i + 1, len(VEHICLE_ORDER)):
                    pairs.append(((p, VEHICLE_ORDER[i]), (p, VEHICLE_ORDER[j])))

        # 添加统计注释（原始参数，保持显著性标识间距不变）
        annotator = Annotator(
            ax, pairs, data=data,
            x=x_var, y="period", hue="vehicle_type",
            order=period_order_reversed,  # 关键修改4：使用反转后的顺序，匹配Y轴视觉
            hue_order=VEHICLE_ORDER, orient="h", dodge=hue_dodge
        )

        # 配置统计注释（原始参数）
        annotator.configure(
            test="Mann-Whitney",
            text_format="star",
            loc='inside',
            fontsize=18
        )
        annotator.apply_and_annotate()

        # 格式化坐标轴（原始样式）
        ax.set_yticks(y_positions)
        ax.set_yticklabels(period_order_reversed)  # 匹配反转后的时段顺序
        ax.set_xlabel(x_label, labelpad=10)
        ax.set_ylabel(None)
        ax.xaxis.grid(True, linestyle='--', alpha=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        if ax.get_legend():
            ax.get_legend().remove()

        # 设置x轴是否从0开始
        if start_from_zero:
            ax.set_xlim(left=0)

    # 辅助函数：绘制公平性子图（针对性优化，补充横轴刻度，修复错位问题）
    def plot_optimized_fairness_chart(ax, data, x_var, x_label, start_from_zero=False):
        """绘制公平性子图，优化重叠问题，补充横轴刻度标注，修复错位问题"""
        # 关键修改1：使用反转后的时段顺序生成Y轴坐标
        y_positions = np.arange(len(period_order_reversed))
        group_width = 0.8  # 与前3个子图保持一致的组宽度
        hue_dodge = group_width / len(VEHICLE_ORDER) * 1.1  # 适度放大间距，解决重叠

        # 关键修改2：直接遍历反转后的时段顺序，无需reversed()
        for y_pos, period in zip(y_positions, period_order_reversed):
            for i, vehicle_type in enumerate(VEHICLE_ORDER):
                # 简化center_y计算，与Annotator的dodge参数对齐
                center_y = y_pos + (i - (len(VEHICLE_ORDER) - 1) / 2) * hue_dodge
                # 筛选对应数据
                data_series = data[(data['period'] == period) & (data['vehicle_type'] == vehicle_type)][x_var].dropna()
                if data_series.empty:
                    print(f"警告：{period} - {vehicle_type} 无{x_var}数据，跳过绘图")
                    continue

                # 绘制小提琴图（适度缩小宽度，增加透明度，解决重叠）
                violin_parts = ax.violinplot(
                    data_series, positions=[center_y], widths=0.25, vert=False,
                    showmeans=False, showmedians=False, showextrema=False
                )
                body = violin_parts['bodies'][0]
                body.set_facecolor(light_color_map[vehicle_type])
                body.set_edgecolor(color_map[vehicle_type])
                body.set_linewidth(1)
                body.set_alpha(0.7)  # 透明化，减少视觉拥挤

                # 绘制箱线图（适度缩小宽度，层级置顶）
                bp = ax.boxplot(
                    data_series, positions=[center_y], widths=0.12, vert=False,
                    patch_artist=True, showfliers=False, zorder=3
                )
                plt.setp(bp['boxes'], facecolor=light_color_map[vehicle_type], edgecolor='black', linewidth=1)
                plt.setp(bp['medians'], color='black', linewidth=2, zorder=4)
                plt.setp(bp['whiskers'], color=color_map[vehicle_type], linewidth=1)
                plt.setp(bp['caps'], color=color_map[vehicle_type], linewidth=1)

                # 绘制散点（固定随机种子保证一致性）
                def sample_points_without_outliers(series, n_points=15):
                    """移除离群值后采样（固定随机种子）"""
                    Q1 = series.quantile(0.25)
                    Q3 = series.quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR
                    non_outliers = series[(series >= lower_bound) & (series <= upper_bound)]
                    if len(non_outliers) < n_points:
                        return non_outliers
                    # 固定采样种子RANDOM_SEED
                    return non_outliers.sample(n=n_points, random_state=RANDOM_SEED)

                sampled_series = sample_points_without_outliers(data_series, n_points=15)
                # 固定抖动种子，使用独立随机数生成器
                rng = np.random.default_rng(seed=RANDOM_SEED)
                y_jit = rng.normal(center_y, 0.01, size=len(sampled_series))
                ax.scatter(
                    sampled_series, y_jit, color=color_map[vehicle_type], s=10,
                    edgecolor='white', linewidth=0.5, zorder=5
                )

        # 关键修改3：按反转后的时段顺序构建统计对比对
        pairs = []
        for p in period_order_reversed:
            for i in range(len(VEHICLE_ORDER)):
                for j in range(i + 1, len(VEHICLE_ORDER)):
                    pairs.append(((p, VEHICLE_ORDER[i]), (p, VEHICLE_ORDER[j])))

        # 统计注释（优化参数，避免重叠）
        annotator = Annotator(
            ax, pairs, data=data,
            x=x_var, y="period", hue="vehicle_type",
            order=period_order_reversed,  # 关键修改4：使用反转后的顺序，匹配Y轴视觉
            hue_order=VEHICLE_ORDER, orient="h", dodge=hue_dodge
        )
        annotator.configure(
            test="Mann-Whitney",
            text_format="star",
            loc='inside',
            fontsize=16,
            line_height=0.05,
            text_offset=0.01,
        )
        annotator.apply_and_annotate()

        # 格式化坐标轴
        ax.set_yticks(y_positions)
        ax.set_yticklabels(period_order_reversed)  # 匹配反转后的时段顺序
        ax.set_xlabel(x_label, labelpad=10)
        ax.set_ylabel(None)
        ax.xaxis.grid(True, linestyle='--', alpha=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        if ax.get_legend():
            ax.get_legend().remove()
        if start_from_zero:
            ax.set_xlim(left=0)

        # 关键：显式设置横轴刻度，标注0.25、0.5、0.75
        ax.set_xlim(0.25, 0.75)  # 固定横轴范围
        ax.set_xticks([0.25, 0.5, 0.75])  # 显式添加指定刻度
        ax.set_xticklabels(['0.25', '0.5', '0.75'])  # 标注刻度文字

    # 绘制前3个行程数据子图（保留原始样式，已修复错位）
    plot_original_chart(axes[0], df, 'duration_min', 'Travel time (min)', start_from_zero=True)
    axes[0].set_xlim(0, 80)

    plot_original_chart(axes[1], df, 'distance_km', 'Travel distance (km)', start_from_zero=True)
    axes[1].set_xlim(0, 60)

    plot_original_chart(axes[2], df, 'speed_kmh', 'Speed (km/h)', start_from_zero=True)
    axes[2].set_xlim(0, 100)

    # 绘制第4个公平性子图（优化后，已修复错位）
    plot_optimized_fairness_chart(axes[3], fairness_df, 'fairness', 'Fairness Index', start_from_zero=True)

    # 统一Y轴标签
    fig.text(0.03, 0.5, 'Time Period', va='center', rotation='vertical', size=24)

    # 创建统一的图例（3类数据）
    handles = [
        plt.Line2D([0], [0], color=color_map['AV'], lw=6, label='Robotaxis'),
        plt.Line2D([0], [0], color=color_map['Human-driven (electric)'], lw=6, label='HVs (electric vehicle)'),
        plt.Line2D([0], [0], color=color_map['Human-driven (other)'], lw=6, label='HVs (ICE vehicle)')
    ]
    fig.legend(handles=handles, loc='upper center',
               ncol=3, bbox_to_anchor=(0.5, 0.99), frameon=False)

    # 调整布局参数，保留原始间距
    plt.tight_layout(pad=1.5, rect=[0.05, 0, 1, 0.96])
    plt.subplots_adjust(hspace=0.3, wspace=0.9)
    plt.savefig('travel_stats_with_fairness_3types_final.svg', format='svg', bbox_inches='tight')
    plt.savefig('travel_stats_with_fairness_3types_final.pdf', format='pdf', bbox_inches='tight')
    plt.show()


# 运行主函数
if __name__ == '__main__':
    plot_box_with_stats()
