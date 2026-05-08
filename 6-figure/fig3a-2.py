import os
import warnings
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import statsmodels.api as sm

warnings.filterwarnings("ignore")

# =========================
# Output
# =========================
OUT_DIR = os.path.join("output", "ch3_sne")
os.makedirs(OUT_DIR, exist_ok=True)

OUT_PNG = os.path.join(OUT_DIR, "AV_HV_15_dualaxis_POP_vs_CTX.png")

# =========================
# Raw order files
# =========================
AV_ORDER_FILE = "v4-av.csv"      # AV orders
HV_ORDER_FILE = "v10-hdv.csv"    # HV orders

# Column names
AV_LON_COL, AV_LAT_COL = "起点经度", "起点纬度"
HV_LON_COL, HV_LAT_COL = "start_lon", "start_lat"

# =========================
# Fixed Wuhan grid definition
# =========================
LON_MIN, LON_MAX = 113.942617, 114.629031
LAT_MIN, LAT_MAX = 30.255898, 30.742468
DX = 0.0103997242944
DY = 0.0089831117499

# =========================
# 15-point series
# =========================
AV_15 = {
    "orders": None,
    "bin_label": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"],
}

HV_15 = {
    "orders": None,
    "bin_label": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"],
}

# Percentile positions for 15 bins
CCI_PCTL_POINTS = np.linspace(1 / 16, 14 / 16, 14)

# =========================
# Data sources
# =========================
POP_CSV = "wuhan_population_grid.csv"
SNE_CSV = "wuhan_grid_sne_2.csv"
POI_CSV = "grid_poi_share_long.csv"
CCI_CANDIDATES = ["cci_grid_linear_grid.csv", "process_grid_metro_cci_ring.csv", "process_grid_bus_cci_ring.csv"]

# Keep your existing bins for feature aggregation
CUTS_15 = [0, 0.063, 0.125, 0.188, 0.250, 0.313, 0.375, 0.438, 0.500, 0.563, 0.625, 0.688, 0.750, 0.813, 0.875, 1.01]

# Modeling switches
EPS = 1e-9
ROBOTAXI_USE_LOG_Y = True
HV_USE_LOG_Y = False


def set_nature_style():
    plt.rcParams.update({
        "font.family": "Arial",
        "font.size": 10,

        "axes.labelsize": 10,
        "axes.titlesize": 11,
        "legend.fontsize": 9,

        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,

        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 3,
        "ytick.major.size": 3,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,

        "lines.linewidth": 1.4,
        "savefig.dpi": 600,
        "savefig.bbox": "tight",
        "savefig.transparent": True,
    })


def pick_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _find_first_existing_file(candidates: List[str]) -> str:
    """Locate the first existing file among candidates in common subfolders."""
    search_dirs = [
        ".",  # current working directory
        os.path.dirname(os.path.abspath(__file__)),  # script directory
        os.path.join(".", "process"),
        os.path.join(".", "output"),
    ]
    for d in search_dirs:
        for fn in candidates:
            fp = os.path.join(d, fn)
            if os.path.exists(fp):
                return fp
    return ""


def _apply_sci_yaxis(ax: plt.Axes, axis_color: str) -> None:
    """Use a consistent scientific-notation formatter (×10^n) for a y-axis."""
    fmt = mticker.ScalarFormatter(useMathText=True)
    fmt.set_scientific(True)
    fmt.set_powerlimits((0, 0))  # force sci for all magnitudes
    ax.yaxis.set_major_formatter(fmt)
    ax.yaxis.get_offset_text().set_color(axis_color)
    ax.yaxis.get_offset_text().set_size(11)


def _ensure_cci_01(s: pd.Series) -> Tuple[pd.Series, str]:
    """
    Ensure CCI in [0,1]. Returns (series_01, note).
    Accepts columns that might be [0,1] already or [0,100] percentile.
    """
    s = s.astype(float)
    s_clean = s.replace([np.inf, -np.inf], np.nan)
    mx = float(s_clean.dropna().max()) if s_clean.dropna().shape[0] else np.nan

    if np.isfinite(mx) and mx > 1.2:
        return (s_clean / 100.0).clip(0, 1), "CCI normalized by /100"
    return s_clean.clip(0, 1), "CCI already in [0,1]"


# =========================
# Observed order counting
# =========================
def get_grid_id(lon: np.ndarray, lat: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Vectorized lon/lat -> (grid_x, grid_y).
    Must match orders.py:
        gx = floor((lon - LON_MIN) / DX)
        gy = floor((lat - LAT_MIN) / DY)
        then clipped.
    """
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)

    gx = np.floor((lon - LON_MIN) / DX).astype(int)
    gy = np.floor((lat - LAT_MIN) / DY).astype(int)

    gx_max = int(np.ceil((LON_MAX - LON_MIN) / DX))
    gy_max = int(np.ceil((LAT_MAX - LAT_MIN) / DY))

    gx = np.clip(gx, 0, gx_max)
    gy = np.clip(gy, 0, gy_max)
    return gx, gy


def load_cci_and_quantiles(cci_file: str) -> Tuple[Dict[Tuple[int, int], float], np.ndarray]:
    """
    Load CCI grid file and compute CCI quantile thresholds for 14 percentile bins,
    following orders.py logic.

    Returns:
        grid_cci: {(grid_x,grid_y)->cci_value},
        q_values: 13 quantile thresholds in CCI-value space.
    """
    ext = os.path.splitext(cci_file)[1].lower()
    if ext in [".xlsx", ".xls"]:
        cci_df = pd.read_excel(cci_file)
    else:
        cci_df = pd.read_csv(cci_file)

    if {"grid_lon", "grid_lat"}.issubset(cci_df.columns):
        cci_df = cci_df[
            (cci_df["grid_lon"] >= LON_MIN) & (cci_df["grid_lon"] <= LON_MAX) &
            (cci_df["grid_lat"] >= LAT_MIN) & (cci_df["grid_lat"] <= LAT_MAX)
        ].copy()

    cx = pick_col(cci_df, ["grid_x", "x", "gx"])
    cy = pick_col(cci_df, ["grid_y", "y", "gy"])
    cci_col = pick_col(cci_df, ["cci_max", "CCI", "cci", "cci_value"])
    if cx is None or cy is None or cci_col is None:
        raise ValueError(f"CCI file must contain grid_x/grid_y and a CCI column. Got columns: {list(cci_df.columns)}")

    cci_df = cci_df[[cx, cy, cci_col]].copy()
    cci_df.columns = ["grid_x", "grid_y", "cci_raw"]
    cci_df["cci"], _ = _ensure_cci_01(cci_df["cci_raw"])

    grid_cci: Dict[Tuple[int, int], float] = {}
    for _, row in cci_df.iterrows():
        gx, gy = int(row["grid_x"]), int(row["grid_y"])
        grid_cci[(gx, gy)] = float(row["cci"])

    valid_cci = np.array([v for v in grid_cci.values() if np.isfinite(v) and v > 0], dtype=float)
    if valid_cci.size == 0:
        q_values = np.zeros(len(CCI_PCTL_POINTS), dtype=float)
    else:
        q_values = np.quantile(valid_cci, CCI_PCTL_POINTS)

    return grid_cci, q_values


def read_order_grid_counts(
    csv_path: str,
    lon_col: str,
    lat_col: str,
    chunk_size: int = 200_000,
) -> Dict[Tuple[int, int], int]:
    """
    Read order file in chunks and aggregate counts per (grid_x, grid_y).
    Filters to Wuhan lon/lat bounds before mapping, consistent with orders.py.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Order file not found: {csv_path}")

    # validate columns early
    header = pd.read_csv(csv_path, nrows=0)
    missing = [c for c in [lon_col, lat_col] if c not in header.columns]
    if missing:
        raise ValueError(
            f"Missing columns {missing} in {csv_path}. Available columns include: {list(header.columns)[:30]}"
        )

    counts: Dict[Tuple[int, int], int] = defaultdict(int)

    usecols = [lon_col, lat_col]
    for chunk in pd.read_csv(csv_path, usecols=usecols, chunksize=chunk_size):
        chunk = chunk.dropna(subset=usecols)
        if chunk.empty:
            continue

        chunk = chunk[
            (chunk[lon_col] >= LON_MIN) & (chunk[lon_col] <= LON_MAX) &
            (chunk[lat_col] >= LAT_MIN) & (chunk[lat_col] <= LAT_MAX)
        ]
        if chunk.empty:
            continue

        gx, gy = get_grid_id(chunk[lon_col].to_numpy(), chunk[lat_col].to_numpy())
        uniq, cnt = np.unique(np.vstack([gx, gy]), axis=1, return_counts=True)
        for (xx, yy), cc in zip(uniq.T, cnt):
            counts[(int(xx), int(yy))] += int(cc)

    return counts


def bin_orders_to_15_intervals(
    grid_counts: Dict[Tuple[int, int], int],
    grid_cci: Dict[Tuple[int, int], float],
    q_values: np.ndarray,
) -> np.ndarray:
    """
    Aggregate grid-level order counts into 15 CCI-quantile intervals.

    Interval logic matches orders.py:
        (-inf, q0], (q0, q1], ..., (q13, +inf]
    Implemented as:
        idx = searchsorted(q_values, cci, side='left')
    """
    q = np.asarray(q_values, dtype=float)
    out = np.zeros(15, dtype=np.int64)

    for (gx, gy), n in grid_counts.items():
        cci = grid_cci.get((gx, gy), None)
        if cci is None or not np.isfinite(cci):
            continue
        idx = int(np.searchsorted(q, float(cci), side="left"))  # 0..14
        if idx < 0:
            idx = 0
        elif idx > 14:
            idx = 14
        out[idx] += int(n)

    return out


def compute_observed_orders_15(
    av_csv: str,
    hv_csv: str,
    cci_file: str,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute observed AV/HV orders per 15 CCI percentile bins.
    """
    grid_cci, q_values = load_cci_and_quantiles(cci_file)

    av_grid_counts = read_order_grid_counts(av_csv, lon_col=AV_LON_COL, lat_col=AV_LAT_COL)
    hv_grid_counts = read_order_grid_counts(hv_csv, lon_col=HV_LON_COL, lat_col=HV_LAT_COL)

    av_orders_15 = bin_orders_to_15_intervals(av_grid_counts, grid_cci, q_values)
    hv_orders_15 = bin_orders_to_15_intervals(hv_grid_counts, grid_cci, q_values)

    return av_orders_15, hv_orders_15


# =========================
# Grid features
# =========================
def load_grid_features_15bins(cuts: List[float]) -> pd.DataFrame:
    """
    Merge grid features then aggregate into the same percentile bins as the 15-point series.
    NOTE: This part keeps your previous binning logic unchanged (uses CUTS_15 directly).
    """

    # --- Population ---
    pop = pd.read_csv(POP_CSV)
    kx = pick_col(pop, ["grid_x", "x", "gx"])
    ky = pick_col(pop, ["grid_y", "y", "gy"])
    pop_col = pick_col(pop, ["population", "pop", "POP", "pop_count", "pop_cnt"])
    if kx is None or ky is None or pop_col is None:
        raise ValueError("Population file must contain grid_x/grid_y and a population column.")
    pop = pop[[kx, ky, pop_col]].copy()
    pop.columns = ["grid_x", "grid_y", "population"]

    # --- SNE (optional) ---
    sne = pd.read_csv(SNE_CSV)
    sx = pick_col(sne, ["grid_x", "x", "gx"])
    sy = pick_col(sne, ["grid_y", "y", "gy"])
    sne_col = pick_col(sne, ["SNE", "sne", "SNE_mean", "sne_mean", "SNE_norm"])
    if sx is None or sy is None or sne_col is None:
        sne = pd.DataFrame(columns=["grid_x", "grid_y", "SNE"])
    else:
        sne = sne[[sx, sy, sne_col]].copy()
        sne.columns = ["grid_x", "grid_y", "SNE"]

    # --- POI ---
    poi = pd.read_csv(POI_CSV)
    px = pick_col(poi, ["grid_x", "x", "gx"])
    py = pick_col(poi, ["grid_y", "y", "gy"])
    total_col = pick_col(poi, ["grid_total_count", "total_count", "poi_total", "poi_count", "count"])
    if px is None or py is None:
        raise ValueError("POI file must contain grid_x/grid_y.")
    if total_col is None:
        numeric_cols = [c for c in poi.columns if pd.api.types.is_numeric_dtype(poi[c])]
        if not numeric_cols:
            poi2 = pd.DataFrame({"grid_x": poi[px], "grid_y": poi[py], "poi": 0.0})
        else:
            poi2 = poi[[px, py] + numeric_cols].copy()
            poi2["poi"] = poi2[numeric_cols].sum(axis=1)
            poi2 = poi2.groupby([px, py], as_index=False)["poi"].sum()
            poi2.columns = ["grid_x", "grid_y", "poi"]
        poi = poi2
    else:
        poi = poi.groupby([px, py], as_index=False)[total_col].max()
        poi.columns = ["grid_x", "grid_y", "poi"]

    # --- CCI ---
    cci_file = _find_first_existing_file(CCI_CANDIDATES)
    if not cci_file:
        raise FileNotFoundError(
            f"No CCI file found. Expected one of: {CCI_CANDIDATES} (searched: ., script dir, ./process, ./output)"
        )

    ext = os.path.splitext(cci_file)[1].lower()
    if ext in [".xlsx", ".xls"]:
        cci = pd.read_excel(cci_file)
    else:
        cci = pd.read_csv(cci_file)

    cx = pick_col(cci, ["grid_x", "x", "gx"])
    cy = pick_col(cci, ["grid_y", "y", "gy"])
    cci_col = pick_col(cci, ["cci_max", "CCI", "cci", "cci_value"])
    if cx is None or cy is None or cci_col is None:
        raise ValueError(f"CCI file {cci_file} must contain grid_x/grid_y and CCI column.")
    cci = cci[[cx, cy, cci_col]].copy()
    cci.columns = ["grid_x", "grid_y", "cci_raw"]
    cci["cci"], _ = _ensure_cci_01(cci["cci_raw"])

    # --- Merge ---
    merged = cci.merge(pop, on=["grid_x", "grid_y"], how="left") \
                .merge(sne, on=["grid_x", "grid_y"], how="left") \
                .merge(poi, on=["grid_x", "grid_y"], how="left")

    merged["population"] = merged["population"].fillna(0.0)
    merged["poi"] = merged["poi"].fillna(0.0)

    # Bin by CCI
    merged["bin"] = pd.cut(merged["cci"], bins=cuts, labels=False, include_lowest=True)

    # Aggregate to bins
    agg = merged.groupby("bin", dropna=False).agg(
        population=("population", "sum"),
        poi_sum=("poi", "sum"),
        n_grids=("cci", "size"),
        cci=("cci", "mean"),
    ).reindex(range(len(cuts) - 1))

    agg = agg.fillna({
        "population": 0.0,
        "poi_sum": 0.0,
        "n_grids": 0.0,
        "cci": float(merged["cci"].mean()) if np.isfinite(merged["cci"].mean()) else 0.0
    })

    # POI density per grid
    agg["poi_density"] = agg.apply(
        lambda r: float(r["poi_sum"]) / float(r["n_grids"]) if float(r["n_grids"]) > 0 else 0.0,
        axis=1
    )

    feat = agg.reset_index(drop=True)

    # Normalize features used in models
    pop_max = float(feat["population"].max())
    feat["pop_norm"] = (feat["population"] / pop_max) * 10.0 if pop_max > 0 else 0.0
    feat["pop_norm2"] = feat["pop_norm"] ** 2

    cci_max = float(feat["cci"].max())
    feat["cci_norm"] = (feat["cci"] / cci_max) if cci_max > 0 else 0.0

    poi_max = float(feat["poi_density"].max())
    feat["poi_norm"] = (feat["poi_density"] / poi_max) if poi_max > 0 else 0.0

    return feat


def fit_ols_predict(y: np.ndarray, X: np.ndarray, use_log: bool) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    Xc = sm.add_constant(X, has_constant="add")

    if use_log:
        y_fit = np.log(np.clip(y, EPS, None))
        model = sm.OLS(y_fit, Xc).fit()
        pred_log = model.predict(Xc)
        return np.exp(pred_log)
    else:
        model = sm.OLS(y, Xc).fit()
        return model.predict(Xc)


def plot_dual_axis_one_figure(
    x_labels: List[str],
    hv_obs: np.ndarray,
    robotaxi_obs: np.ndarray,
    hv_pred_pop: np.ndarray,
    hv_pred_ctx: np.ndarray,
    robotaxi_pred_pop: np.ndarray,
    robotaxi_pred_ctx: np.ndarray,
    out_png: str,
):
    """
    One panel, dual y-axis:
    - HV on left (blue): points + POP (dashed) + CTX baseline (solid)
    - Robotaxi on right (orange): points + POP (dashed) + CTX baseline (solid)
    - Legend used to identify curves (no on-line labels)
    - Statistics box on the left side showing R² and correlation coefficients
    """

    def calc_stats(y_true, y_pred):
        """Calculate R² and Pearson correlation coefficient"""
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)

        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan

        if len(y_true) >= 2:
            from scipy.stats import pearsonr
            r, p = pearsonr(y_true, y_pred)
        else:
            r, p = np.nan, np.nan

        return r2, r, p

    set_nature_style()

    # palette
    C_HV = "#2C4E75"     # deep blue
    C_ROBO = "#C2572D"   # warm orange
    C_HV_L = "#8FB3D9"   # light blue baseline
    C_ROBO_L = "#E3A07D" # light orange baseline

    x = np.arange(len(x_labels))

    fig, ax_hv = plt.subplots(figsize=(6.6, 3.3))
    ax_robo = ax_hv.twinx()

    # Observations
    ax_hv.scatter(
        x, hv_obs, s=26, facecolors="white", edgecolors=C_HV, linewidths=0.9,
        zorder=6, label="HV observed"
    )
    ax_robo.scatter(
        x, robotaxi_obs, s=26, facecolors="white", edgecolors=C_ROBO, linewidths=0.9,
        zorder=6, label="Robotaxi observed"
    )

    # Curves
    ax_hv.plot(
        x, hv_pred_pop, color=C_HV_L, linestyle="--", linewidth=1.6, zorder=2,
        label="HV (POP)"
    )
    ax_hv.plot(
        x, hv_pred_ctx, color=C_HV, linestyle="-", linewidth=2.2, zorder=3,
        label="HV (CTX)"
    )

    ax_robo.plot(
        x, robotaxi_pred_pop, color=C_ROBO_L, linestyle="--", linewidth=1.6, zorder=2,
        label="Robotaxi (POP)"
    )
    ax_robo.plot(
        x, robotaxi_pred_ctx, color=C_ROBO, linestyle="-", linewidth=2.2, zorder=3,
        label="Robotaxi (CTX)"
    )

    # Axis formatting
    ax_hv.set_xticks(x)
    ax_hv.set_xticklabels(x_labels, rotation=0, ha="center")
    ax_hv.set_xlabel("CCI percentile bins")
    ax_hv.set_ylabel("HV orders", color=C_HV)
    ax_robo.set_ylabel("Robotaxi orders", color=C_ROBO)

    # Background grid lines (horizontal only)
    ax_hv.yaxis.grid(True, color="0.85", linewidth=0.5)
    ax_hv.xaxis.grid(False)

    ax_hv.tick_params(axis="y", colors=C_HV)
    ax_robo.tick_params(axis="y", colors=C_ROBO)

    # Ensure right y-axis spine is visible
    ax_robo.spines["right"].set_visible(True)
    ax_robo.spines["right"].set_linewidth(0.8)
    ax_robo.spines["right"].set_color(C_ROBO)

    # Unified y-axis number formatting
    _apply_sci_yaxis(ax_hv, axis_color=C_HV)
    _apply_sci_yaxis(ax_robo, axis_color=C_ROBO)

    ax_hv.yaxis.set_major_locator(mticker.MaxNLocator(4))
    ax_robo.yaxis.set_major_locator(mticker.MaxNLocator(4))

    ax_hv.set_title("Robotaxi vs HV | POP vs CTX", pad=4)

    # Legend
    h1, l1 = ax_hv.get_legend_handles_labels()
    h2, l2 = ax_robo.get_legend_handles_labels()
    ax_hv.legend(
        h1 + h2, l1 + l2,
        frameon=False, loc="upper left", ncol=2,
        handlelength=2.6, columnspacing=1.2, borderaxespad=0.2
    )

    # Statistics
    r2_hv_pop, r_hv_pop, _ = calc_stats(hv_obs, hv_pred_pop)
    r2_hv_ctx, r_hv_ctx, _ = calc_stats(hv_obs, hv_pred_ctx)
    r2_robo_pop, r_robo_pop, _ = calc_stats(robotaxi_obs, robotaxi_pred_pop)
    r2_robo_ctx, r_robo_ctx, _ = calc_stats(robotaxi_obs, robotaxi_pred_ctx)

    stats_text = [
        "R²={:.3f}, r={:.3f} (HV-POP)".format(r2_hv_pop, r_hv_pop),
        "R²={:.3f}, r={:.3f} (HV-CTX)".format(r2_hv_ctx, r_hv_ctx),
        "R²={:.3f}, r={:.3f} (Robotaxi-POP)".format(r2_robo_pop, r_robo_pop),
        "R²={:.3f}, r={:.3f} (Robotaxi-CTX)".format(r2_robo_ctx, r_robo_ctx),
    ]

    ax_hv.text(
        0.02, 0.58,
        "\n".join(stats_text),
        transform=ax_hv.transAxes,
        ha="left",
        va="top",
        fontsize=7.5,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="0.75", alpha=0.85)
    )

    fig.savefig(out_png)
    fig.savefig(out_png.replace(".png", ".pdf"))
    plt.close(fig)


def main():
    # locate required files (same-folder default + common subfolders)
    av_csv = _find_first_existing_file([AV_ORDER_FILE])
    hv_csv = _find_first_existing_file([HV_ORDER_FILE])
    cci_csv = _find_first_existing_file(CCI_CANDIDATES)

    if not av_csv:
        raise FileNotFoundError(f"Cannot find {AV_ORDER_FILE} in current/script/process/output folders.")
    if not hv_csv:
        raise FileNotFoundError(f"Cannot find {HV_ORDER_FILE} in current/script/process/output folders.")
    if not cci_csv:
        raise FileNotFoundError(f"Cannot find CCI file. Expected one of: {CCI_CANDIDATES}")

    # 1) Compute observed orders and fill AV_15/HV_15
    av_orders_15, hv_orders_15 = compute_observed_orders_15(
        av_csv=av_csv,
        hv_csv=hv_csv,
        cci_file=cci_csv,
    )
    AV_15["orders"] = av_orders_15.astype(int).tolist()
    HV_15["orders"] = hv_orders_15.astype(int).tolist()

    # 2) Build the two 15-point series
    df_av = pd.DataFrame(AV_15)
    df_hv = pd.DataFrame(HV_15)

    # 3) Load & aggregate grid features to the same 15 bins (unchanged logic)
    feat = load_grid_features_15bins(CUTS_15)

    # 4) Prepare design matrices for POP and CTX baseline
    X_pop = feat[["pop_norm", "pop_norm2"]].values.astype(float)
    X_ctx = feat[["pop_norm", "pop_norm2", "cci_norm", "poi_norm"]].values.astype(float)

    # 5) Fit & predict for HV
    hv_y = df_hv["orders"].values.astype(float)
    hv_pred_pop = fit_ols_predict(hv_y, X_pop, use_log=HV_USE_LOG_Y)
    hv_pred_ctx = fit_ols_predict(hv_y, X_ctx, use_log=HV_USE_LOG_Y)

    # 6) Fit & predict for Robotaxi (AV)
    robo_y = df_av["orders"].values.astype(float)
    robo_pred_pop = fit_ols_predict(robo_y, X_pop, use_log=ROBOTAXI_USE_LOG_Y)
    robo_pred_ctx = fit_ols_predict(robo_y, X_ctx, use_log=ROBOTAXI_USE_LOG_Y)

    # 7) Plot one figure only
    plot_dual_axis_one_figure(
        x_labels=df_av["bin_label"].tolist(),
        hv_obs=hv_y,
        robotaxi_obs=robo_y,
        hv_pred_pop=hv_pred_pop,
        hv_pred_ctx=hv_pred_ctx,
        robotaxi_pred_pop=robo_pred_pop,
        robotaxi_pred_ctx=robo_pred_ctx,
        out_png=OUT_PNG
    )

    print("[Done] Saved:")
    print(" -", os.path.abspath(OUT_PNG))
    print(" -", os.path.abspath(OUT_PNG.replace(".png", ".pdf")))

    print("\n[Observed orders by CCI percentile bins]")
    print("AV:", AV_15["orders"])
    print("HV:", HV_15["orders"])


if __name__ == "__main__":
    main()
