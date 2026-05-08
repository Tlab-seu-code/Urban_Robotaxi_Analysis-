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
x_grid = np.linspace(vals.min(), vals.max(), 500)
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
    "legend.fontsize": 8,
})

fig, ax = plt.subplots(figsize=(7.2, 4.6))

# --- Left axis: histogram + KDE ---
hist = ax.hist(
    vals, bins=bins, density=True,
    edgecolor="black", linewidth=0.6, alpha=0.25, label="Histogram"
)
kde_line, = ax.plot(x_grid, kde_y, linewidth=1.5, label="KDE")

ax.set_xlabel("CCI")
ax.set_ylabel("Density")
ax.set_title("CCI distribution across grid cells", pad=8)

# --- Right axis: ECDF ---
axr = ax.twinx()
ecdf_line, = axr.plot(x_sorted, y_ecdf, linewidth=1.4, label="ECDF")
axr.set_ylabel("Cumulative probability")
axr.set_ylim(0, 1)
axr.set_yticks([0, 0.25, 0.5, 0.75, 1.0])

# Quantile markers on ECDF
axr.scatter(q_values, q_levels, s=22, zorder=5, label="Quantiles (ECDF)")

# --- Quantile guide lines (lighter, behind text) ---
# vertical lines: draw on main ax so they align with shared x
for qv in q_values:
    ax.axvline(qv, linestyle="--", linewidth=0.9, alpha=0.55, zorder=1)

# optional L-shape guides on ECDF axis (dotted, very light)
xmin = vals.min()
for ql, qv in zip(q_levels, q_values):
    axr.hlines(ql, xmin, qv, linestyles=":", linewidth=0.8, alpha=0.45, zorder=2)
    axr.vlines(qv, 0, ql, linestyles=":", linewidth=0.8, alpha=0.45, zorder=2)

# --- Top x-axis: percentile labels (P10/P25/P50/P75/P90) ---
axt = ax.twiny()
axt.set_xlim(ax.get_xlim())
axt.set_xticks(q_values)
axt.set_xticklabels([f"P{int(p*100)}" for p in q_levels])
axt.set_xlabel("Percentile", labelpad=6)

# Make sure top labels won't visually clash
axt.tick_params(axis="x", pad=3, length=3, width=0.8)

# Clean spines (keep right & top because twinx/twiny need them)
ax.spines["top"].set_visible(False)  # use axt's top spine instead
ax.spines["right"].set_visible(False)  # right spine from axr

# Panel label like Nature
ax.text(-0.03, 1.02, "a", transform=ax.transAxes, fontweight="bold", fontsize=11, va="bottom")

# Combined legend (from both axes)
handles = [kde_line, ecdf_line]
labels = ["KDE (density)", "ECDF (cumulative)"]
ax.legend(handles, labels, loc="upper left", frameon=False)

fig.text(0.01, 0.01, f"N={n:,} grid cells; top ticks indicate P10/P25/P50/P75/P90", fontsize=8)

fig.savefig(os.path.join(OUT_DIR, "Fig_CCI_distribution_combined.png"), dpi=600, bbox_inches="tight")
fig.savefig(os.path.join(OUT_DIR, "Fig_CCI_distribution_combined.pdf"), bbox_inches="tight")
plt.close(fig)
