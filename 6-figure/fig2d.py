import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from statannotations.Annotator import Annotator
import numpy as np
import warnings

warnings.filterwarnings('ignore')

# ---------------- 核心参数定义 ----------------
# 颜色定义（修改为指定的灰色系 #D3D0D9 和 #50555B）
AV_COLOR = '#50555B'  # Robotaxi-type A order 颜色（深灰蓝调）
HV_COLOR = '#D3D0D9'  # HV-type A order 颜色（浅灰紫调）

# 数据文件路径
DATA_PATH = r"F:\Research_Group\City_Grading\0927data\metro_bus_a_category_analysis_data.xlsx"

# 绘图样式配置
plt.rcParams.update({
    'font.family': 'Calibri',
    'font.size': 28,  # 14×2
    'axes.labelsize': 28,
    'axes.titlesize': 32,  # 16×2
    'xtick.labelsize': 24,
    'ytick.labelsize': 24,
    'legend.fontsize': 24,
    'legend.title_fontsize': 24,
    'axes.linewidth': 1,
    'lines.linewidth': 1,
    'xtick.major.width': 1,
    'ytick.major.width': 1,
    'xtick.major.size': 4,
    'ytick.major.size': 4
})

# 名称映射（仅用于展示）
NAME_MAPPING = {
    'AV-A': 'Robotaxi-type A order',
    'HV-A': 'HV-type A order'
}


# ---------------- 数据预处理函数 ----------------
def load_and_preprocess_data(file_path):
    """加载并预处理数据"""
    # 读取Excel文件
    df = pd.read_excel(file_path)

    # 检查必要列是否存在（使用原始列名）
    required_cols = ['Time', 'HV-A (Metro)', 'AV-A (Bus)', 'AV-A (Metro)', 'HV-A (Bus)']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"缺失必要列：{missing_cols}")

    # 数据清洗
    df = df.dropna(subset=required_cols)
    df['Time'] = df['Time'].astype(int)
    df = df[(df['Time'] >= 0) & (df['Time'] <= 23)]  # 确保时间在0-23范围内

    # 重塑数据格式（长格式）
    data_list = []
    # Metro数据
    data_list.append(pd.DataFrame({
        'value': df['HV-A (Metro)'],
        'type': 'HV-A',  # 内部仍用原始名称
        'transport': 'Metro',
        'Time': df['Time']
    }))
    data_list.append(pd.DataFrame({
        'value': df['AV-A (Metro)'],
        'type': 'AV-A',  # 内部仍用原始名称
        'transport': 'Metro',
        'Time': df['Time']
    }))
    # Bus数据
    data_list.append(pd.DataFrame({
        'value': df['HV-A (Bus)'],
        'type': 'HV-A',  # 内部仍用原始名称
        'transport': 'Bus',
        'Time': df['Time']
    }))
    data_list.append(pd.DataFrame({
        'value': df['AV-A (Bus)'],
        'type': 'AV-A',  # 内部仍用原始名称
        'transport': 'Bus',
        'Time': df['Time']
    }))

    # 合并数据
    plot_df = pd.concat(data_list, ignore_index=True)
    plot_df = plot_df.dropna(subset=['value'])

    # 确保分类顺序（内部仍用原始名称）
    plot_df['transport'] = pd.Categorical(plot_df['transport'], categories=['Metro', 'Bus'], ordered=True)
    plot_df['type'] = pd.Categorical(plot_df['type'], categories=['HV-A', 'AV-A'], ordered=True)

    print(f"数据加载完成：")
    print(f"- 总样本数：{len(plot_df)}")
    print(f"- Metro样本：{len(plot_df[plot_df['transport'] == 'Metro'])}")
    print(f"- Bus样本：{len(plot_df[plot_df['transport'] == 'Bus'])}")
    print(f"- {NAME_MAPPING['HV-A']}样本：{len(plot_df[plot_df['type'] == 'HV-A'])}")
    print(f"- {NAME_MAPPING['AV-A']}样本：{len(plot_df[plot_df['type'] == 'AV-A'])}")

    return plot_df


# ---------------- 核心绘图函数（双 Y 轴版） ----------------
def plot_metro_bus_raincloud():
    """绘制Metro和Bus的云雨图（交换XY轴，使用双Y轴）"""
    # 加载数据
    df = load_and_preprocess_data(DATA_PATH)

    # ========== 修复：初始化统计量存储字典（改用元组作为键） ==========
    stats_values = {}  # 存储均值、中位数、方差

    # 创建画布与左侧主坐标轴（AV-A 刻度）
    fig = plt.figure(figsize=(12, 10))
    fig.suptitle('Category analysis between metro and bus', fontsize=36, y=0.98)
    ax = fig.add_subplot(111)
    ax_right = ax.twinx()  # 右侧坐标轴（HV-A 刻度）

    # 主图：仅保留箱线和雨点图（XY轴交换）
    transport_order = ['Metro', 'Bus']
    type_order = ['HV-A', 'AV-A']  # 内部仍用原始名称
    cmap = {'HV-A': HV_COLOR, 'AV-A': AV_COLOR}
    # 配套的浅色版本（在原颜色基础上提亮/减淡）
    cmap_light = {'HV-A': '#E8E7EB', 'AV-A': '#7A7F86'}

    # ---------- 提前算好缩放/逆映射 ----------
    hv_min, hv_max = 40, 100  # HV 真实区间
    av_min, av_max = 0, 40  # AV 真实区间（也是画布坐标区间）

    def hv2canvas(y):  # HV 真实值 → 画布 0-40
        return (y - hv_min) / (hv_max - hv_min) * 40

    def canvas2hv(y):  # 画布 0-40 → HV 真实值（给右侧轴用）
        return y / 40 * (hv_max - hv_min) + hv_min

    # ---------- 循环绘制箱线和雨点图（XY轴交换） ----------
    for x_pos, transport in enumerate(transport_order):  # 0=Metro, 1=Bus
        for i, type_val in enumerate(type_order):
            # 位置调整：HV 在右，AV 在左
            if type_val == 'HV-A':
                box_x = x_pos + 0.2  # HV-A 箱线位置
            else:
                box_x = x_pos - 0.2  # AV-A 箱线位置

            data_series = df[(df['transport'] == transport) & (df['type'] == type_val)]['value']

            # ========== 修复：使用元组作为键，避免字符串分割问题 ==========
            key = (transport, type_val)
            if data_series.empty:
                stats_values[key] = {'mean': None, 'median': None, 'variance': None}
                continue

            # ========== 新增：计算并存储真实均值、中位数、方差 ==========
            real_mean = data_series.mean()
            real_median = data_series.median()
            real_variance = data_series.var()  # 方差（默认是样本方差，ddof=1）
            # 如果需要总体方差，使用 data_series.var(ddof=0)
            stats_values[key] = {
                'mean': real_mean,
                'median': real_median,
                'variance': real_variance
            }

            # 坐标缩放
            if type_val == 'HV-A':
                data_canvas = hv2canvas(data_series)
            else:
                data_canvas = data_series

            # 绘制箱线图（调宽：从0.12改为0.25，vert=True因为XY交换）
            bp = ax.boxplot(
                data_canvas, positions=[box_x], widths=0.25, vert=True,
                patch_artist=True, showfliers=False
            )
            plt.setp(bp['boxes'], facecolor=cmap_light[type_val], edgecolor='black', linewidth=1, zorder=3)
            plt.setp(bp['medians'], color='black', linewidth=2, zorder=4)
            plt.setp(bp['whiskers'], color=cmap[type_val], linewidth=1, zorder=3)
            plt.setp(bp['caps'], color=cmap[type_val], linewidth=1, zorder=3)

            # 雨点图（XY轴交换，随机抖动在X轴）
            def sample_without_outliers(series, n=50):
                Q1, Q3 = series.quantile([0.25, 0.75])
                IQR = Q3 - Q1
                inside = series[(series >= Q1 - 1.5 * IQR) & (series <= Q3 + 1.5 * IQR)]
                return inside.sample(min(n, len(inside)), random_state=42)

            sampled = sample_without_outliers(data_canvas)
            rain_x = np.random.normal(box_x, 0.02, size=len(sampled))
            ax.scatter(rain_x, sampled, color=cmap[type_val], s=15,
                       edgecolor='w', linewidth=.5, zorder=5, alpha=0.8)

    # ========== 修复&新增：打印四个箱线图的真实统计量（均值、中位数、方差） ==========
    print("\n" + "=" * 80)
    print("四个箱线图的真实统计量（原始值，未缩放）：")
    print("=" * 80)
    # 格式化输出表头
    print(f"{'分组名称':<30} {'均值':<15} {'中位数':<15} {'方差':<15}")
    print("-" * 80)
    for (transport, type_val), stats in stats_values.items():
        display_name = f"{transport} - {NAME_MAPPING[type_val]}"
        if stats['mean'] is not None:
            print(f"{display_name:<30} {stats['mean']:<15.4f} {stats['median']:<15.4f} {stats['variance']:<15.4f}")
        else:
            print(f"{display_name:<30} {'无数据':<15} {'无数据':<15} {'无数据':<15}")
    print("=" * 80 + "\n")

    # ---------- 显著性检验（适配XY轴交换） ----------
    df_test = df.copy()  # 保持原始值
    # 指定要比较的对（内部仍用原始名称）
    pairs = [(('Metro', 'HV-A'), ('Metro', 'AV-A')),
             (('Bus', 'HV-A'), ('Bus', 'AV-A'))]

    # 实例化 Annotator（调整orient为v，x/y交换）
    annotator = Annotator(
        ax, pairs,
        data=df_test,
        y='value', x='transport', hue='type',
        order=transport_order,
        hue_order=type_order,
        orient='v',
        dodge=0.4
    )

    # 配置并标注星号
    annotator.configure(
        test='Mann-Whitney',
        text_format='star',
        loc='inside',
        verbose=0,
        fontsize=28
    )
    annotator.apply_and_annotate()

    # ---------- 坐标轴设置（双Y轴） ----------
    # 横轴（Transport Type）
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['Metro', 'Bus'])
    ax.set_xlabel('Transport Type', labelpad=10)
    ax.set_xlim(-0.5, 1.5)

    # 左侧Y轴（AV-A）- 统一为黑色边框（显示新名称）
    ax.set_ylabel(f'{NAME_MAPPING["AV-A"]} Value', labelpad=10)
    ax.set_ylim(0, 40)
    ax.set_yticks(np.arange(0, 41, 10))
    ax.tick_params(axis='y', colors='black')  # Y轴刻度颜色改为黑色
    ax.spines['left'].set_color('black')  # 左侧边框改为黑色
    ax.spines['bottom'].set_color('black')  # 底部边框改为黑色
    ax.spines['top'].set_color('black')  # 顶部边框改为黑色
    ax.spines['right'].set_color('black')  # 右侧边框改为黑色

    # 右侧Y轴（HV-A）- 统一为黑色边框（显示新名称）
    ax_right.set_ylabel(f'{NAME_MAPPING["HV-A"]} Value', labelpad=10, color='black')  # 标签颜色改为黑色
    ax_right.set_ylim(0, 40)
    hv_ticks = np.arange(40, 101, 15)
    ax_right.set_yticks(hv2canvas(hv_ticks))
    ax_right.set_yticklabels(hv_ticks.astype(int))
    ax_right.tick_params(axis='y', colors='black')  # 右侧Y轴刻度颜色改为黑色
    ax_right.spines['right'].set_color('black')  # 右侧边框改为黑色

    # 图例 - 移到左上角（显示新名称）
    handles = [plt.Line2D([0], [0], color=cmap['HV-A'], lw=6, label=NAME_MAPPING['HV-A']),
               plt.Line2D([0], [0], color=cmap['AV-A'], lw=6, label=NAME_MAPPING['AV-A'])]
    ax.legend(handles=handles, loc='upper left', frameon=False)

    # 调整布局并保存
    plt.tight_layout()
    plt.savefig('metro_bus_boxplot_dual_y.svg', format='svg', bbox_inches='tight')
    plt.savefig('metro_bus_boxplot_dual_y.pdf', format='pdf', bbox_inches='tight')
    plt.savefig('metro_bus_boxplot_dual_y.png', format='png', dpi=300, bbox_inches='tight')
    plt.show()


# ---------------- 主函数执行 ----------------
if __name__ == '__main__':
    plot_metro_bus_raincloud()
