"""CCI distribution figure (Nature-sub-journal style).

Reads grid-level CCI values and outputs a publication-ready figure.

Input / output convention (kept consistent with your original script):
  - IN_CSV: cci_grid_linear_grid.csv
  - OUT_DIR: output/
  - Outputs: output/Fig_CCI_distribution_combined.{png,pdf} (combined mode)
             output/Fig_CCI_distribution.{png,pdf} (two_panel mode)

Latest tweaks requested (2025-12-23):
1) Remove the in-figure note moved to subtitle (i.e., do not show N / quantile note anywhere).
2) Put the percentile dashed lines to the back (lower z-order) to avoid covering bars/curves/labels.

Dependencies: numpy, pandas, matplotlib, scipy
"""

from __future__ import annotations

import os
from typing import Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
from scipy.stats import gaussian_kde


# -----------------------------
# User-configurable I/O
# -----------------------------
IN_CSV = "cci_grid_linear_grid.csv"  # keep the original filename convention
OUT_DIR = "output"

# "combined": histogram+KDE (left y) + ECDF (right y) in one panel
# "two_panel": legacy layout (a: hist+KDE, b: ECDF)
PLOT_MODE = "combined"


def _apply_nature_style() -> None:
    """Minimal styling closer to Nature sub-journal figures."""
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "axes.linewidth": 0.9,
            "xtick.major.width": 0.9,
            "ytick.major.width": 0.9,
            "xtick.major.size": 3,
            "ytick.major.size": 3,
            "axes.labelsize": 10,
            "axes.titlesize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 14,
        }
    )


def _load_cci_values(csv_path: str) -> Tuple[np.ndarray, str]:
    """Load and clean CCI values. Returns (values, used_column_name)."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"Input file not found: {csv_path}\n"
            "Please put the file next to this script, or update IN_CSV accordingly."
        )

    df = pd.read_csv(csv_path)
    cci_col = "cci_max" if "cci_max" in df.columns else ("cci" if "cci" in df.columns else None)
    if cci_col is None:
        raise ValueError("Cannot find a CCI column. Expected 'cci_max' or 'cci'.")

    vals = (
        df[cci_col]
        .astype(float)
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
        .to_numpy()
    )
    if vals.size < 10:
        raise ValueError(f"Too few valid CCI values after cleaning (n={vals.size}).")
    return vals, cci_col


def _freedman_diaconis_bins(x: np.ndarray) -> int:
    """Bin count via Freedman–Diaconis rule, clipped to a sensible range."""
    n = x.size
    q25, q75 = np.quantile(x, [0.25, 0.75])
    iqr = max(q75 - q25, 1e-12)
    bin_width = 2 * iqr * (n ** (-1 / 3))
    if not np.isfinite(bin_width) or bin_width <= 0:
        return 30
    bins = int(np.clip((x.max() - x.min()) / bin_width, 18, 60))
    return max(bins, 5)


def plot_combined(vals: np.ndarray) -> plt.Figure:
    """Single-panel: histogram+KDE + ECDF with top percentile ticks."""
    n = vals.size
    bins = _freedman_diaconis_bins(vals)

    # Quantiles
    q_levels = np.array([0.10, 0.25, 0.50, 0.75, 0.90])
    q_labels = ["P10", "P25", "P50", "P75", "P90"]
    q_values = np.quantile(vals, q_levels)

    # KDE
    x_grid = np.linspace(vals.min(), vals.max(), 500)
    kde = gaussian_kde(vals)
    kde_y = kde(x_grid)
    kde_qy = kde(q_values)

    # ECDF
    x_sorted = np.sort(vals)
    y_ecdf = np.arange(1, n + 1) / n

    # Palette (distinct but restrained)
    col_hist = "#A6CEE3"  # light blue fill
    col_edge = "#4D4D4D"  # neutral grey border
    col_kde = "#D95F02"   # warm orange
    col_ecdf = "#1F78B4"  # deep blue
    col_qline = "#7F7F7F"  # grey (percentile vlines)
    col_guide = "#BDBDBD"  # light grey (guide lines)

    fig, ax = plt.subplots(figsize=(7.2, 5.2))

    # Make axis patches transparent to avoid any twin-axes covering artifacts
    ax.set_zorder(2)
    ax.patch.set_alpha(0)

    # Histogram (unified border appearance)
    _, _, patches = ax.hist(
        vals,
        bins=bins,
        density=True,
        color=col_hist,
        edgecolor=col_edge,
        linewidth=0.7,
        zorder=1.0,
    )
    for p in patches:
        p.set_alpha(0.45)  # face transparency
        p.set_edgecolor((0.302, 0.302, 0.302, 0.85))  # consistent border alpha
        p.set_linewidth(0.7)
        p.set_zorder(1.0)

    # Percentile dashed vlines (push to background)
    for qv in q_values:
        ax.axvline(
            qv,
            linestyle="--",
            linewidth=1.0,
            color=col_qline,
            alpha=0.85,
            zorder=0.2,   # <-- below bars/curves/labels
        )

    # KDE (on top)
    ax.plot(x_grid, kde_y, color=col_kde, linewidth=1.8, label="KDE", zorder=3.0)
    ax.scatter(
        q_values, kde_qy,
        s=28, color=col_kde, edgecolor="white", linewidth=0.6,
        zorder=4.0,
    )

    ax.set_xlabel("CCI")
    ax.set_ylabel("Density")

    # ECDF on the right axis
    ax_r = ax.twinx()
    ax_r.set_zorder(1)
    ax_r.patch.set_alpha(0)

    ax_r.plot(x_sorted, y_ecdf, color=col_ecdf, linewidth=1.8, label="ECDF", zorder=3.0)
    ax_r.scatter(q_values, q_levels, s=34, color=col_ecdf, zorder=4.0)

    # Guide lines (also to background)
    for ql, qv in zip(q_levels, q_values):
        ax_r.hlines(
            ql, vals.min(), qv,
            linestyles=":", linewidth=0.9, color=col_guide,
            zorder=0.2,
        )
        ax_r.vlines(
            qv, 0, ql,
            linestyles=":", linewidth=0.9, color=col_guide,
            zorder=0.2,
        )

    ax_r.set_ylabel("Cumulative probability")
    ax_r.set_ylim(0, 1)
    ax_r.set_yticks([0, 0.25, 0.50, 0.75, 1.00])
    ax_r.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))

    # Top axis: percentile labels
    ax_top = ax.twiny()
    ax_top.set_xlim(ax.get_xlim())
    ax_top.set_xticks(q_values)
    ax_top.set_xticklabels(q_labels)
    ax_top.set_xlabel("Percentile")
    ax_top.tick_params(axis="x", pad=2)

    # Title only (no subtitle / note)
    fig.suptitle("CCI distribution across grid cells", y=0.88)

    # Legend: merge handles from both axes
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax_r.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False)

    ax.spines["top"].set_visible(False)
    ax_r.spines["top"].set_visible(False)

    # Panel label (if you embed this as panel b later)
    ax.text(-0.06, 1.02, "b", transform=ax.transAxes, fontweight="bold", fontsize=12, va="bottom")

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    return fig


def plot_two_panel(vals: np.ndarray) -> plt.Figure:
    """Legacy two-panel: (a) histogram+KDE, (b) ECDF."""
    bins = _freedman_diaconis_bins(vals)

    q_levels = np.array([0.10, 0.25, 0.50, 0.75, 0.90])
    q_values = np.quantile(vals, q_levels)

    x_grid = np.linspace(vals.min(), vals.max(), 500)
    kde = gaussian_kde(vals)
    kde_y = kde(x_grid)
    kde_qy = kde(q_values)

    x_sorted = np.sort(vals)
    y_ecdf = np.arange(1, len(vals) + 1) / len(vals)

    col_hist = "#A6CEE3"
    col_edge = "#4D4D4D"
    col_kde = "#D95F02"
    col_ecdf = "#1F78B4"
    col_qline = "#7F7F7F"
    col_guide = "#BDBDBD"

    fig = plt.figure(figsize=(7.2, 5.4))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.15, 0.85], hspace=0.28)

    ax1 = fig.add_subplot(gs[0, 0])
    _, _, patches = ax1.hist(
        vals,
        bins=bins,
        density=True,
        color=col_hist,
        edgecolor=col_edge,
        linewidth=0.7,
        zorder=1.0,
    )
    for p in patches:
        p.set_alpha(0.45)
        p.set_edgecolor((0.302, 0.302, 0.302, 0.85))
        p.set_linewidth(0.7)
        p.set_zorder(1.0)

    for qv in q_values:
        ax1.axvline(qv, linestyle="--", linewidth=1.0, color=col_qline, alpha=0.85, zorder=0.2)

    ax1.plot(x_grid, kde_y, color=col_kde, linewidth=1.8, zorder=3.0)
    ax1.scatter(q_values, kde_qy, s=28, color=col_kde, edgecolor="white", linewidth=0.6, zorder=4.0)
    ax1.set_ylabel("Density")
    ax1.set_title("CCI distribution across grid cells", pad=6)
    ax1.text(-0.03, 1.02, "a", transform=ax1.transAxes, fontweight="bold", fontsize=12, va="bottom")

    ax2 = fig.add_subplot(gs[1, 0])
    ax2.plot(x_sorted, y_ecdf, color=col_ecdf, linewidth=1.8, zorder=3.0)
    ax2.scatter(q_values, q_levels, s=34, color=col_ecdf, zorder=4.0)

    for ql, qv in zip(q_levels, q_values):
        ax2.hlines(ql, vals.min(), qv, linestyles=":", linewidth=0.9, color=col_guide, zorder=0.2)
        ax2.vlines(qv, 0, ql, linestyles=":", linewidth=0.9, color=col_guide, zorder=0.2)

    ax2.set_xlabel("CCI")
    ax2.set_ylabel("Cumulative probability")
    ax2.set_ylim(0, 1)
    ax2.set_yticks([0, 0.25, 0.50, 0.75, 1.00])
    ax2.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    ax2.text(-0.03, 1.02, "b", transform=ax2.transAxes, fontweight="bold", fontsize=12, va="bottom")

    for ax in (ax1, ax2):
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.tight_layout()
    return fig


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    _apply_nature_style()

    vals, used_col = _load_cci_values(IN_CSV)

    if PLOT_MODE.lower().strip() == "combined":
        fig = plot_combined(vals)
        base = "Fig_CCI_distribution_combined"
    else:
        fig = plot_two_panel(vals)
        base = "Fig_CCI_distribution"

    out_png = os.path.join(OUT_DIR, f"{base}.png")
    out_pdf = os.path.join(OUT_DIR, f"{base}.pdf")
    fig.savefig(out_png, dpi=600, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)

    print(f"[OK] Saved: {out_png}")
    print(f"[OK] Saved: {out_pdf}")
    print(f"[Info] Used column: {used_col}; n={vals.size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
