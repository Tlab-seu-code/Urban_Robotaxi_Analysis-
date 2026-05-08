# -*- coding: utf-8 -*-
"""
figure_d.py (HIST ONLY, ALGORITHM UNCHANGED)

Input (unchanged):
- ./hv_av_trips_sne_filtered.csv
  required columns: mode (HV/AV or HV/Robotaxi), SNE_mean, dist_km

Output (only one figure):
- hv_av_sne_hist.png

IMPORTANT:
- The histogram algorithm is IDENTICAL to your original:
  sns.histplot(x=SNE_mean, hue=mode, weights=dist_km, bins=60, stat="density",
               common_norm=False, element="step", alpha=0.45, ...)
- Only figure texts are updated to label the plotted object as OPCI.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats


# =========================
# I/O (unchanged)
# =========================
INPUT_CSV = r"./hv_av_trips_sne_filtered.csv"
OUT_FIG = "hv_av_sne_hist.png"

# =========================
# Columns (unchanged)
# =========================
MODE_COL = "mode"
SNE_COL = "SNE_mean"
DIST_COL = "dist_km"

# =========================
# Style (Nature-style, consistent with figure5b)
# =========================
def set_nature_style():
    plt.rcParams.update({
        "font.family": "Arial",
        "font.size": 13,
        "axes.labelsize": 13,
        "axes.titlesize": 13,
        "legend.fontsize": 13,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.unicode_minus": False,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 3,
        "ytick.major.size": 3,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "lines.linewidth": 1.6,
        "savefig.dpi": 600,
        "savefig.bbox": "tight",
        "savefig.transparent": True,
        "savefig.pad_inches": 0.05,
        "figure.dpi": 600,
    })

COLOR_MAP = {"HV": "#1f77b4", "Robotaxi": "#ff7f0e"}


def _fmt_p(p: float) -> str:
    if p is None or (isinstance(p, float) and (np.isnan(p) or np.isinf(p))):
        return "NA"
    if p < 1e-4:
        return f"{p:.1e}"
    return f"{p:.4f}"


def _fmt_f(x: float, nd: int = 3) -> str:
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
        return "NA"
    return f"{x:.{nd}f}"


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    valid = (~values.isna()) & (~weights.isna()) & (weights > 0)
    if not valid.any():
        return np.nan
    return (values[valid] * weights[valid]).sum() / weights[valid].sum()


def compute_tests(df: pd.DataFrame, col: str) -> dict:
    sub = df[[MODE_COL, col]].copy()
    sub[col] = sub[col].replace([np.inf, -np.inf], np.nan)

    hv = sub.loc[sub[MODE_COL] == "HV", col].dropna().values
    rx = sub.loc[sub[MODE_COL] == "Robotaxi", col].dropna().values

    if len(hv) < 2 or len(rx) < 2:
        return {"t_p": np.nan, "cohen_d": np.nan}

    # Welch t-test
    _, t_p = stats.ttest_ind(rx, hv, equal_var=False, nan_policy="omit")

    # Cohen's d (Robotaxi - HV)
    s1 = np.std(rx, ddof=1)
    s2 = np.std(hv, ddof=1)
    n1, n2 = len(rx), len(hv)
    sp = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
    d = (np.mean(rx) - np.mean(hv)) / sp if sp > 0 else np.nan

    return {"t_p": float(t_p), "cohen_d": float(d)}


def add_inplot_box(ax, lines, anchor=(0.02, 0.98), fontsize=10):
    ax.text(
        anchor[0], anchor[1], "\n".join(lines),
        transform=ax.transAxes,
        va="top", ha="left",
        fontsize=fontsize,
        family="Arial",
        bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="0.75", alpha=0.85),
    )


def main():
    if not os.path.exists(INPUT_CSV):
        raise FileNotFoundError(f"Input not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)

    missing = {MODE_COL, SNE_COL, DIST_COL} - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    # Mode normalization (text only; does not change any algorithmic intent)
    df[MODE_COL] = df[MODE_COL].astype(str)
    df.loc[df[MODE_COL].str.upper().eq("AV"), MODE_COL] = "Robotaxi"
    df.loc[df[MODE_COL].str.lower().eq("robotaxi"), MODE_COL] = "Robotaxi"

    # Numeric cleaning (same intent as original)
    df[SNE_COL] = pd.to_numeric(df[SNE_COL], errors="coerce").replace([np.inf, -np.inf], np.nan)
    df[DIST_COL] = pd.to_numeric(df[DIST_COL], errors="coerce").replace([np.inf, -np.inf], np.nan)

    # =========================
    # HIST (ALGORITHM UNCHANGED)
    # =========================
    df_hist = df[[SNE_COL, MODE_COL, DIST_COL]].copy()
    df_hist = df_hist.dropna(subset=[SNE_COL, DIST_COL, MODE_COL])
    df_hist["w_km"] = df_hist[DIST_COL].clip(lower=0)

    # Stats for the annotation box (does not affect histogram)
    hv_n = int((df_hist[MODE_COL] == "HV").sum())
    rx_n = int((df_hist[MODE_COL] == "Robotaxi").sum())
    hv_wmean = weighted_mean(df_hist.loc[df_hist[MODE_COL] == "HV", SNE_COL],
                             df_hist.loc[df_hist[MODE_COL] == "HV", "w_km"])
    rx_wmean = weighted_mean(df_hist.loc[df_hist[MODE_COL] == "Robotaxi", SNE_COL],
                             df_hist.loc[df_hist[MODE_COL] == "Robotaxi", "w_km"])
    tests = compute_tests(df_hist.rename(columns={"w_km": DIST_COL}), SNE_COL)  # identical test basis

    # Apply Nature style (consistent with figure5b)
    set_nature_style()
    
    fig, ax = plt.subplots(figsize=(6.8, 3.4))

    # --- DO NOT CHANGE THESE histplot PARAMETERS ---
    sns.histplot(
        data=df_hist,
        x=SNE_COL,
        hue=MODE_COL,
        weights="w_km",
        bins=60,
        stat="density",
        common_norm=False,
        element="step",
        alpha=0.45,
        palette=COLOR_MAP,
        legend=True,
        ax=ax
    )
    # ----------------------------------------------

    # Text-only updates: label the plotted object as OPCI (a per-operational-km complexity distribution)
    ax.set_title("Operational-Path Complexity Index", pad=4)
    ax.set_xlabel("OPCI value")
    ax.set_ylabel("Operational-km Density")
    ax.yaxis.grid(True, color="0.85", linewidth=0.5)
    ax.xaxis.grid(False)

    # 修改图例：移除标题并设置字体
    legend = ax.get_legend()
    if legend:
        legend.set_title('')  # 移除 "mode" 标题
        for text in legend.get_texts():
            text.set_fontsize(11)  # 图例文字字号与figure5b一致（+1）
    
    # Align axes to start from 0
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    
    # 合并xy轴零点标签：隐藏x轴的0刻度标签，只保留y轴的
    xticks = ax.get_xticks()
    xticklabels = ['' if t == 0 else ax.xaxis.get_major_formatter()(t) for t in xticks]
    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels)

    add_inplot_box(
        ax,
        lines=[
            "OPCI: per-kilometre complexity distribution",
            f"Δweighted_mean={_fmt_f(rx_wmean - hv_wmean, 4)}",
            f"Cohen's d={_fmt_f(tests['cohen_d'], 3)}",
            f"Welch p={_fmt_p(tests['t_p'])}",
        ],
        anchor=(0.02, 0.98),
        fontsize=9
    )

    # 使用与figure5b一致的保存设置
    fig.savefig(OUT_FIG, dpi=600, bbox_inches='tight', pad_inches=0.05)
    fig.savefig(OUT_FIG.replace(".png", ".pdf"), dpi=600, bbox_inches='tight', pad_inches=0.05, format='pdf')
    plt.close(fig)
    print(f"[OK] Saved: {OUT_FIG}")
    print(f"[OK] Saved: {OUT_FIG.replace('.png', '.pdf')}")


if __name__ == "__main__":
    main()
