# -*- coding: utf-8 -*-
"""
Generate radar-only figures for K = 10% to 90%.

Each output figure contains only the right-side radar chart.
A total of 9 figures will be generated:
Top-10%, Top-20%, ..., Top-90%

Input files are assumed to be in the same folder as this script:
1. v3-districts.csv
2. v10-hdv.csv
3. cci_grid_linear_grid.csv   (or .xlsx)

Outputs will be saved to:
./sensitivity output/
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict


# ---------------- Font settings ----------------
plt.rcParams["font.family"] = "Calibri"
plt.rcParams["axes.unicode_minus"] = False


# ---------------- File paths ----------------
def get_script_dir():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()


SCRIPT_DIR = get_script_dir()

AV_FILE = os.path.join(SCRIPT_DIR, "v3-districts.csv")
HV_FILE = os.path.join(SCRIPT_DIR, "v10-hdv.csv")
CCI_FILE = os.path.join(SCRIPT_DIR, "cci_grid_linear_grid.csv")

# These are not used in the current script, but kept as relative paths
POI_FILE = os.path.join(SCRIPT_DIR, "武汉市POI数据.csv")
POPULATION_FILE = os.path.join(SCRIPT_DIR, "wuhan_grid_population_density.csv")
BOUNDARY_FILE = os.path.join(SCRIPT_DIR, "wuhan_boundary.geojson.json")

CHUNK_SZ = 200_000

OUTPUT_DIR = os.path.join(SCRIPT_DIR, "sensitivity output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------- Core parameters ----------------
PERIODS = [
    "Peak hour (Morning)",
    "Day",
    "Peak hour (Evening)",
    "Night",
    "All Periods"
]

period_order = [
    "Peak hour (Morning)",
    "Day",
    "Peak hour (Evening)",
    "Night"
]

CCI_QUANTILES = [0.2, 0.4, 0.6, 0.8]

CCI_LABELS = [
    f"<{CCI_QUANTILES[0] * 100:.0f}%",
    f"{CCI_QUANTILES[0] * 100:.0f}%~{CCI_QUANTILES[1] * 100:.0f}%",
    f"{CCI_QUANTILES[1] * 100:.0f}%~{CCI_QUANTILES[2] * 100:.0f}%",
    f"{CCI_QUANTILES[2] * 100:.0f}%~{CCI_QUANTILES[3] * 100:.0f}%",
    f">{CCI_QUANTILES[3] * 100:.0f}%"
]

CCI_LEGEND_LABELS = [
    "CCI < P20",
    "P20 ~ P40",
    "P40 ~ P60",
    "P60 ~ P80",
    "CCI > P80"
]

RADAR_ORDER = [0, 1, 2, 3, 4]
RADAR_LABELS = [CCI_LEGEND_LABELS[i] for i in RADAR_ORDER]

sensitivity_config = {
    "Peak hour (Morning)": {
        "color": "#E64B35",
        "marker": "^",
        "label": "Peak hour (Morning)"
    },
    "Day": {
        "color": "#00A087",
        "marker": "s",
        "label": "Day"
    },
    "Peak hour (Evening)": {
        "color": "#F39B7F",
        "marker": "D",
        "label": "Peak hour (Evening)"
    },
    "Night": {
        "color": "#4DBBD5",
        "marker": "*",
        "label": "Night"
    },
    "All Periods": {
        "color": "#3C5488",
        "marker": "o",
        "label": "All Periods"
    }
}

RADAR_COLORS = [
    sensitivity_config["Peak hour (Morning)"]["color"],
    sensitivity_config["Peak hour (Evening)"]["color"],
    sensitivity_config["All Periods"]["color"],
    sensitivity_config["Night"]["color"],
    sensitivity_config["Day"]["color"]
]


# ---------------- Wuhan grid settings ----------------
LON_MIN, LON_MAX = 113.942617, 114.629031
LAT_MIN, LAT_MAX = 30.255898, 30.742468

dx = 0.0103997242944
dy = 0.0089831117499


# ---------------- Utility functions ----------------
def check_file_exists(path, label):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{label} not found:\n"
            f"{path}\n\n"
            f"Please put this file in the same folder as this script:\n"
            f"{SCRIPT_DIR}"
        )


def get_grid_id(lon, lat):
    gx = np.floor((lon - LON_MIN) / dx).astype(int)
    gy = np.floor((lat - LAT_MIN) / dy).astype(int)

    gx = np.clip(gx, 0, int(np.ceil((LON_MAX - LON_MIN) / dx)))
    gy = np.clip(gy, 0, int(np.ceil((LAT_MAX - LAT_MIN) / dy)))

    return gx, gy


def classify_time(h):
    if 7 <= h < 9:
        return "Peak hour (Morning)"
    elif 9 <= h < 17:
        return "Day"
    elif 17 <= h < 20:
        return "Peak hour (Evening)"
    else:
        return "Night"


def top_k_overlap(arr1, arr2, k_pct):
    flat1 = arr1.ravel()
    flat2 = arr2.ravel()

    mask = (flat1 > 0) | (flat2 > 0)
    idc = np.where(mask)[0]
    total_grids = len(idc)

    k = int(total_grids * k_pct) if total_grids > 0 else 0

    if k == 0:
        return 0.0

    top1 = set(idc[np.argsort(flat1[mask])[::-1][:k]])
    top2 = set(idc[np.argsort(flat2[mask])[::-1][:k]])

    return len(top1 & top2) / k


def load_cci_data(cci_file_path):
    """
    Supports both .csv and .xlsx files.
    Required columns:
    grid_lon, grid_lat, grid_x, grid_y, cci_max
    """
    ext = os.path.splitext(cci_file_path)[1].lower()

    if ext == ".csv":
        try:
            cci_df = pd.read_csv(cci_file_path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            cci_df = pd.read_csv(cci_file_path, encoding="gbk")
    elif ext in [".xlsx", ".xls"]:
        cci_df = pd.read_excel(cci_file_path)
    else:
        raise ValueError(
            f"Unsupported CCI file format: {ext}. "
            "Please use .csv, .xlsx, or .xls."
        )

    cci_df.columns = [str(c).strip() for c in cci_df.columns]

    required_cols = ["grid_lon", "grid_lat", "grid_x", "grid_y", "cci_max"]
    missing_cols = [c for c in required_cols if c not in cci_df.columns]

    if missing_cols:
        raise ValueError(
            f"CCI file is missing required columns: {missing_cols}\n"
            f"Available columns: {list(cci_df.columns)}"
        )

    cci_df = cci_df[
        (cci_df["grid_lon"] >= LON_MIN) &
        (cci_df["grid_lon"] <= LON_MAX) &
        (cci_df["grid_lat"] >= LAT_MIN) &
        (cci_df["grid_lat"] <= LAT_MAX)
    ].copy()

    grid_cci = {}

    for _, row in cci_df.iterrows():
        if pd.isna(row["grid_x"]) or pd.isna(row["grid_y"]) or pd.isna(row["cci_max"]):
            continue

        gx = int(row["grid_x"])
        gy = int(row["grid_y"])
        grid_cci[(gx, gy)] = float(row["cci_max"])

    valid_cci = [v for v in grid_cci.values() if pd.notna(v) and v > 0]

    if not valid_cci:
        quantile_values = [0, 0, 0, 0]
    else:
        quantile_values = np.quantile(valid_cci, CCI_QUANTILES)

    return grid_cci, quantile_values, cci_df


def get_grid_cci_interval(grid_cci, quantile_values):
    grid_interval = {}

    for (gx, gy), cci in grid_cci.items():
        if cci <= quantile_values[0]:
            grid_interval[(gx, gy)] = 0
        elif cci <= quantile_values[1]:
            grid_interval[(gx, gy)] = 1
        elif cci <= quantile_values[2]:
            grid_interval[(gx, gy)] = 2
        elif cci <= quantile_values[3]:
            grid_interval[(gx, gy)] = 3
        else:
            grid_interval[(gx, gy)] = 4

    return grid_interval


def build_compete(arr_av, arr_hv):
    all_grids = set(arr_av.keys()).union(set(arr_hv.keys()))

    if len(all_grids) == 0:
        return (
            np.zeros((1, 1), float),
            np.zeros((1, 1), float),
            {},
            {},
            1,
            1
        )

    gx_vals = sorted({g[0] for g in all_grids})
    gy_vals = sorted({g[1] for g in all_grids})

    gx_map = {v: i for i, v in enumerate(gx_vals)}
    gy_map = {v: i for i, v in enumerate(gy_vals)}

    nr = len(gy_vals)
    nc = len(gx_vals)

    av_arr = np.zeros((nr, nc), float)
    hv_arr = np.zeros((nr, nc), float)

    for g in all_grids:
        r = gy_map[g[1]]
        c = gx_map[g[0]]

        av_arr[r, c] = arr_av.get(g, 0)
        hv_arr[r, c] = arr_hv.get(g, 0)

    return av_arr, hv_arr, gx_map, gy_map, nr, nc


def calculate_region_topk(av_arr, hv_arr, grid_interval, gx_map, gy_map, nr, nc, k_pct):
    interval_masks = [np.zeros((nr, nc), dtype=bool) for _ in range(5)]

    for (gx, gy), interval in grid_interval.items():
        if gx in gx_map and gy in gy_map:
            r = gy_map[gy]
            c = gx_map[gx]

            if 0 <= r < nr and 0 <= c < nc:
                interval_masks[interval][r, c] = True

    topk_ratios = []

    for mask in interval_masks:
        av_region = av_arr[mask]
        hv_region = hv_arr[mask]

        if len(av_region) == 0 or len(hv_region) == 0:
            topk_ratios.append(0.0)
            continue

        overlap = top_k_overlap(
            av_region.reshape(-1, 1),
            hv_region.reshape(-1, 1),
            k_pct
        )

        topk_ratios.append(overlap)

    return topk_ratios


def align_av_hv_dates(av_data, hv_data):
    av_data["date"] = av_data["呼单时间"].dt.date
    hv_data["date"] = hv_data["start_time"].dt.date

    av_unique_dates = sorted(av_data["date"].unique())
    hv_unique_dates = sorted(hv_data["date"].unique())

    common_days_count = min(len(av_unique_dates), len(hv_unique_dates))

    print("=== Date alignment statistics ===")
    print(f"AV data: {len(av_unique_dates)} days, {len(av_data)} records")
    print(f"HV data: {len(hv_unique_dates)} days, {len(hv_data)} records")
    print(f"Aligned days: {common_days_count}")

    if common_days_count == 0:
        raise SystemExit("No available days for AV-HV matching. Program terminated.")

    av_aligned_dates = av_unique_dates[:common_days_count]
    hv_aligned_dates = hv_unique_dates[:common_days_count]

    av_data_aligned = av_data[av_data["date"].isin(av_aligned_dates)].copy()
    hv_data_aligned = hv_data[hv_data["date"].isin(hv_aligned_dates)].copy()

    av_data_aligned = av_data_aligned.drop(columns=["date"])
    hv_data_aligned = hv_data_aligned.drop(columns=["date"])

    print(f"After date alignment: AV = {len(av_data_aligned)}, HV = {len(hv_data_aligned)}")

    return av_data_aligned, hv_data_aligned


def plot_radar_only(ax, data_list, labels, periods, colors, topk_percent):
    num_vars = len(periods)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()

    legend_items = []

    for i, data in enumerate(data_list):
        values = data + [data[0]]
        angles_closed = angles + [angles[0]]

        line, = ax.plot(
            angles_closed,
            values,
            color=colors[i],
            linewidth=2,
            label=labels[i],
            zorder=1
        )

        ax.fill(
            angles_closed,
            values,
            color=colors[i],
            alpha=0.2,
            zorder=1
        )

        legend_items.append((line, labels[i]))

    ax.set_thetagrids(np.degrees(angles), periods, fontsize=20)

    for label in ax.get_xticklabels():
        label.set_zorder(100)

        theta, r = label.get_position()
        angle_deg = round(np.degrees(theta)) % 360

        if angle_deg == 0:
            new_r = r * 1.14
            label.set_ha("left")
            label.set_va("center")
        elif angle_deg == 72:
            new_r = r * 1.30
            label.set_ha("left")
            label.set_va("bottom")
        elif angle_deg == 144:
            new_r = r * 1.18
            label.set_ha("right")
            label.set_va("bottom")
        elif angle_deg == 216:
            new_r = r * 1.20
            label.set_ha("right")
            label.set_va("top")
        elif angle_deg == 288:
            new_r = r * 1.30
            label.set_ha("left")
            label.set_va("top")
        else:
            new_r = r * 1.30

        label.set_position((theta, new_r))

    ax.set_rlabel_position(112.5)

    # Dynamic radial scale:
    # Top-10% to Top-50% keep the original 0-50% scale;
    # Top-60% to Top-90% extend to the corresponding K value.
    radial_max = max(50, int(topk_percent))

    # Also avoid clipping if the actual overlap value is higher than the K-based scale.
    data_max = max(max(row) for row in data_list) if data_list else 0
    radial_max = max(radial_max, int(np.ceil(data_max / 10.0) * 10))
    radial_max = min(radial_max, 100)

    ax.set_ylim(0, radial_max)
    ax.set_yticks(np.arange(0, radial_max + 1, 10))
    ax.set_yticklabels([f"{x}%" for x in range(0, radial_max + 1, 10)], fontsize=20)

    for tick in ax.get_yticklabels():
        tick.set_zorder(100)

    ax.set_title(f"Top-{topk_percent}%", fontsize=24, pad=6, y=1.05)
    ax.title.set_zorder(100)

    ax.spines["polar"].set_color("black")
    ax.spines["polar"].set_linewidth(0.8)
    ax.grid(
        color="black",
        linestyle="-",
        linewidth=0.5,
        alpha=0.2,
        zorder=2
    )

    handles, texts = zip(*legend_items)

    legend = ax.legend(
        handles,
        texts,
        title="CCI",
        loc="upper left",
        bbox_to_anchor=(1.00, 1.00),
        bbox_transform=ax.transAxes,
        fontsize=14,
        title_fontsize=14,
        frameon=True
    )

    legend.set_zorder(100)


def compute_period_results_for_k(
    av_grid, hv_grid, av_pgrid, hv_pgrid, grid_interval, k_pct
):
    results = {}

    av_total_arr, hv_total_arr, base_gx_map, base_gy_map, base_nr, base_nc = build_compete(
        av_grid,
        hv_grid
    )

    results["All Periods"] = calculate_region_topk(
        av_total_arr,
        hv_total_arr,
        grid_interval,
        base_gx_map,
        base_gy_map,
        base_nr,
        base_nc,
        k_pct
    )

    for p in PERIODS[:4]:
        av_p_arr, hv_p_arr, _, _, _, _ = build_compete(
            av_pgrid[p],
            hv_pgrid[p]
        )

        av_aligned = np.zeros((base_nr, base_nc), float)
        hv_aligned = np.zeros((base_nr, base_nc), float)

        curr_grids = set(av_pgrid[p].keys()).union(set(hv_pgrid[p].keys()))
        curr_gx_vals = sorted({g[0] for g in curr_grids})
        curr_gy_vals = sorted({g[1] for g in curr_grids})

        curr_gx_map = {v: i for i, v in enumerate(curr_gx_vals)}
        curr_gy_map = {v: i for i, v in enumerate(curr_gy_vals)}

        for g in curr_grids:
            if g[0] in base_gx_map and g[1] in base_gy_map:
                target_r = base_gy_map[g[1]]
                target_c = base_gx_map[g[0]]

                if g[0] in curr_gx_map and g[1] in curr_gy_map:
                    src_r = curr_gy_map[g[1]]
                    src_c = curr_gx_map[g[0]]

                    av_aligned[target_r, target_c] = av_p_arr[src_r, src_c]
                    hv_aligned[target_r, target_c] = hv_p_arr[src_r, src_c]

        results[p] = calculate_region_topk(
            av_aligned,
            hv_aligned,
            grid_interval,
            base_gx_map,
            base_gy_map,
            base_nr,
            base_nc,
            k_pct
        )

    return results


def save_single_radar_figure(results, topk_percent):
    fig = plt.figure(figsize=(12.5, 8.5))
    ax = fig.add_subplot(111, polar=True)

    radar_data = []

    for i in range(5):
        row = [results[p][i] * 100 for p in PERIODS]
        radar_data.append(row)

    ordered_radar_data = [radar_data[i] for i in RADAR_ORDER]

    plot_radar_only(
        ax,
        ordered_radar_data,
        RADAR_LABELS,
        PERIODS,
        RADAR_COLORS,
        topk_percent
    )

    plt.subplots_adjust(
        left=0.18,
        right=0.74,
        top=0.88,
        bottom=0.20
    )

    # Slight right shift, aligned with your finalized style
    ax_pos = ax.get_position()
    ax.set_position([
        ax_pos.x0 + 0.01,
        ax_pos.y0,
        ax_pos.width,
        ax_pos.height
    ])

    fig.text(
        0.5,
        0.085,
        f"Top-K Overlap by Time Period and CCI Percentile (K = {topk_percent}%)",
        ha="center",
        va="center",
        fontsize=28
    )

    output_file = os.path.join(
        OUTPUT_DIR,
        f"combined_topk_cci_radar_top{topk_percent}.png"
    )

    plt.savefig(output_file, dpi=300, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)

    print(f"Saved: {output_file}")


# ---------------- Main workflow ----------------
def main():
    check_file_exists(AV_FILE, "AV file")
    check_file_exists(HV_FILE, "HV file")
    check_file_exists(CCI_FILE, "CCI file")

    # 1. Read and clean AV data
    print("1. Reading and cleaning AV data...")

    av_chunks = []
    av_required_cols = ["订单号", "呼单时间", "起点经度", "起点纬度"]

    for chunk in pd.read_csv(
        AV_FILE,
        usecols=av_required_cols,
        chunksize=CHUNK_SZ,
        encoding="utf-8-sig"
    ):
        chunk = chunk.drop_duplicates(subset=["订单号"], keep="first")
        chunk = chunk.dropna(subset=["呼单时间", "起点经度", "起点纬度"])

        chunk = chunk[
            (chunk["起点经度"] >= LON_MIN) &
            (chunk["起点经度"] <= LON_MAX) &
            (chunk["起点纬度"] >= LAT_MIN) &
            (chunk["起点纬度"] <= LAT_MAX)
        ].copy()

        chunk["呼单时间"] = pd.to_datetime(chunk["呼单时间"], errors="coerce")
        chunk = chunk.dropna(subset=["呼单时间"])

        av_chunks.append(chunk)

    av_data = pd.concat(av_chunks, ignore_index=True)

    if len(av_data) == 0:
        raise SystemExit("AV data is empty after cleaning. Program terminated.")

    # 2. Read and clean HV data
    print("2. Reading and cleaning HV data...")

    hv_chunks = []
    hv_required_cols = ["order_id", "start_time", "start_lon", "start_lat"]

    for chunk in pd.read_csv(
        HV_FILE,
        usecols=hv_required_cols,
        chunksize=CHUNK_SZ,
        encoding="utf-8-sig"
    ):
        chunk = chunk.drop_duplicates(subset=["order_id"], keep="first")
        chunk = chunk.dropna(subset=["start_time", "start_lon", "start_lat"])

        chunk["start_time"] = pd.to_datetime(chunk["start_time"], errors="coerce")
        chunk = chunk.dropna(subset=["start_time"])

        chunk = chunk[
            (chunk["start_lon"] >= LON_MIN) &
            (chunk["start_lon"] <= LON_MAX) &
            (chunk["start_lat"] >= LAT_MIN) &
            (chunk["start_lat"] <= LAT_MAX)
        ].copy()

        hv_chunks.append(chunk)

    hv_data = pd.concat(hv_chunks, ignore_index=True)

    if len(hv_data) == 0:
        raise SystemExit("HV data is empty after cleaning. Program terminated.")

    # 3. Align dates
    print("3. Aligning AV and HV dates...")
    av_data_aligned, hv_data_aligned = align_av_hv_dates(av_data, hv_data)

    # 4. Count AV by grid and time period
    print("4. Counting AV orders by grid and time period...")

    av_grid = defaultdict(int)
    av_pgrid = {p: defaultdict(int) for p in PERIODS[:4]}

    av_data_aligned["hour"] = av_data_aligned["呼单时间"].dt.hour
    av_data_aligned["period"] = av_data_aligned["hour"].apply(classify_time)

    av_gx, av_gy = get_grid_id(
        av_data_aligned["起点经度"],
        av_data_aligned["起点纬度"]
    )

    av_data_aligned["grid_id"] = list(zip(av_gx, av_gy))

    av_grid_counts = av_data_aligned["grid_id"].value_counts()

    for grid, count in av_grid_counts.items():
        av_grid[grid] = count

    for p in PERIODS[:4]:
        av_period_data = av_data_aligned[av_data_aligned["period"] == p]

        if not av_period_data.empty:
            period_counts = av_period_data["grid_id"].value_counts()

            for grid, count in period_counts.items():
                av_pgrid[p][grid] = count

    # 5. Count HV by grid and time period
    print("5. Counting HV orders by grid and time period...")

    hv_grid = defaultdict(int)
    hv_pgrid = {p: defaultdict(int) for p in PERIODS[:4]}

    hv_data_aligned["hour"] = hv_data_aligned["start_time"].dt.hour
    hv_data_aligned["period"] = hv_data_aligned["hour"].apply(classify_time)

    hv_gx, hv_gy = get_grid_id(
        hv_data_aligned["start_lon"],
        hv_data_aligned["start_lat"]
    )

    hv_data_aligned["grid_id"] = list(zip(hv_gx, hv_gy))

    hv_grid_counts = hv_data_aligned["grid_id"].value_counts()

    for grid, count in hv_grid_counts.items():
        hv_grid[grid] = count

    for p in PERIODS[:4]:
        hv_period_data = hv_data_aligned[hv_data_aligned["period"] == p]

        if not hv_period_data.empty:
            period_counts = hv_period_data["grid_id"].value_counts()

            for grid, count in period_counts.items():
                hv_pgrid[p][grid] = count

    # 6. Load CCI data
    print("6. Loading CCI data and assigning intervals...")

    grid_cci, cci_quantile_values, _ = load_cci_data(CCI_FILE)
    grid_interval = get_grid_cci_interval(grid_cci, cci_quantile_values)

    print(f"CCI quantiles: {[f'{q:.3f}' for q in cci_quantile_values]}")

    # 7. Generate 9 radar-only figures
    print("7. Generating radar-only figures for Top-10% to Top-90%...")

    for topk_percent in range(10, 100, 10):
        k_pct = topk_percent / 100.0
        print(f"Processing Top-{topk_percent}% ...")

        results = compute_period_results_for_k(
            av_grid,
            hv_grid,
            av_pgrid,
            hv_pgrid,
            grid_interval,
            k_pct
        )

        save_single_radar_figure(results, topk_percent)

    print("Program completed.")


if __name__ == "__main__":
    main()