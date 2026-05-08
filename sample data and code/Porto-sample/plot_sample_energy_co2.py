from pathlib import Path
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
OUT_ROOT = PROJECT_ROOT / "output"
AGG_METHOD = "sum"

CARBON_FACTOR = 351.7
FUEL_ENERGY_DENSITY_J_PER_G = 44_000
SYSTEM_ELEC_KWH_BASE = 0.0

FIG_OUT = OUT_ROOT / "fig_d_porto_sample.png"
DPI = 100

FUEL_BAR_COLOR = "#FEC79E"
ELEC_BAR_COLOR = "#8EC4CB"
ENERGY_LINE_COLOR = "#45819B"
CO2_LINE_COLOR = "#F39967"


def parse_p(pdir: str) -> float:
    return float(pdir[1:])


def get_first(df: pd.DataFrame, col: str, default: float = 0.0) -> float:
    if df is None or len(df) == 0 or col not in df.columns:
        return default
    try:
        return float(df[col].iloc[0])
    except Exception:
        return default


def compute_fuel_kJ(hv: pd.DataFrame, rb: pd.DataFrame) -> float:
    if ("fuel_mg" in hv.columns) or ("fuel_mg" in rb.columns):
        hv_fuel_mg = get_first(hv, "fuel_mg", 0.0)
        rb_fuel_mg = get_first(rb, "fuel_mg", 0.0)
        fuel_g = (hv_fuel_mg + rb_fuel_mg) / 1000.0
        fuel_J = fuel_g * FUEL_ENERGY_DENSITY_J_PER_G
        return fuel_J / 1000.0
    hv_fuel_J = get_first(hv, "fuel_J", 0.0)
    rb_fuel_J = get_first(rb, "fuel_J", 0.0)
    return (hv_fuel_J + rb_fuel_J) / 1000.0


def compute_elec_kWh(hv: pd.DataFrame, rb: pd.DataFrame) -> float:
    if ("electricity_Wh" in hv.columns) or ("electricity_Wh" in rb.columns):
        hv_elec_Wh = get_first(hv, "electricity_Wh", 0.0)
        rb_elec_Wh = get_first(rb, "electricity_Wh", 0.0)
        return (hv_elec_Wh + rb_elec_Wh) / 1000.0 + SYSTEM_ELEC_KWH_BASE
    hv_elec_J = get_first(hv, "electricity_J", 0.0)
    rb_elec_J = get_first(rb, "electricity_J", 0.0)
    return (hv_elec_J + rb_elec_J) / 3_600_000.0 + SYSTEM_ELEC_KWH_BASE


def compute_hv_tailpipe_g(hv: pd.DataFrame) -> float:
    if "co2_mg" in hv.columns:
        return get_first(hv, "co2_mg", 0.0) / 1000.0
    return get_first(hv, "co2_g_final", 0.0)


def build_daily_table(out_root: Path) -> pd.DataFrame:
    rows = []
    pdirs = [
        child for child in out_root.iterdir()
        if child.is_dir() and re.fullmatch(r"p\d+\.\d{2}", child.name)
    ]
    pdirs = sorted(pdirs, key=lambda p: parse_p(p.name))

    for pdir in pdirs:
        p = parse_p(pdir.name)
        files = sorted(pdir.glob("*/energy_emissions_agg.csv"))
        for path in files:
            date = path.parent.name
            df = pd.read_csv(path)
            hv = df[df["mode"] == "hv"]
            rb = df[df["mode"] == "robotaxi"]

            fuel_kJ = compute_fuel_kJ(hv, rb)
            elec_kWh = compute_elec_kWh(hv, rb)
            elec_kJ = elec_kWh * 3600.0
            total_energy_kJ = fuel_kJ + elec_kJ

            hv_tailpipe_g = compute_hv_tailpipe_g(hv)
            elec_co2_g = elec_kWh * CARBON_FACTOR
            total_co2_ton = (hv_tailpipe_g + elec_co2_g) / 1_000_000.0

            rows.append({
                "p": p,
                "date": date,
                "fuel_kJ": fuel_kJ,
                "elec_kJ": elec_kJ,
                "total_energy_kJ": total_energy_kJ,
                "total_co2_ton": total_co2_ton,
            })

    if not rows:
        raise RuntimeError(f"No agg files found under: {out_root}/p*/YYYYMMDD/energy_emissions_agg.csv")
    return pd.DataFrame(rows)


def discrete_inflection_idx(y: np.ndarray):
    if len(y) < 5:
        return None
    d2 = np.diff(y, n=2)
    idx = 1 + int(np.argmax(np.abs(d2)))
    if idx <= 0 or idx >= len(y) - 1:
        return None
    return idx


def set_rcparams_like_example():
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "font.size": 18,
        "axes.labelsize": 20,
        "xtick.labelsize": 18,
        "ytick.labelsize": 18,
        "legend.fontsize": 18,
        "axes.linewidth": 1.8,
        "legend.frameon": False,
    })


def main():
    set_rcparams_like_example()

    df = build_daily_table(OUT_ROOT)
    agg_func = np.sum if AGG_METHOD.lower() == "sum" else np.mean
    dfp = (
        df.groupby("p", as_index=False)
        .agg(
            fuel_kJ=("fuel_kJ", agg_func),
            elec_kJ=("elec_kJ", agg_func),
            total_energy_kJ=("total_energy_kJ", agg_func),
            total_co2_ton=("total_co2_ton", agg_func),
        )
        .sort_values("p")
        .reset_index(drop=True)
    )

    x = (dfp["p"].values * 100).round().astype(int)

    fig, ax = plt.subplots(figsize=(14, 8.35), dpi=DPI)
    ax2 = ax.twinx()

    ax.tick_params(axis="both", which="major", length=10, width=2.4, direction="out", pad=10)
    ax2.tick_params(axis="y", which="major", length=10, width=2.4, direction="out", pad=10)
    for spine in ax.spines.values():
        spine.set_linewidth(1.8)
    for spine in ax2.spines.values():
        spine.set_linewidth(1.8)

    width = 3.2
    offset = 1.8
    bar_fuel = ax.bar(
        x - offset,
        dfp["fuel_kJ"].values,
        width=width,
        color=FUEL_BAR_COLOR,
        alpha=0.85,
        label="Fuel energy",
        zorder=1,
    )
    bar_elec = ax.bar(
        x + offset,
        dfp["elec_kJ"].values,
        width=width,
        color=ELEC_BAR_COLOR,
        alpha=0.85,
        label="Electric energy",
        zorder=1,
    )

    line_co2, = ax2.plot(
        x,
        dfp["total_co2_ton"].values,
        color=CO2_LINE_COLOR,
        linestyle="--",
        marker="D",
        markersize=6.5,
        linewidth=2.0,
        label="Total CO$_2$",
        zorder=3,
    )

    line_energy, = ax.plot(
        x,
        dfp["total_energy_kJ"].values,
        color=ENERGY_LINE_COLOR,
        linestyle="-",
        marker="o",
        markersize=6.5,
        linewidth=2.2,
        label="Total energy",
        zorder=3,
    )

    idx_c = discrete_inflection_idx(dfp["total_co2_ton"].values)
    idx_e = discrete_inflection_idx(dfp["total_energy_kJ"].values)

    star_c = None
    star_e = None
    if idx_c is not None:
        star_c = ax2.scatter(
            [x[idx_c]],
            [dfp["total_co2_ton"].values[idx_c]],
            marker="*",
            s=380,
            color=CO2_LINE_COLOR,
            label="Total CO$_2$ inflection",
            zorder=5,
        )
    if idx_e is not None:
        star_e = ax.scatter(
            [x[idx_e]],
            [dfp["total_energy_kJ"].values[idx_e]],
            marker="*",
            s=380,
            color=ENERGY_LINE_COLOR,
            label="Total energy inflection",
            zorder=5,
        )

    ax.set_xlabel("AV penetration (%)")
    ax.set_ylabel("Total energy consumption (kJ)")
    ax2.set_ylabel("Total CO$_2$ emissions (ton)")

    ax.set_xticks(x)
    ax.set_xlim(-5, 105)

    ymax = ax2.get_ylim()[1]
    ax2.set_ylim(0, ymax * 1.2)

    ax.ticklabel_format(style="sci", axis="y", scilimits=(0, 0))
    ax2.ticklabel_format(style="sci", axis="y", scilimits=(0, 0))

    handles = [line_co2, line_energy]
    labels = ["Total CO$_2$", "Total energy"]
    if star_c is not None:
        handles.append(star_c)
        labels.append("Total CO$_2$ inflection")
    if star_e is not None:
        handles.append(star_e)
        labels.append("Total energy inflection")
    handles.extend([bar_fuel, bar_elec])
    labels.extend(["Fuel energy", "Electric energy"])

    ax.legend(handles, labels, loc="upper right", frameon=False, handlelength=2.8, borderaxespad=0.8)
    ax.grid(False)
    ax2.grid(False)

    plt.subplots_adjust(left=0.09, right=0.91, bottom=0.14, top=0.92)
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    plt.savefig(FIG_OUT)
    plt.close()

    print("[OK] saved:", FIG_OUT)
    print(f"[INFO] plotting factors: CARBON_FACTOR={CARBON_FACTOR} g/kWh, FUEL_ENERGY_DENSITY={FUEL_ENERGY_DENSITY_J_PER_G} J/g")
    print("[INFO] x(%):", x.tolist())


if __name__ == "__main__":
    main()
