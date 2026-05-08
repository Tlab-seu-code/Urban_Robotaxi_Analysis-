import os, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import rasterio
from rasterio.windows import from_bounds
from rasterio import features as rio_features
from rasterio.warp import transform as rio_transform
from rasterio.transform import Affine
from shapely.geometry import LineString, Polygon, box
from shapely.ops import split as shp_split, unary_union

try:
    from scipy.ndimage import gaussian_filter
    from scipy.optimize import curve_fit
    HAVE_SCIPY = True
except Exception:
    gaussian_filter = None
    curve_fit = None
    HAVE_SCIPY = False

# 研究范围
LON_MIN, LON_MAX = 113.942617, 114.629031
LAT_MIN, LAT_MAX = 30.255898, 30.742468
RECT: Polygon = box(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX)

# 格子参数
GRID_DX = 0.0103997242944
GRID_DY = 0.0089831117499
NX = int((LON_MAX - LON_MIN) // GRID_DX)
NY = int((LAT_MAX - LAT_MIN) // GRID_DY)

# VIIRS annual
TIF_PATH = "VNL_npp_2024_global_vcmslcfg_v2_c202502261200.average_masked.dat.tif"

# 切分3线4区
P1, P2 = (114.284880,30.556817), (114.170507,30.602691)
P3, P4 = (114.392777,30.667402), (114.044454,30.254089)
P5, P6 = (114.435440,30.593722), (114.351353,30.456384)

# params
RING_BIN_KM   = 1.0
GAMMA_VIS     = 0.6
SMOOTH_SIGMA  = 1.0
TOPK_PEAKS    = 40
SUPPRESS_Q    = 0.998
CAND_TOPQ     = 0.95

# snapping
SNAP_RADIUS_KM    = 1.5
SNAP_SMOOTH_SIGMA = 0.8
SNAP_MAX_R2_DROP  = 0.03

# ring styles
REGION_RING_STEP_KM = 1.5
REGION_RING_ALPHA   = 0.35
REGION_RING_LW      = 0.8
REGION_RING_COLOR   = "k"

RING_FIELD_STEP_KM  = 2.0
RING_FIELD_ALPHA    = 0.35
RING_FIELD_LW       = 0.8
RING_FIELD_COLOR    = "k"

def extend_line_to_bbox(p1, p2, bbox):
    xmin,ymin,xmax,ymax = bbox; x1,y1=p1; x2,y2=p2
    dx, dy = x2-x1, y2-y1
    if abs(dx)<1e-12 and abs(dy)<1e-12: return None
    t=[]
    if abs(dx)>1e-12:
        for xe in (xmin,xmax):
            tt=(xe-x1)/dx; y=y1+tt*dy
            if ymin-1e-10<=y<=ymax+1e-10: t.append((tt,xe,y))
    if abs(dy)>1e-12:
        for ye in (ymin,ymax):
            tt=(ye-y1)/dy; x=x1+tt*dx
            if xmin-1e-10<=x<=xmax+1e-10: t.append((tt,x,ye))
    if len(t)<2: return None
    t.sort(key=lambda z:z[0]); A=(t[0][1],t[0][2]); B=(t[-1][1],t[-1][2])
    return LineString([A,B])

def x_on_line_at_y(pA, pB, y0):
    x1,y1=pA; x2,y2=pB
    if abs(y2-y1)<1e-12: return (x1+x2)/2.0
    t=(y0-y1)/(y2-y1); return x1+t*(x2-x1)

def rasterize_polygon(poly, shape, transform):
    return rio_features.rasterize([(poly,1)], out_shape=shape, transform=transform,
                                  fill=0, all_touched=True, dtype="uint8").astype(bool)

def haversine_km(lon1, lat1, lon2, lat2):
    R=6371.0088
    lon1,lat1,lon2,lat2 = map(np.radians,[lon1,lat1,lon2,lat2])
    dlon, dlat = lon2-lon1, lat2-lat1
    a=np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    return 2*R*np.arcsin(np.sqrt(a))

def load_viirs_subwindow():
    if not os.path.exists(TIF_PATH):
        raise FileNotFoundError(f"Not found: {TIF_PATH}")
    with rasterio.open(TIF_PATH) as src:
        win = from_bounds(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX, transform=src.transform)
        arr = src.read(1, window=win, masked=True)
        tfm = rasterio.windows.transform(win, src.transform)
        crs_src = src.crs
    A = arr.filled(0.0).astype("float64")
    h,w = A.shape
    a,b,c,d,e,f = tfm.a, tfm.b, tfm.c, tfm.d, tfm.e, tfm.f
    cols = np.arange(w); rows = np.arange(h)
    X_src = c + cols*a + 0.5*a
    Y_src = f + rows*e + 0.5*e
    Xs = np.tile(X_src,(h,1)); Ys = np.tile(Y_src.reshape(-1,1),(1,w))
    if crs_src is None or (crs_src.to_epsg() != 4326):
        lon, lat = rio_transform(crs_src, "EPSG:4326", Xs.ravel(), Ys.ravel())
        Xg = np.asarray(lon).reshape(h,w)
        Yg = np.asarray(lat).reshape(h,w)
        tfm_out = Affine((Xg[0,1]-Xg[0,0]), 0, Xg[0,0], 0, (Yg[1,0]-Yg[0,0]), Yg[0,0])
    else:
        Xg, Yg = Xs, Ys
        tfm_out = tfm
    return A, tfm_out, "EPSG:4326", Xg, Yg

def build_four_regions():
    bbox=(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX)
    L1=extend_line_to_bbox(P1,P2,bbox)
    L2=extend_line_to_bbox(P3,P4,bbox)
    L3=extend_line_to_bbox(P5,P6,bbox)
    parts_lr = list(shp_split(RECT, L2).geoms)
    left_parts, right_parts = [], []
    for poly in parts_lr:
        cy,cx = float(poly.centroid.y), float(poly.centroid.x)
        x_line = x_on_line_at_y(P3,P4,cy)
        (right_parts if cx>x_line else left_parts).append(poly)
    left_union, right_union = unary_union(left_parts), unary_union(right_parts)
    left_pieces  = list(shp_split(left_union, L1).geoms)  if not left_union.is_empty else []
    right_pieces = list(shp_split(right_union, L3).geoms) if not right_union.is_empty else []
    if len(left_pieces)<2: left_pieces=[left_union]
    if len(right_pieces)<2: right_pieces=[right_union]
    left_pieces  = sorted(left_pieces,  key=lambda g:g.area, reverse=True)[:2]
    right_pieces = sorted(right_pieces, key=lambda g:g.area, reverse=True)[:2]
    regions = sorted(left_pieces+right_pieces, key=lambda g:(-g.centroid.y, g.centroid.x))
    lines_for_plot = [L2, L1.intersection(left_union), L3.intersection(right_union)]
    return regions, lines_for_plot

# inverse-S fit
def ring_profile_and_fit(x0, y0, A, mask, Xg, Yg):
    valid = mask
    if np.count_nonzero(valid) < 200: return None
    d = haversine_km(Xg, Yg, x0, y0)
    dv = d[valid].ravel()
    yv = A[valid].ravel()
    if dv.size < 50: return None
    Dmax = float(np.quantile(dv, 0.95))
    if Dmax <= 0: return None
    edges = np.arange(0, max(1.0, Dmax) + RING_BIN_KM, RING_BIN_KM)
    ring = np.digitize(dv, edges, right=False) - 1
    ring = np.clip(ring, 0, len(edges)-2)
    df = (pd.DataFrame({"ring": ring, "val": yv}).groupby("ring")["val"].mean().reset_index())
    if df.empty or df.shape[0] < 6: return None
    r = ((edges[df["ring"].values] + edges[df["ring"].values+1]) / 2.0).astype(float)
    vals = df["val"].to_numpy()
    vals = pd.Series(vals).rolling(3, center=True, min_periods=1).median().to_numpy()
    vmin, vmax = float(vals.min()), float(vals.max())
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax - vmin <= 0: return None
    nli = (vals - vmin) / (vmax - vmin)
    def invS(rr, a, cpar, Dpar): return 1.0 - cpar / (1.0 + np.exp(a*(2.0*rr/Dpar - 1.0))) + cpar
    a_fit = c_fit = D_fit = r2 = None
    if HAVE_SCIPY and curve_fit is not None:
        p0 = [2.0, 0.05, max(5.0, r.max()*0.8)]
        bounds = ([0.1, 0.0, r.max()*0.3], [8.0, 0.6, r.max()*2.5])
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                popt, _ = curve_fit(invS, r, nli, p0=p0, bounds=bounds, maxfev=10000)
            a_fit, c_fit, D_fit = map(float, popt)
        except Exception:
            a_fit = None
    if a_fit is None:
        best=None
        for a in np.linspace(0.5,6.0,24):
            for cpar in np.linspace(0.0,0.5,11):
                for Dpar in np.linspace(max(3.0,r.max()*0.5), r.max()*2.0, 20):
                    yh = invS(r, a, cpar, Dpar)
                    ss_res = float(np.sum((nli - yh)**2))
                    ss_tot = float(np.sum((nli - nli.mean())**2))
                    r2_tmp = 1.0 - ss_res/ss_tot if ss_tot>1e-12 else 0.0
                    if (best is None) or (r2_tmp > best[0]): best = (r2_tmp, a, cpar, Dpar)
        if best is None: return None
        r2, a_fit, c_fit, D_fit = map(float, best)
    if r2 is None:
        yh = invS(r, a_fit, c_fit, D_fit)
        ss_res = float(np.sum((nli - yh)**2))
        ss_tot = float(np.sum((nli - nli.mean())**2))
        r2 = 1.0 - ss_res/ss_tot if ss_tot>1e-12 else 0.0
    return {"alpha": a_fit, "c": c_fit, "D": D_fit, "r2": float(r2),
            "r": r, "nli": nli, "Dmax": Dmax}

def regional_candidates(A, mask, k=30, sigma=1.0, bright_thr=None):
    B = A if gaussian_filter is None else gaussian_filter(A, sigma=sigma)
    H,W = B.shape; rad=3; coords=[]
    for r in range(rad, H-rad):
        br = B[r]
        for c in range(rad, W-rad):
            if not mask[r,c]: continue
            if bright_thr is not None and A[r,c] < bright_thr: continue
            v = br[c]; win = B[r-rad:r+rad+1, c-rad:c+rad+1]
            if v == np.max(win) and v>0: coords.append((v,r,c))
    coords.sort(reverse=True)
    return [(r,c) for _,r,c in coords[:k]]

def snap_to_local_peak(x0, y0, A2, Xg, Yg, region_mask, r_km=SNAP_RADIUS_KM, sigma=SNAP_SMOOTH_SIGMA):
    if sigma is not None and gaussian_filter is not None: G = gaussian_filter(A2, sigma=sigma)
    else: G = A2
    d = haversine_km(Xg, Yg, x0, y0)
    cand_mask = (region_mask & (d <= r_km))
    if np.count_nonzero(cand_mask) == 0: return x0, y0, None, None
    rr, cc = np.where(cand_mask); idx = np.argmax(G[cand_mask])
    r_sel, c_sel = rr[idx], cc[idx]
    return float(Xg[r_sel, c_sel]), float(Yg[r_sel, c_sel]), r_sel, c_sel

def compute_center_and_cci(poly, A, Xg, Yg, tfm):
    mask = rasterize_polygon(poly, A.shape, tfm).astype(bool)
    A2 = A
    if SUPPRESS_Q is not None:
        vals = A2[mask]
        if vals.size>0:
            hi = np.quantile(vals, SUPPRESS_Q)
            A2 = A2.copy(); A2[A2>hi] = hi
    vloc = A2[mask]
    cand_thr = np.quantile(vloc[vloc>0], CAND_TOPQ) if np.any(vloc>0) else None
    cand = regional_candidates(A2, mask, k=TOPK_PEAKS, sigma=SMOOTH_SIGMA, bright_thr=cand_thr)

    best = None
    for (r, c) in cand:
        fit = ring_profile_and_fit(float(Xg[r, c]), float(Yg[r, c]), A2, mask, Xg, Yg)
        if not fit: continue
        r2 = fit.get("r2", np.nan)
        if not (isinstance(r2, (int,float)) and np.isfinite(r2)): continue
        anchor_val = float(A2[r,c])
        key_cur = (r2, anchor_val, fit["D"])
        if (best is None) or (key_cur > best["key"]): best = {"r": r, "c": c, "fit": fit, "key": key_cur}

    if best is None:
        Ap = np.where(mask, A2, 0.0); s = Ap.sum()
        if s > 0:
            xs, ys = Xg[0,:], Yg[:,0]
            cx = float((xs * Ap.sum(axis=0)).sum() / s)
            cy = float((ys * Ap.sum(axis=1)).sum() / s)   # fix typo
        else:
            cx, cy = float(poly.centroid.x), float(poly.centroid.y)
        return (cx, cy), None, mask, None, None, None

    x0, y0 = float(Xg[best["r"], best["c"]]), float(Yg[best["r"], best["c"]])
    fit0 = best["fit"]; r2_0 = fit0["r2"]

    x_s, y_s, r_s, c_s = snap_to_local_peak(x0, y0, A2, Xg, Yg, mask)
    if r_s is not None:
        fit_s = ring_profile_and_fit(x_s, y_s, A2, mask, Xg, Yg)
        if fit_s is not None and (fit_s["r2"] >= r2_0 - SNAP_MAX_R2_DROP):
            x0, y0, fit0 = x_s, y_s, fit_s

    alpha, cpar, Dpar = fit0["alpha"], fit0["c"], fit0["D"]
    d = haversine_km(Xg, Yg, x0, y0)
    def invS(rr): return 1.0 - cpar / (1.0 + np.exp(alpha*(2.0*rr/Dpar - 1.0))) + cpar
    rmax_norm = float(np.quantile(d[mask], 0.90))
    y0_hat, yD_hat = invS(0.0), invS(rmax_norm)
    den = (y0_hat - yD_hat) if (y0_hat - yD_hat) != 0 else 1.0
    CCI = np.clip((invS(d) - yD_hat) / den, 0.0, 1.0)
    center = (x0, y0)
    return center, CCI, mask, float(fit0["r2"]), fit0, rmax_norm

# rings
def circle_lonlat(lon0, lat0, radius_km, n=540):
    lat0_rad = np.radians(lat0)
    dlat = radius_km / 110.574
    dlon = radius_km / (111.320 * np.cos(lat0_rad) + 1e-12)
    theta = np.linspace(0, 2*np.pi, n, endpoint=True)
    lats = lat0 + dlat * np.sin(theta)
    lons = lon0 + dlon * np.cos(theta)
    return lons, lats

def draw_concentric_rings_clipped(ax, center_lon, center_lat, step_km, max_km, clip_poly,
                                  color="k", lw=0.8, alpha=0.35):
    r = step_km
    while r <= max_km + 1e-9:
        xs, ys = circle_lonlat(center_lon, center_lat, r, n=540)
        inter = LineString(np.column_stack([xs, ys])).intersection(clip_poly)
        if not inter.is_empty:
            if inter.geom_type == "LineString":
                sx, sy = inter.xy; ax.plot(sx, sy, color=color, lw=lw, alpha=alpha)
            elif inter.geom_type == "MultiLineString":
                for seg in inter.geoms:
                    sx, sy = seg.xy; ax.plot(sx, sy, color=color, lw=lw, alpha=alpha)
        r += step_km

def farthest_to_bbox_km(lon0, lat0):
    corners = [(LON_MIN,LAT_MIN),(LON_MIN,LAT_MAX),(LON_MAX,LAT_MIN),(LON_MAX,LAT_MAX)]
    return max(float(haversine_km(lon0,lat0,cx,cy)) for (cx,cy) in corners)

# plotting
def _plot_center_marker(ax, x, y, label=None):
    ax.scatter([x],[y], s=36, marker="o", facecolor="#e41a1c", edgecolor="black", linewidths=0.8)
    if label: ax.text(x+0.004, y+0.004, label, fontsize=10, color="black")

def plot_region(idx, poly, lines, A, CCI, center, out_png, Xg, Yg):
    extent=(LON_MIN, LON_MAX, LAT_MIN, LAT_MAX)
    fig, ax = plt.subplots(figsize=(8,7))
    im = ax.imshow(np.power(np.clip(A,0,None),GAMMA_VIS), origin="upper",
                   extent=extent, cmap="Reds")
    plt.colorbar(im, ax=ax, fraction=0.035, pad=0.02, label="VIIRS radiance (gamma view)")
    xs,ys = poly.exterior.xy; ax.plot(xs,ys,lw=2.0,color="black")
    for ln in lines:
        if ln is None: continue
        if ln.geom_type=="MultiLineString":
            for seg in ln.geoms: xs,ys = seg.xy; ax.plot(xs,ys,"k-",lw=1.6,alpha=0.9)
        else:
            xs,ys = ln.xy; ax.plot(xs,ys,"k-",lw=1.6,alpha=0.9)
    max_km = farthest_to_bbox_km(center[0], center[1])
    draw_concentric_rings_clipped(ax, center[0], center[1], REGION_RING_STEP_KM, max_km, RECT,
                                  color=REGION_RING_COLOR, lw=REGION_RING_LW, alpha=REGION_RING_ALPHA)
    if CCI is not None:
        ax.contour(Xg, Yg, CCI, levels=[0.25,0.5,0.75,0.9], linewidths=0.8, colors="k", alpha=0.35)
    _plot_center_marker(ax, center[0], center[1], None)
    ax.set_xlim(LON_MIN, LON_MAX); ax.set_ylim(LAT_MIN, LAT_MAX)
    ax.set_title(f"Region {idx}: center via inverse-S best-fit (clipped single-center rings)")
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    fig.tight_layout(); fig.savefig(out_png, dpi=300); plt.close(fig)

def plot_overall(polys, lines, centers, A, Xg, Yg):
    extent=(LON_MIN, LON_MAX, LAT_MIN, LAT_MAX)
    fig, ax = plt.subplots(figsize=(9,7.6))
    im = ax.imshow(np.power(np.clip(A,0,None),GAMMA_VIS), origin="upper",
                   extent=extent, cmap="Reds")
    plt.colorbar(im, ax=ax, fraction=0.035, pad=0.02, label="VIIRS radiance (gamma view)")
    for poly in polys:
        xs,ys = poly.exterior.xy; ax.plot(xs,ys,lw=2.0,color="black")
    for ln in lines:
        if ln is None: continue
        if ln.geom_type=="MultiLineString":
            for seg in ln.geoms: xs,ys = seg.xy; ax.plot(xs,ys,"k-",lw=1.8,alpha=0.95)
        else:
            xs,ys = ln.xy; ax.plot(xs,ys,"k-",lw=1.8,alpha=0.95)
    if centers:
        dist_stack = [haversine_km(Xg, Yg, lonc, latc) for (lonc, latc) in centers]
        dist_min = np.minimum.reduce(dist_stack)
        maxR = np.nanmax(dist_min)
        levels = np.arange(RING_FIELD_STEP_KM, maxR + 1e-9, RING_FIELD_STEP_KM)
        ax.contour(Xg, Yg, dist_min, levels=levels, colors=RING_FIELD_COLOR,
                   linewidths=RING_FIELD_LW, alpha=RING_FIELD_ALPHA)
    for i,c in enumerate(centers,1): _plot_center_marker(ax, c[0], c[1], f"C{i}")
    ax.set_xlim(LON_MIN, LON_MAX); ax.set_ylim(LAT_MIN, LAT_MAX)
    ax.set_title("All regions — centers")
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    fig.tight_layout(); fig.savefig("wuhan_regions_overall.png", dpi=300); plt.close(fig)

#  PIXEL-level CCI
def pixel_linear_cci(centers, Xg, Yg):
    if not centers:
        H,W = Xg.shape
        return np.zeros((H,W),dtype=np.float32), []
    per_center = []
    for (lonc, latc) in centers:
        d = haversine_km(Xg, Yg, lonc, latc)
        Rmax = farthest_to_bbox_km(lonc, latc)
        c = 1.0 - d / max(Rmax, 1e-6)
        per_center.append(np.clip(c, 0.0, 1.0).astype(np.float32))
    cci_max = np.maximum.reduce(per_center)
    return cci_max, per_center

def save_pixel_cci(cci_max, per_center, Xg, Yg, tfm, crs_str, centers):
    H,W = cci_max.shape
    cols = ["lon","lat","cci_max"] + [f"cci_c{i+1}" for i in range(len(per_center))]
    data = {"lon": Xg.ravel(), "lat": Yg.ravel(), "cci_max": cci_max.ravel()}
    for i,ci in enumerate(per_center,1): data[f"cci_c{i}"] = ci.ravel()
    pd.DataFrame(data)[cols].to_csv("cci_grid_linear.csv", index=False, float_format="%.6f")
    with rasterio.open("cci_grid_linear.tif", "w", driver="GTiff",
                       height=H, width=W, count=1, dtype="float32",
                       crs=crs_str, transform=tfm, nodata=0.0, compress="deflate") as dst:
        dst.write(cci_max.astype("float32"), 1)
    fig, ax = plt.subplots(figsize=(9,7.6))
    extent=(LON_MIN, LON_MAX, LAT_MIN, LAT_MAX)
    im = ax.imshow(cci_max, origin="upper", extent=extent, cmap="Reds", vmin=0, vmax=1)
    plt.colorbar(im, ax=ax, fraction=0.035, pad=0.02, label="CCI (linear, max over centers) — pixel grid")
    regions, lines = build_four_regions()
    for ln in lines:
        if ln is None: continue
        if ln.geom_type=="MultiLineString":
            for seg in ln.geoms:
                xs,ys = seg.xy; ax.plot(xs,ys,"k-",lw=1.6,alpha=0.9)
        else:
            xs,ys = ln.xy; ax.plot(xs,ys,"k-",lw=1.6,alpha=0.9)
    ax.set_xlim(LON_MIN, LON_MAX); ax.set_ylim(LAT_MIN, LAT_MAX)
    for i,(x,y) in enumerate([(c[0],c[1]) for c in centers],1):
        ax.scatter([x],[y], s=36, marker="o", facecolor="#e41a1c", edgecolor="black", linewidths=0.8)
        ax.text(x+0.004, y+0.004, f"C{i}", fontsize=10, color="black")
    ax.set_title("Pixel CCI — linear distance-decay (max over 4 centers)")
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    fig.tight_layout(); fig.savefig("cci_grid_linear.png", dpi=300); plt.close(fig)

# GRID-level CCI 
def build_regular_grid_centers():
    # row 0 at top (LAT_MAX), col 0 at LON_MIN
    x_centers = LON_MIN + (np.arange(NX) + 0.5) * GRID_DX
    y_centers_top = LAT_MAX - (np.arange(NY) + 0.5) * GRID_DY
    Xc, Yc = np.meshgrid(x_centers, y_centers_top)  # shape (NY, NX)
    return Xc, Yc

def grid_linear_cci_on_regular(centers, Xc, Yc):
    if not centers:
        return np.zeros_like(Xc, dtype=np.float32), []
    per_center = []
    for (lonc, latc) in centers:
        d = haversine_km(Xc, Yc, lonc, latc)
        Rmax = farthest_to_bbox_km(lonc, latc)
        c = 1.0 - d / max(Rmax, 1e-6)
        per_center.append(np.clip(c, 0.0, 1.0).astype(np.float32))
    cci_max = np.maximum.reduce(per_center)
    return cci_max, per_center

def save_grid_cci_regular(centers, Xc, Yc, cci_max, per_center):
    # CSV with grid indices and center (lon,lat)
    gy_from_row = np.arange(NY)  # row index from top
    grid_y = (NY - 1 - gy_from_row)[:, None] * np.ones((1, NX), dtype=int)
    grid_x = np.arange(NX)[None, :].repeat(NY, axis=0)

    grid_lon = Xc
    grid_lat = Yc
    dom_idx = np.argmax(np.stack(per_center, axis=0), axis=0) + 1  # 1..4

    df = pd.DataFrame({
        "grid_id": (grid_y * NX + grid_x).ravel().astype(int),
        "grid_x": grid_x.ravel().astype(int),
        "grid_y": grid_y.ravel().astype(int),
        "grid_lon": grid_lon.ravel(),
        "grid_lat": grid_lat.ravel(),
        "cci_max": cci_max.ravel(),
        "dom_center": dom_idx.ravel().astype(int)
    })
    for i,ci in enumerate(per_center,1):
        df[f"cci_c{i}"] = ci.ravel()
    cols = ["grid_id","grid_x","grid_y","grid_lon","grid_lat","cci_max","dom_center"] + [f"cci_c{i}" for i in range(1, len(per_center)+1)]
    df[cols].to_csv("cci_grid_linear_grid.csv", index=False, float_format="%.6f")

    # GeoTIFF
    tfm_grid = Affine(GRID_DX, 0, LON_MIN, 0, -GRID_DY, LAT_MAX)
    with rasterio.open("cci_grid_linear_grid.tif", "w", driver="GTiff",
                       height=NY, width=NX, count=1, dtype="float32",
                       crs="EPSG:4326", transform=tfm_grid, nodata=0.0, compress="deflate") as dst:
        dst.write(cci_max.astype("float32"), 1)

    # PNG
    fig, ax = plt.subplots(figsize=(9,7.6))
    extent=(LON_MIN, LON_MAX, LAT_MIN, LAT_MAX)
    im = ax.imshow(cci_max, origin="upper", extent=extent, cmap="Reds", vmin=0, vmax=1)
    plt.colorbar(im, ax=ax, fraction=0.035, pad=0.02, label="CCI (linear, max over 4 centers) — 1-km grid")
    regions, lines = build_four_regions()
    for ln in lines:
        if ln is None: continue
        if ln.geom_type=="MultiLineString":
            for seg in ln.geoms:
                xs,ys = seg.xy; ax.plot(xs,ys,"k-",lw=1.6,alpha=0.9)
        else:
            xs,ys = ln.xy; ax.plot(xs,ys,"k-",lw=1.6,alpha=0.9)
    # centers
    for i,(x,y) in enumerate(centers,1):
        ax.scatter([x],[y], s=36, marker="o", facecolor="#e41a1c", edgecolor="black", linewidths=0.8)
        ax.text(x+0.004, y+0.004, f"C{i}", fontsize=10, color="black")
    ax.set_xlim(LON_MIN, LON_MAX); ax.set_ylim(LAT_MIN, LAT_MAX)
    ax.set_title("Grid CCI — linear distance-decay (max over 4 centers)  [with grid_id]")
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    fig.tight_layout(); fig.savefig("cci_grid_linear_grid.png", dpi=300); plt.close(fig)

# main
def main():
    A, tfm, crs_str, Xg, Yg = load_viirs_subwindow()
    regions, lines = build_four_regions()

    centers=[]; rows=[]; cci_rows=[]

    for i,poly in enumerate(regions,1):
        center, CCI, mask, _, fit, rmax_norm = compute_center_and_cci(poly, A, Xg, Yg, tfm)
        print(f"[ok] Region {i} center = ({center[0]:.6f}, {center[1]:.6f})")
        plot_region(i, poly, lines, A, CCI, center, f"region_{i}.png", Xg, Yg)
        centers.append(center)
        rows.append({"region_id":i,"center_lon":center[0],"center_lat":center[1]})
        if fit is not None and rmax_norm is not None:
            alpha, cpar, Dpar = fit["alpha"], fit["c"], fit["D"]
            def invS(rr): return 1.0 - cpar / (1.0 + np.exp(alpha*(2.0*rr/Dpar - 1.0))) + cpar
            r_profile = np.arange(0.0, max(RING_BIN_KM, rmax_norm)+1e-9, RING_BIN_KM)
            y0_hat, yD_hat = invS(0.0), invS(rmax_norm)
            den = (y0_hat - yD_hat) if (y0_hat - yD_hat) != 0 else 1.0
            cci_hat = np.clip((invS(r_profile) - yD_hat)/den, 0.0, 1.0)
            r_obs, nli_obs = fit["r"], fit["nli"]
            if len(r_obs) >= 2:
                nli_interp = np.interp(r_profile, r_obs, nli_obs, left=nli_obs[0], right=nli_obs[-1])
            else:
                nli_interp = np.full_like(r_profile, np.nan, dtype=float)
            for rk, ck, nk in zip(r_profile, cci_hat, nli_interp):
                cci_rows.append({
                    "region_id": i,
                    "center_lon": center[0],
                    "center_lat": center[1],
                    "r_km": round(float(rk), 3),
                    "cci_hat": round(float(ck), 6),
                    "nli_obs": round(float(nk), 6) if np.isfinite(nk) else np.nan
                })

    pd.DataFrame(rows).to_csv("regional_centers.csv", index=False, float_format="%.6f")
    if len(cci_rows) > 0:
        pd.DataFrame(cci_rows).to_csv("cci_profiles.csv", index=False)

    # overall fig
    plot_overall(regions, lines, centers, A, Xg, Yg)

    # 1) pixel-level CCI
    cci_max_px, per_center_px = pixel_linear_cci(centers, Xg, Yg)
    save_pixel_cci(cci_max_px, per_center_px, Xg, Yg, tfm, crs_str, centers)

    # 2) regular 1-km GRID CCI
    Xc, Yc = build_regular_grid_centers()
    cci_max_grid, per_center_grid = grid_linear_cci_on_regular(centers, Xc, Yc)
    save_grid_cci_regular(centers, Xc, Yc, cci_max_grid, per_center_grid)

    print("[done] regional_centers.csv, cci_profiles.csv, region_1~4.png, "
          "wuhan_regions_overall.png, cci_grid_linear.csv/.tif/.png (pixel), "
          "cci_grid_linear_grid.csv/.tif/.png (1-km grid with grid_id)")

if __name__=="__main__":
    main()
