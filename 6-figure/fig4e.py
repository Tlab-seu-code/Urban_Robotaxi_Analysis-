import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from math import sqrt

# === 文件名 ===
BASE_CSV = "vehicle_stats_detail_av_electricity_hourly_all.csv"
OPT_CSV  = "vehicle_stats_detail_av_electricity_hourly_allR.csv"

# === 读入与列规范化（确保列名是 '0'..'23' 的字符串） ===
def read_hour_table(path):
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    cols = [str(i) for i in range(24)]
    # 只保留 0..23 列，并按顺序排列
    df = df[[c for c in cols if c in df.columns]].copy()
    # 转数值
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

orig_df = read_hour_table(BASE_CSV)
opt_df  = read_hour_table(OPT_CSV)

# === t 分布临界值（若 scipy 可用则用 t.ppf，否则退化为 1.96） ===
try:
    from scipy.stats import t
    def tcrit(n): return t.ppf(0.975, n-1) if n > 1 else np.nan
except Exception:
    def tcrit(n): return 1.96 if n > 1 else np.nan

# === 计算均值与 95% CI（按列=小时） ===
def mean_ci_by_hour(df):
    hours = [str(i) for i in range(24)]
    mu = []; lo = []; hi = []; nlist = []
    for h in hours:
        vals = df[h].dropna().to_numpy(float)
        n = len(vals); nlist.append(n)
        if n == 0:
            mu.append(np.nan); lo.append(np.nan); hi.append(np.nan)
            continue
        m = float(np.mean(vals))
        if n > 1:
            s = float(np.std(vals, ddof=1))
            half = tcrit(n) * s / sqrt(n) if s > 0 else 0.0
        else:
            half = 0.0
        mu.append(m); lo.append(m - half); hi.append(m + half)
    return np.array(mu), np.array(lo), np.array(hi), np.array(nlist)

orig_mu, orig_lo, orig_hi, orig_n = mean_ci_by_hour(orig_df)
opt_mu,  opt_lo,  opt_hi,  opt_n  = mean_ci_by_hour(opt_df)

# === 计算提升百分比：(opt - orig) / orig * 100（逐行成对、逐小时） ===
# 若两表行数不同，按最小行数对齐；若 orig==0 则该样本为 NaN
min_rows = min(len(orig_df), len(opt_df))
if min_rows == 0:
    raise ValueError("输入数据为空：请检查 CSV 是否包含行。")

orig_sub = orig_df.iloc[:min_rows].reset_index(drop=True)
opt_sub  = opt_df.iloc[:min_rows].reset_index(drop=True)

improve_df = pd.DataFrame(index=range(min_rows), columns=[str(i) for i in range(24)], dtype=float)
for h in range(24):
    col = str(h)
    o = orig_sub[col].to_numpy(float)
    r = opt_sub[col].to_numpy(float)
    with np.errstate(divide='ignore', invalid='ignore'):
        imp = abs((r - o)) / o * 100.0
        imp[~np.isfinite(imp)] = np.nan  # 处理 orig 为 0 的情况（inf/-inf）为 NaN
    improve_df[col] = imp

imp_mu, imp_lo, imp_hi, imp_n = mean_ci_by_hour(improve_df)

# === 作图 ===
x = np.arange(24)
hours_label = [str(i) for i in range(24)]

plt.rcParams.update({
    'font.family': 'Arial',
    'font.size': 19,
    'axes.labelsize': 17,
    'xtick.labelsize': 17,
    'ytick.labelsize': 17,
    'axes.linewidth': 0.7,
})

fig, ax1 = plt.subplots(figsize=(12, 4.2), dpi=300)  # 主轴：原始/优化（kWh）- 压缩宽度
ax2 = ax1.twinx()                                   # 次轴：百分比（%）

# 颜色
c_orig = "#FF7F6E"   # 原始
c_opt  = "#5AA7D9"   # 优化
c_imp  = "#4CAF50"   # 提升百分比

# 1) 折线处改为接收句柄
line_orig, = ax1.plot(x, orig_mu, marker='o', ms=3.5, lw=1.2, color=c_orig, label='Original (mean)')
line_opt,  = ax1.plot(x, opt_mu,  marker='o', ms=3.5, lw=1.2, color=c_opt,  label='Optimized (mean)')
line_imp,  = ax2.plot(x, imp_mu,  marker='^', ms=3.5, lw=1.2, color=c_imp,  label='Improvement (mean)')
# 折线代码之后，补回阴影，且放在折线下方
ax1.fill_between(x, orig_lo, orig_hi, color=c_orig, alpha=0.25, linewidth=0,
                 zorder=line_orig.get_zorder()-1)
ax1.fill_between(x, opt_lo,  opt_hi,  color=c_opt,  alpha=0.25, linewidth=0,
                 zorder=line_opt.get_zorder()-1)
ax2.fill_between(x, imp_lo,  imp_hi,  color=c_imp,  alpha=0.25, linewidth=0,
                 zorder=line_imp.get_zorder()-1)
print(imp_mu)

# 坐标轴与网格
# 替换原来的小时标签定义，并应用到 X 轴刻度
x = np.arange(24)
hours_label = [f"{i}:00" for i in range(24)]

ax1.set_xlim(-0.5, 23.5)
ax1.set_xticks(x[::2])  # 每隔一个小时标注
ax1.set_xticklabels(hours_label[::2])
ax1.set_xlabel("Hour of day")
ax1.set_ylabel("Electricity per hour (kWh)")
# ax1.grid(True, axis='y', linestyle='--', alpha=0.35)

ax2.set_ylabel("Improvement (%)")

# ax2.yaxis.set_major_formatter(PercentFormatter(decimals=0))

# # 图例（合并两轴）
# lines1, labels1 = ax1.get_legend_handles_labels()
# lines2, labels2 = ax2.get_legend_handles_labels()
# ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper center', ncol=2, frameon=False)
# 3) 新建只含三条折线、并排的图例
# ax1.legend(
#     [line_orig, line_opt, line_imp],
#     ['Robotaxi total on the road', 'Minimum fleet total on the road', 'Improvement'],
#     loc='upper center', ncol=3, frameon=False
# )
from matplotlib.lines import Line2D
# 注释/删除原来的 ax1.legend(...)
legend_lines = [
    Line2D([0], [0], color=c_orig, lw=2.0, marker='o', ms=6),
    Line2D([0], [0], color=c_opt,  lw=2.0, marker='o', ms=6),
    Line2D([0], [0], color=c_imp,  lw=2.0, marker='^', ms=7),  # 百分比用三角形
]
ax1.legend(
    legend_lines,
    ['Robotaxi volume', 'Minimum fleet volume', 'Improvement'],
    loc='upper center', ncol=3, frameon=False,
    handlelength=2.6, handletextpad=0.6, borderaxespad=0.2,
    fontsize=18.5  # 图例字号比全局字号小2（17-2=15）
)
# 在设置右轴格式后，新增这两行：
ax2.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
ax1.set_ylim(0, 1400)

plt.tight_layout()
ax1.spines['top'].set_visible(False)
ax2.spines['top'].set_visible(False)
# 去掉百分号，右轴范围 0–100，并用整数刻度
ax2.set_ylim(0, 100)
from matplotlib.ticker import StrMethodFormatter, MaxNLocator, FixedLocator
ax2.yaxis.set_major_locator(FixedLocator([0, 20, 40, 60, 80]))
ax2.yaxis.set_major_formatter(StrMethodFormatter('{x:.0f}'))
plt.savefig("hourly_original_optimized_and_improvement_with_CI.svg", format="svg", bbox_inches="tight")
plt.savefig("hourly_original_optimized_and_improvement_with_CI.pdf", format="pdf", bbox_inches="tight")
plt.show()
