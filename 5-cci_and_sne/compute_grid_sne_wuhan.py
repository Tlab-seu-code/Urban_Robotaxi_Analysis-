import math
import numpy as np
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, box

# 研究范围
LON_MIN, LON_MAX = 113.942617, 114.629031
LAT_MIN, LAT_MAX = 30.255898, 30.742468
# 网格步长
LON_STEP = 0.0103997242944
LAT_STEP = 0.0089831117499

# 由范围和步长推算网格数量
NX = int((LON_MAX - LON_MIN) // LON_STEP)
NY = int((LAT_MAX - LAT_MIN) // LAT_STEP)

# 输入道路文件
INPUT_EDGES_PATH = "wuhan_drive_edges.gpkg"

# 输出网格级SNE
OUTPUT_GRID_SNE_CSV = "wuhan_grid_sne_2.csv"

# 投影坐标系
PROJ_CRS = "EPSG:32649"

# 每个网格最少需要多少条边才计算 SNE (太少时结果很不稳定)
MIN_EDGES_PER_CELL = 2


def compute_bearing_from_linestring_utm(geom):
    """
    以 UTM (米制) 坐标系下的 LineString/MultiLineString 为输入,
    计算代表性方位角 bearing (degree, 0–360).
    定义: 北为 0°, 顺时针为正.
    取线段的首末点来估计整体方向.
    """
    if geom.is_empty:
        return math.nan

    # MultiLineString 时, 取最长的一段
    if geom.geom_type == "MultiLineString":
        if len(geom.geoms) == 0:
            return math.nan
        line = max(geom.geoms, key=lambda g: g.length)
    elif geom.geom_type == "LineString":
        line = geom
    else:
        return math.nan

    coords = list(line.coords)
    if len(coords) < 2:
        return math.nan

    x1, y1 = coords[0]
    x2, y2 = coords[-1]

    dx = x2 - x1  # 东向
    dy = y2 - y1  # 北向

    # 以北为 0°, 顺时针为正: atan2(dx, dy)
    angle_rad = math.atan2(dx, dy)
    angle_deg = math.degrees(angle_rad)
    bearing = (angle_deg + 360.0) % 360.0
    return bearing


def map_lonlat_to_grid(lon, lat):
    """
    将一个 WGS84 点 (lon, lat) 映射到 (grid_x, grid_y).
    - 若点不在研究范围内, 返回 (None, None).
    - 网格索引从 (0,0) 开始, 最大为 (NX-1, NY-1).
    """
    if not (LON_MIN <= lon < LON_MAX and LAT_MIN <= lat < LAT_MAX):
        return None, None

    gx = int((lon - LON_MIN) // LON_STEP)
    gy = int((lat - LAT_MIN) // LAT_STEP)

    # 保护一下边界
    if gx < 0 or gx >= NX or gy < 0 or gy >= NY:
        return None, None

    return gx, gy


def compute_sne_from_bearings(bearings_deg):
    """
    bearings_deg: 1D array-like, 每条边的方位角, 范围 [0,360).
    1) 用 72 个 5° bins 统计直方图, 范围 [0,360).
    2) 先在 72-bin 上做 roll(shift=1), 将最后一个 bin [355,360) 移到最前,
       使其与原来的 [0,5) 挨在一起, 形成 [355,5) 的连续区间.
    3) 再将 72-bin 以两两合并方式变成 36 个 10° bins.
    4) p_i = count_i / N, H = -∑ p_i ln p_i.
    5) H_norm = H / ln(36), 归一化到 [0,1].
    返回:
    - H, H_norm, n_edges
    """
    bearings = np.asarray(bearings_deg)
    bearings = bearings[~np.isnan(bearings)]
    n = bearings.size
    if n == 0:
        return math.nan, math.nan, 0

    # 72 x 5° bins
    hist_72, _ = np.histogram(
        bearings,
        bins=72,
        range=(0.0, 360.0)
    )

    # 先 roll
    hist_72_rot = np.roll(hist_72, shift=1)

    # 再合并为 36 x 10° bins
    hist_36 = hist_72_rot.reshape((36, 2)).sum(axis=1)

    total = hist_36.sum()
    if total == 0:
        return math.nan, math.nan, 0

    p = hist_36 / total
    mask = p > 0
    H = -np.sum(p[mask] * np.log(p[mask]))
    H_norm = H / math.log(36.0)

    return H, H_norm, n



def main():
    print(f"[LOAD] 读取道路文件: {INPUT_EDGES_PATH}")
    gdf_wgs = gpd.read_file(INPUT_EDGES_PATH)

    if gdf_wgs.crs is None:
        raise ValueError("输入 GPKG 没有 CRS, 请确认其为 WGS84 并手动设为 EPSG:4326.")
    if gdf_wgs.crs.to_string() != "EPSG:4326":
        print(f"[CRS] 当前 CRS = {gdf_wgs.crs}, 转为 WGS84 (EPSG:4326)...")
        gdf_wgs = gdf_wgs.to_crs("EPSG:4326")
    # 去掉空几何
    gdf_wgs = gdf_wgs[~gdf_wgs.geometry.is_empty].copy()
    gdf_wgs.reset_index(drop=True, inplace=True)
    print(f"[LOAD] 有效边数量: {len(gdf_wgs)}")
    print("[MIDPOINT] 计算每条边的中点 (WGS84)...")
    midpoints = gdf_wgs.geometry.interpolate(0.5, normalized=True)
    mid_lons = midpoints.x
    mid_lats = midpoints.y

    grid_x_list = []
    grid_y_list = []
    in_range_mask = []

    for lon, lat in zip(mid_lons, mid_lats):
        gx, gy = map_lonlat_to_grid(lon, lat)
        if gx is None:
            in_range_mask.append(False)
            grid_x_list.append(None)
            grid_y_list.append(None)
        else:
            in_range_mask.append(True)
            grid_x_list.append(gx)
            grid_y_list.append(gy)

    gdf_wgs["mid_lon"] = mid_lons
    gdf_wgs["mid_lat"] = mid_lats
    gdf_wgs["grid_x"] = grid_x_list
    gdf_wgs["grid_y"] = grid_y_list

    # 只保留落在研究范围内的道路段
    gdf_wgs_in = gdf_wgs[in_range_mask].copy()
    gdf_wgs_in.reset_index(drop=True, inplace=True)
    print(f"[FILTER] 研究范围内的道路段数量: {len(gdf_wgs_in)}")

    if len(gdf_wgs_in) == 0:
        raise ValueError("研究范围内没有任何道路段, 请检查范围和数据。")
    print(f"[CRS] 转换到投影坐标系 {PROJ_CRS} 以计算方位角...")
    gdf_utm = gdf_wgs_in.to_crs(PROJ_CRS)

    print("[BEARING] 计算每条边的方位角 (0–360°)...")
    bearings = []
    for geom in gdf_utm.geometry:
        b = compute_bearing_from_linestring_utm(geom)
        bearings.append(b)

    gdf_wgs_in["bearing_deg"] = bearings
    # 剔除 NaN 方位角
    before = len(gdf_wgs_in)
    gdf_wgs_in = gdf_wgs_in[~gdf_wgs_in["bearing_deg"].isna()].copy()
    after = len(gdf_wgs_in)
    print(f"[BEARING] 有效方位角边数量: {after} (剔除 {before - after} 条)")

    # 按网格分组, 计算每个网格的SNE
    print("[SNE] 按 (grid_x, grid_y) 分组计算 SNE...")
    records = []

    grouped = gdf_wgs_in.groupby(["grid_x", "grid_y"])
    for (gx, gy), group in grouped:
        bearings_cell = group["bearing_deg"].values
        H, H_norm, n_edges = compute_sne_from_bearings(bearings_cell)

        # 对于边数太少的格子, 根据阈值决定是否保留
        if n_edges < MIN_EDGES_PER_CELL:
            H = math.nan
            H_norm = math.nan

        # 该格子对应的经纬度范围
        lon_min = LON_MIN + gx * LON_STEP
        lon_max = lon_min + LON_STEP
        lat_min = LAT_MIN + gy * LAT_STEP
        lat_max = lat_min + LAT_STEP

        records.append({
            "grid_x": gx,
            "grid_y": gy,
            "lon_min": lon_min,
            "lon_max": lon_max,
            "lat_min": lat_min,
            "lat_max": lat_max,
            "n_edges": n_edges,
            "SNE": H,
            "SNE_norm": H_norm
        })

    df_grid = pd.DataFrame(records)
    df_grid.sort_values(by=["grid_y", "grid_x"], inplace=True)
    df_grid.reset_index(drop=True, inplace=True)

    print(f"[SNE] 共计算出 {len(df_grid)} 个非空网格的道路复杂度 (SNE).")

    # 4.5 保存结果
    df_grid.to_csv(OUTPUT_GRID_SNE_CSV, index=False, encoding="utf-8-sig")
    print(f"[OUT] 网格级 SNE 已保存到: {OUTPUT_GRID_SNE_CSV}")

    print("\n[SUMMARY] 你现在拥有:")
    print("  - 基于完整武汉路网、在你研究范围内的网格级道路复杂度 SNE/SNE_norm;")
    print("  - 每行对应一个 (grid_x, grid_y), 可以与 AV/HV 轨迹的同网格统计直接 merge。")


if __name__ == "__main__":
    main()
