import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

IN_CSV = "cci_grid_linear_grid.csv"
OUT_DIR = "output"
os.makedirs(OUT_DIR, exist_ok=True)

df = pd.read_csv(IN_CSV)
cci_col = "cci_max" if "cci_max" in df.columns else "cci"
vals = df[cci_col].astype(float).replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
n = vals.size

# Freedman–Diaconis bins
q25, q75 = np.quantile(vals, [0.25, 0.75])
iqr = max(q75 - q25, 1e-12)
bin_width = 2 * iqr * (n ** (-1/3))
bins = int(np.clip((vals.max() - vals.min()) / bin_width, 18, 60)) if np.isfinite(bin_width) and bin_width > 0 else 30

# Quantiles
q_levels = np.array([0.10, 0.25, 0.50, 0.75, 0.90])
q_values = np.quantile(vals, q_levels)

# KDE
x_grid = np.linspace(vals.min(), vals.max(), 400)
kde = gaussian_kde(vals)
kde_y = kde(x_grid)

# ECDF
x_sorted = np.sort(vals)
y_ecdf = np.arange(1, n + 1) / n

# Nature-like styling
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "axes.linewidth": 0.8,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "axes.labelsize": 9,
    "axes.titlesize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
})

fig = plt.figure(figsize=(7.2, 5.4))
gs = fig.add_gridspec(2, 1, height_ratios=[1.15, 0.85], hspace=0.28)

# a) histogram + KDE
ax1 = fig.add_subplot(gs[0, 0])
ax1.hist(vals, bins=bins, density=True, edgecolor="black", linewidth=0.6, alpha=0.30)
ax1.plot(x_grid, kde_y, linewidth=1.4)
for qv in q_values:
    ax1.axvline(qv, linestyle="--", linewidth=0.9)
ax1.text(q_values[2], ax1.get_ylim()[1] * 0.95, "median", ha="center", va="top", fontsize=8)
ax1.set_ylabel("Density")
ax1.set_title("CCI distribution across grid cells", pad=6)
ax1.text(-0.03, 1.02, "a", transform=ax1.transAxes, fontweight="bold", fontsize=11, va="bottom")

# b) ECDF
ax2 = fig.add_subplot(gs[1, 0])
ax2.plot(x_sorted, y_ecdf, linewidth=1.3)
ax2.scatter(q_values, q_levels, s=18, zorder=3)
for ql, qv in zip(q_levels, q_values):
    ax2.hlines(ql, vals.min(), qv, linestyles=":", linewidth=0.8)
    ax2.vlines(qv, 0, ql, linestyles=":", linewidth=0.8)
ax2.set_xlabel("CCI")
ax2.set_ylabel("Cumulative probability")
ax2.set_ylim(0, 1)
ax2.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
ax2.text(-0.03, 1.02, "b", transform=ax2.transAxes, fontweight="bold", fontsize=11, va="bottom")

for ax in (ax1, ax2):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

fig.text(0.01, 0.01, f"N={n:,} grid cells; quantiles shown: 10, 25, 50, 75, 90%", fontsize=8)

fig.savefig(os.path.join(OUT_DIR, "Fig_CCI_distribution.png"), dpi=600, bbox_inches="tight")
fig.savefig(os.path.join(OUT_DIR, "Fig_CCI_distribution.pdf"), bbox_inches="tight")
plt.close(fig)
