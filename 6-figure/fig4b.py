import os
import warnings
from typing import List, Optional, Tuple, Dict
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import statsmodels.api as sm
from scipy.stats import pearsonr

warnings.filterwarnings("ignore")

# =========================
# Output
# =========================
OUT_DIR = os.path.join("output", "ch3_sne")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PNG = os.path.join(OUT_DIR, "Robotaxi_15_CTX_vs_SNE2.png")

# =========================
# Raw Robotaxi file
# =========================
AV_ORDER_FILE = "v4-av.csv"
AV_LON_COL, AV_LAT_COL = "起点经度", "起点纬度"
ORDER_CHUNK_SIZE = 200_000

# =========================
# Fixed Wuhan grid definition
# =========================
LON_MIN, LON_MAX = 113.942617, 114.629031
LAT_MIN, LAT_MAX = 30.255898, 30.742468
dx = 0.0103997242944
dy = 0.0089831117499

# CCI quantiles
CCI_QUANTILES = np.linspace(1 / 16, 14 / 16, 14)

# =========================
# Robotaxi 15-point series
# =========================
ROBOTAXI_15 = {
    "orders": None,
    "bin_label": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"],
}

CUTS_15 = [0, 0.063, 0.125, 0.188, 0.250, 0.313, 0.375, 0.438, 0.500, 0.563, 0.625, 0.688, 0.750, 0.813, 0.875, 1.01]

MID_CCI_LOW = 0.25
MID_CCI_HIGH = 0.75

# =========================
# Data sources
# =========================
POP_CSV = "wuhan_population_grid.csv"
SNE_CSV = "wuhan_grid_sne_2.csv"
POI_CSV = "grid_poi_share_long.csv"
CCI_CANDIDATES = ["cci_grid_linear_grid.csv", "process_grid_metro_cci_ring.csv", "process_grid_bus_cci_ring.csv"]

# =========================
# Modeling
# =========================
EPS = 1e-9
ROBOTAXI_USE_LOG_Y = True


def set_nature_style():
    plt.rcParams.update({
        "font.family": "Arial",
        "font.size": 14,
        "axes.labelsize": 14,
        "axes.titlesize": 14,
        "legend.fontsize": 14,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
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


def pick_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _ensure_cci_01(s: pd.Series) -> Tuple[pd.Series, str]:
    """
    Safety: if CCI is in [0,100] percentile-like scale, normalize by /100.
    (orders.py uses raw, but this normalization only triggers if max>1.2)
    """
    s = s.astype(float)
    s_clean = s.replace([np.inf, -np.inf], np.nan)
    mx = float(s_clean.dropna().max()) if s_clean.dropna().shape[0] else np.nan
    if np.isfinite(mx) and mx > 1.2:
        return (s_clean / 100.0).clip(0, 1), "CCI normalized by /100"
    return s_clean, "CCI kept as-is"


def _find_first_existing_file(candidates: List[str]) -> str:
    search_dirs = [
        ".",
        os.path.dirname(os.path.abspath(__file__)),
        os.path.join(".", "process"),
        os.path.join(".", "output"),
    ]
    for d in search_dirs:
        for fn in candidates:
            fp = os.path.join(d, fn)
            if os.path.exists(fp):
                return fp
    return ""


# =========================
# Observed orders
# =========================
def get_grid_id(lon: np.ndarray, lat: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Match orders.py exactly:
        gx = floor((lon - LON_MIN) / dx)
        gy = floor((lat - LAT_MIN) / dy)
        then clip to [0, ceil(range/step)].
    """
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)

    gx = np.floor((lon - LON_MIN) / dx).astype(int)
    gy = np.floor((lat - LAT_MIN) / dy).astype(int)

    gx = np.clip(gx, 0, int(np.ceil((LON_MAX - LON_MIN) / dx)))
    gy = np.clip(gy, 0, int(np.ceil((LAT_MAX - LAT_MIN) / dy)))
    return gx, gy


def load_cci_quantile_values(cci_file_path: str) -> Tuple[Dict[Tuple[int, int], float], np.ndarray]:
    """
    Match orders.py:
      - filter by lon/lat bounds if grid_lon/grid_lat exist
      - cci column: 'cci_max' if present else 'cci'
      - valid_cci: values > 0
      - quantile_values = np.quantile(valid_cci, CCI_QUANTILES)
    """
    ext = os.path.splitext(cci_file_path)[1].lower()
    if ext in [".xlsx", ".xls"]:
        cci_df = pd.read_excel(cci_file_path)
    else:
        cci_df = pd.read_csv(cci_file_path)

    if {"grid_lon", "grid_lat"}.issubset(cci_df.columns):
        cci_df = cci_df[
            (cci_df["grid_lon"] >= LON_MIN) & (cci_df["grid_lon"] <= LON_MAX) &
            (cci_df["grid_lat"] >= LAT_MIN) & (cci_df["grid_lat"] <= LAT_MAX)
        ].copy()

    if "grid_x" not in cci_df.columns or "grid_y" not in cci_df.columns:
        # fall back if alternative names exist
        cx = pick_col(cci_df, ["grid_x", "x", "gx"])
        cy = pick_col(cci_df, ["grid_y", "y", "gy"])
        if cx is None or cy is None:
            raise ValueError(f"CCI file must contain grid_x/grid_y. Got columns: {list(cci_df.columns)}")
        cci_df = cci_df.rename(columns={cx: "grid_x", cy: "grid_y"})

    cci_col = "cci_max" if "cci_max" in cci_df.columns else ("cci" if "cci" in cci_df.columns else None)
    if cci_col is None:
        # extra fallback
        cci_col = pick_col(cci_df, ["cci_value", "CCI"])
        if cci_col is None:
            raise ValueError("CCI file must contain one of: cci_max / cci / cci_value / CCI")

    cci_series, _ = _ensure_cci_01(cci_df[cci_col])

    grid_cci: Dict[Tuple[int, int], float] = {}
    for gx, gy, v in zip(cci_df["grid_x"].astype(int).values, cci_df["grid_y"].astype(int).values, cci_series.values):
        if np.isfinite(v):
            grid_cci[(int(gx), int(gy))] = float(v)

    valid_cci = [v for v in grid_cci.values() if v > 0]
    if not valid_cci:
        quantile_values = np.zeros(len(CCI_QUANTILES), dtype=float)
    else:
        quantile_values = np.quantile(np.asarray(valid_cci, dtype=float), CCI_QUANTILES)

    return grid_cci, np.asarray(quantile_values, dtype=float)


def read_robotaxi_grid_counts(csv_path: str, chunk_size: int = ORDER_CHUNK_SIZE) -> Dict[Tuple[int, int], int]:
    """
    Aggregate Robotaxi order counts per (grid_x, grid_y) from v4-av.csv.
    Only uses start lon/lat columns and filters to Wuhan bounds.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Robotaxi file not found: {csv_path}")

    header = pd.read_csv(csv_path, nrows=0)
    missing = [c for c in [AV_LON_COL, AV_LAT_COL] if c not in header.columns]
    if missing:
        raise ValueError(
            f"Missing columns {missing} in {csv_path}. Available columns include: {list(header.columns)[:40]}"
        )

    counts: Dict[Tuple[int, int], int] = defaultdict(int)

    for chunk in pd.read_csv(csv_path, usecols=[AV_LON_COL, AV_LAT_COL], chunksize=chunk_size):
        chunk = chunk.dropna(subset=[AV_LON_COL, AV_LAT_COL])
        if chunk.empty:
            continue

        chunk = chunk[
            (chunk[AV_LON_COL] >= LON_MIN) & (chunk[AV_LON_COL] <= LON_MAX) &
            (chunk[AV_LAT_COL] >= LAT_MIN) & (chunk[AV_LAT_COL] <= LAT_MAX)
        ]
        if chunk.empty:
            continue

        gx, gy = get_grid_id(chunk[AV_LON_COL].to_numpy(), chunk[AV_LAT_COL].to_numpy())

        # fast unique counting via packed keys
        keys = gx.astype(np.int64) * 1_000_000 + gy.astype(np.int64)
        u, c = np.unique(keys, return_counts=True)
        for key, cnt in zip(u, c):
            xx = int(key // 1_000_000)
            yy = int(key % 1_000_000)
            counts[(xx, yy)] += int(cnt)

    return counts


def bin_counts_to_15_by_cci_quantiles(
    grid_counts: Dict[Tuple[int, int], int],
    grid_cci: Dict[Tuple[int, int], float],
    quantile_values: np.ndarray
) -> np.ndarray:
    """
    Match orders.py interval rules:
      intervals = [(-inf, q0], (q0, q1], ..., (q13, +inf]]
      mask: (cci > low) & (cci <= high)
    Equivalent mapping:
      idx = searchsorted(q_values, cci, side="left")  -> 0..14
    """
    q = np.asarray(quantile_values, dtype=float)
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


def compute_robotaxi_orders_15(av_csv: str, cci_file: str) -> np.ndarray:
    grid_cci, q_values = load_cci_quantile_values(cci_file)
    grid_counts = read_robotaxi_grid_counts(av_csv)
    return bin_counts_to_15_by_cci_quantiles(grid_counts, grid_cci, q_values)


# =========================
# Existing plot utilities
# =========================
def bin_midpoints(cuts: List[float]) -> np.ndarray:
    c = np.asarray(cuts, dtype=float)
    return 0.5 * (c[:-1] + c[1:])


def mid_range_indices(cuts: List[float], low: float, high: float) -> List[int]:
    mids = bin_midpoints(cuts)
    return [i for i, m in enumerate(mids) if (m >= low) and (m <= high)]


def load_grid_features_15bins(cuts: List[float]) -> pd.DataFrame:
    # --- Population ---
    pop = pd.read_csv(POP_CSV)
    kx = pick_col(pop, ["grid_x", "x", "gx"])
    ky = pick_col(pop, ["grid_y", "y", "gy"])
    pop_col = pick_col(pop, ["population", "pop", "POP", "pop_count", "pop_cnt"])
    if kx is None or ky is None or pop_col is None:
        raise ValueError("Population file must contain grid_x/grid_y and a population column.")
    pop = pop[[kx, ky, pop_col]].copy()
    pop.columns = ["grid_x", "grid_y", "population"]

    # --- SNE ---
    sne = pd.read_csv(SNE_CSV)
    sx = pick_col(sne, ["grid_x", "x", "gx"])
    sy = pick_col(sne, ["grid_y", "y", "gy"])
    sne_col = pick_col(sne, ["SNE", "sne", "SNE_mean", "sne_mean"])
    if sx is None or sy is None or sne_col is None:
        raise ValueError("SNE file must contain grid_x/grid_y and SNE column (SNE/sne/SNE_mean/sne_mean).")
    sne = sne[[sx, sy, sne_col]].copy()
    sne.columns = ["grid_x", "grid_y", "SNE"]

    # --- POI (for CTX model) ---
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

    # --- CCI (binning + CTX model) ---
    cci_file = _find_first_existing_file(CCI_CANDIDATES)
    if not cci_file:
        raise FileNotFoundError(f"No CCI file found. Expected one of: {CCI_CANDIDATES}")

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
    sne_mean = float(merged["SNE"].dropna().mean()) if merged["SNE"].notna().any() else 0.0
    merged["SNE"] = merged["SNE"].fillna(sne_mean)

    # Bin by CCI
    merged["bin"] = pd.cut(merged["cci"], bins=cuts, labels=False, include_lowest=True)

    # Aggregate by bins
    agg = merged.groupby("bin", dropna=False).agg(
        population=("population", "sum"),
        poi_sum=("poi", "sum"),
        n_grids=("cci", "size"),
        cci=("cci", "mean"),
        SNE=("SNE", "mean"),
    ).reindex(range(len(cuts) - 1))

    agg = agg.fillna({
        "population": 0.0,
        "poi_sum": 0.0,
        "n_grids": 0.0,
        "cci": float(merged["cci"].mean()) if np.isfinite(merged["cci"].mean()) else 0.0,
        "SNE": float(merged["SNE"].mean()) if np.isfinite(merged["SNE"].mean()) else 0.0,
    })

    # POI density
    agg["poi_density"] = agg.apply(
        lambda r: float(r["poi_sum"]) / float(r["n_grids"]) if float(r["n_grids"]) > 0 else 0.0,
        axis=1
    )

    feat = agg.reset_index(drop=True)

    # Pop' scaling
    pop_max = float(feat["population"].max())
    feat["pop_norm"] = (feat["population"] / pop_max) * 10.0 if pop_max > 0 else 0.0
    feat["pop_norm2"] = feat["pop_norm"] ** 2

    # CCI/POI scaling (CTX)
    cci_max = float(feat["cci"].max())
    feat["cci_norm"] = (feat["cci"] / cci_max) if cci_max > 0 else 0.0

    poi_max = float(feat["poi_density"].max())
    feat["poi_norm"] = (feat["poi_density"] / poi_max) if poi_max > 0 else 0.0

    # SNE terms (FOLLOW final.py): SNE and SNE^2 (NOT centered)
    feat["sne"] = feat["SNE"].astype(float)
    feat["sne2"] = feat["SNE"].astype(float) ** 2

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

    model = sm.OLS(y, Xc).fit()
    return model.predict(Xc)


def metrics_r2_r(y_true: np.ndarray, y_pred: np.ndarray) -> Tuple[float, float]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = float(1.0 - ss_res / (ss_tot + EPS))
    r, _ = pearsonr(y_true, y_pred) if len(y_true) >= 2 else (np.nan, np.nan)
    return r2, float(r)


def argmax_in_window(y: np.ndarray, idxs: List[int]) -> int:
    y = np.asarray(y, dtype=float)
    if not idxs:
        return int(np.nanargmax(y))
    sub = y[idxs]
    return int(idxs[int(np.nanargmax(sub))])


def plot_robotaxi_ctx_vs_sne(
    x_labels: List[str],
    y_obs: np.ndarray,
    y_ctx: np.ndarray,
    y_sne: np.ndarray,
    cuts: List[float],
    out_png: str,
):
    set_nature_style()

    # Okabe–Ito palette
    C_OBS = "#000000"   # black
    C_CTX = "#C2572D"   # warm orange (match figure4a Robotaxi CTX)
    C_SNE = "#009E73"   # green
    C_GAP = "#9E9E9E"   # neutral grey

    x = np.arange(len(x_labels))
    fig, ax = plt.subplots(figsize=(6.8, 3.4))

    # Observed points
    ax.scatter(
        x, y_obs,
        s=28, facecolors="white", edgecolors=C_OBS, linewidths=0.9,
        zorder=6, label="Robotaxi observed"
    )

    # Model curves
    ax.plot(x, y_ctx, color=C_CTX, linestyle="-", linewidth=2.2, zorder=3, label="CTX")
    ax.plot(x, y_sne, color=C_SNE, linestyle="-", linewidth=2.0, zorder=2, label="POP + SNE")

    # Difference shading (neutral)
    y_low = np.minimum(y_ctx, y_sne)
    y_high = np.maximum(y_ctx, y_sne)
    ax.fill_between(x, y_low, y_high, color=C_GAP, alpha=0.18, zorder=1, linewidth=0)

    # Mark largest divergence
    gap = np.abs(y_ctx - y_sne)
    j = int(np.nanargmax(gap)) if np.all(np.isfinite(gap)) else 0
    ax.plot([x[j], x[j]], [y_low[j], y_high[j]], color="0.35", linewidth=0.8, zorder=4)
    ax.text(x[j] - 0.15, y_high[j] + 0.05, " max Δ", fontsize=12, color="0.35", va="bottom", ha="right")

    # Axes formatting
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=0, ha="center")
    ax.set_xlabel("CCI percentile bins")
    ax.set_ylabel("Robotaxi orders")

    ax.yaxis.set_major_locator(mticker.MaxNLocator(4))
    ax.yaxis.grid(True, color="0.85", linewidth=0.5)
    ax.xaxis.grid(False)
    
    # Y轴使用科学计数法，乘数显示在轴上方
    formatter = mticker.ScalarFormatter(useMathText=True)
    formatter.set_scientific(True)
    formatter.set_powerlimits((0, 0))
    ax.yaxis.set_major_formatter(formatter)
    ax.yaxis.get_offset_text().set_visible(False)
    # 获取指数并在y轴顶部显示
    ax.figure.canvas.draw()
    offset_text = ax.yaxis.get_offset_text().get_text()
    if offset_text:
        ax.text(0, 1.02, offset_text, transform=ax.transAxes, ha='left', va='bottom', fontsize=12)

    ax.set_title("Robotaxi | CTX  vs POP + SNE", pad=4)

    ax.legend(frameon=False, loc="upper left", ncol=1, handlelength=2.6, borderaxespad=0.2, fontsize=12)

    # Stats box
    r2_ctx, r_ctx = metrics_r2_r(y_obs, y_ctx)
    r2_sne, r_sne = metrics_r2_r(y_obs, y_sne)

    stats_text = [
        f"R²={r2_ctx:.3f}, r={r_ctx:.3f} (CTX)",
        f"R²={r2_sne:.3f}, r={r_sne:.3f} (POP+SNE)",
    ]
    ax.text(
        0.02, 0.60,
        "\n".join(stats_text),
        transform=ax.transAxes,
        ha="left", va="top",
        fontsize=11, family="Arial",
        bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="0.75", alpha=0.85)
    )

    fig.savefig(out_png, dpi=600, bbox_inches='tight', pad_inches=0.05)
    fig.savefig(out_png.replace(".png", ".pdf"), dpi=600, bbox_inches='tight', pad_inches=0.05, format='pdf')
    plt.close(fig)


def main():
    # 1) compute observed robotaxi orders (15 bins) and fill ROBOTAXI_15
    av_csv = _find_first_existing_file([AV_ORDER_FILE]) or AV_ORDER_FILE
    cci_csv = _find_first_existing_file(CCI_CANDIDATES)
    if not os.path.exists(av_csv):
        raise FileNotFoundError(f"Robotaxi file not found: {AV_ORDER_FILE} (expected in same folder).")
    if not cci_csv:
        raise FileNotFoundError(f"No CCI file found. Expected one of: {CCI_CANDIDATES}")

    orders_15 = compute_robotaxi_orders_15(av_csv=av_csv, cci_file=cci_csv)
    ROBOTAXI_15["orders"] = orders_15.astype(int).tolist()

    # 2) proceed with original logic
    df = pd.DataFrame(ROBOTAXI_15)
    y_obs = df["orders"].values.astype(float)
    x_labels = df["bin_label"].tolist()

    feat = load_grid_features_15bins(CUTS_15)

    # CTX model: Pop' + Pop'^2 + CCI + POI
    X_ctx = feat[["pop_norm", "pop_norm2", "cci_norm", "poi_norm"]].values.astype(float)

    # SNE model (final.py): Pop' + Pop'^2 + SNE + SNE^2
    X_sne = feat[["pop_norm", "pop_norm2", "sne", "sne2"]].values.astype(float)

    y_ctx = fit_ols_predict(y_obs, X_ctx, use_log=ROBOTAXI_USE_LOG_Y)
    y_sne = fit_ols_predict(y_obs, X_sne, use_log=ROBOTAXI_USE_LOG_Y)

    plot_robotaxi_ctx_vs_sne(
        x_labels=x_labels,
        y_obs=y_obs,
        y_ctx=y_ctx,
        y_sne=y_sne,
        cuts=CUTS_15,
        out_png=OUT_PNG
    )

    print("[Done] Saved:")
    print(" -", os.path.abspath(OUT_PNG))
    print(" -", os.path.abspath(OUT_PNG.replace(".png", ".pdf")))

    print("\n[Observed Robotaxi orders by CCI-quantile bins (15)]")
    print(ROBOTAXI_15["orders"])


if __name__ == "__main__":
    main()
