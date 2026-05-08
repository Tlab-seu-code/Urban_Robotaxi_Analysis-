from pathlib import Path
import csv
import glob
import math
import os
import re
import sys


try:
    import traci
except ImportError:
    sumo_home = os.environ.get("SUMO_HOME")
    if sumo_home:
        sys.path.append(str(Path(sumo_home) / "tools"))
    import traci


PROJECT_ROOT = Path(__file__).resolve().parent

SUMO = os.environ.get("SUMO_BINARY", "sumo")
NET = PROJECT_ROOT / "net" / "robust.net.xml"
VTYPES = PROJECT_ROOT / "process" / "vtypes" / "porto.vtype.xml"
ROUTE_ROOT = PROJECT_ROOT / "process" / "routes_by_p"
OUT_ROOT = PROJECT_ROOT / "output"
DATE_TAG = "20131128"

BEGIN = 0
END = 200000
STEP_LEN = 1.0
SEED = 42

FUEL_ENERGY_DENSITY = 44_000
ELECTRICITY_TO_J = 3_600_000
CARBON_FACTOR = 522.0

OVERWRITE = True


def safe_read(getter, vid: str) -> float:
    try:
        x = float(getter(vid))
    except Exception:
        return 0.0
    if (not math.isfinite(x)) or (x < 0):
        return 0.0
    return x


def mode_of(vtype_id: str) -> str:
    return "robotaxi" if vtype_id == "robotaxi" else "hv"


def parse_p_from_folder(folder_name: str) -> float:
    return float(folder_name[1:])


def parse_date_from_route(route_path: str) -> str:
    match = re.search(r"porto_(\d{8})_p\d+\.\d{2}\.rou\.xml$", Path(route_path).name)
    if not match:
        raise ValueError(f"Cannot parse date from route filename: {route_path}")
    return match.group(1)


def run_one(route_path: Path, p: float, date: str) -> dict:
    p_tag = f"p{p:.2f}"
    out_dir = OUT_ROOT / p_tag / date
    out_dir.mkdir(parents=True, exist_ok=True)

    detail_csv = out_dir / "energy_emissions_vehicle.csv"
    agg_csv = out_dir / "energy_emissions_agg.csv"

    if (not OVERWRITE) and detail_csv.exists() and agg_csv.exists():
        hv = {"fuel_J": 0.0, "electricity_J": 0.0, "co2_g_final": 0.0}
        rb = {"fuel_J": 0.0, "electricity_J": 0.0, "co2_g_final": 0.0}
        with agg_csv.open("r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["mode"] == "hv":
                    hv = {k: float(row[k]) for k in hv}
                elif row["mode"] == "robotaxi":
                    rb = {k: float(row[k]) for k in rb}

        return {
            "date": date,
            "p": p,
            "hv_fuel_J": hv["fuel_J"],
            "hv_electricity_J": hv["electricity_J"],
            "hv_co2_g_final": hv["co2_g_final"],
            "robotaxi_fuel_J": rb["fuel_J"],
            "robotaxi_electricity_J": rb["electricity_J"],
            "robotaxi_co2_g_final": rb["co2_g_final"],
            "total_energy_J": hv["fuel_J"] + rb["electricity_J"],
            "total_co2_g": hv["co2_g_final"] + rb["co2_g_final"],
        }

    cmd = [
        SUMO,
        "-n", str(NET),
        "-r", str(route_path),
        "-a", str(VTYPES),
        "--begin", str(BEGIN),
        "--end", str(END),
        "--step-length", str(STEP_LEN),
        "--seed", str(SEED),
        "--device.emissions.probability", "1",
        "--device.battery.probability", "1",
        "--time-to-teleport", "900",
        "--no-step-log", "true",
    ]

    fuel_mg = {}
    elec_Wh = {}
    co2_mg = {}
    vtype = {}

    try:
        traci.start(cmd)

        def ensure(vid: str):
            if vid not in fuel_mg:
                fuel_mg[vid] = 0.0
                elec_Wh[vid] = 0.0
                co2_mg[vid] = 0.0
                try:
                    vtype[vid] = traci.vehicle.getTypeID(vid)
                except Exception:
                    vtype[vid] = "unknown"

        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            for vid in traci.vehicle.getIDList():
                ensure(vid)
                fuel_mg[vid] += safe_read(traci.vehicle.getFuelConsumption, vid) * STEP_LEN
                elec_Wh[vid] += safe_read(traci.vehicle.getElectricityConsumption, vid) * STEP_LEN
                co2_mg[vid] += safe_read(traci.vehicle.getCO2Emission, vid) * STEP_LEN
    finally:
        try:
            traci.close()
        except Exception:
            pass

    with detail_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "veh_id", "mode",
            "fuel_mg", "electricity_Wh", "co2_mg",
            "fuel_J", "electricity_J", "co2_g_final",
        ])

        for vid in fuel_mg.keys():
            mode = mode_of(vtype.get(vid, "unknown"))
            fuel_g = fuel_mg[vid] / 1000.0
            fuel_J = fuel_g * FUEL_ENERGY_DENSITY
            elec_kWh = elec_Wh[vid] / 1000.0
            elec_J = elec_kWh * ELECTRICITY_TO_J
            co2_g = co2_mg[vid] / 1000.0
            if mode == "robotaxi" and (co2_g == 0.0) and (elec_kWh > 0):
                co2_g = elec_kWh * CARBON_FACTOR
            writer.writerow([vid, mode, fuel_mg[vid], elec_Wh[vid], co2_mg[vid], fuel_J, elec_J, co2_g])

    agg = {
        "hv": {"fuel_mg": 0.0, "elec_Wh": 0.0, "co2_mg": 0.0},
        "robotaxi": {"fuel_mg": 0.0, "elec_Wh": 0.0, "co2_mg": 0.0},
    }
    for vid in fuel_mg.keys():
        mode = mode_of(vtype.get(vid, "unknown"))
        agg[mode]["fuel_mg"] += fuel_mg[vid]
        agg[mode]["elec_Wh"] += elec_Wh[vid]
        agg[mode]["co2_mg"] += co2_mg[vid]

    out_summary = {"date": date, "p": p}

    with agg_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["mode", "fuel_mg", "electricity_Wh", "co2_mg", "fuel_J", "electricity_J", "co2_g_final"])

        for mode in ["hv", "robotaxi"]:
            fuel_g = agg[mode]["fuel_mg"] / 1000.0
            elec_kWh = agg[mode]["elec_Wh"] / 1000.0
            fuel_J = fuel_g * FUEL_ENERGY_DENSITY
            elec_J = elec_kWh * ELECTRICITY_TO_J
            co2_g = agg[mode]["co2_mg"] / 1000.0
            if mode == "robotaxi" and (co2_g == 0.0) and (elec_kWh > 0):
                co2_g = elec_kWh * CARBON_FACTOR

            writer.writerow([mode, agg[mode]["fuel_mg"], agg[mode]["elec_Wh"], agg[mode]["co2_mg"], fuel_J, elec_J, co2_g])
            out_summary[f"{mode}_fuel_J"] = fuel_J
            out_summary[f"{mode}_electricity_J"] = elec_J
            out_summary[f"{mode}_co2_g_final"] = co2_g

    out_summary["total_energy_J"] = out_summary.get("hv_fuel_J", 0.0) + out_summary.get("robotaxi_electricity_J", 0.0)
    out_summary["total_co2_g"] = out_summary.get("hv_co2_g_final", 0.0) + out_summary.get("robotaxi_co2_g_final", 0.0)
    return out_summary


def main():
    p_dirs = []
    for child in ROUTE_ROOT.iterdir():
        if child.is_dir() and re.fullmatch(r"p\d+\.\d{2}", child.name):
            p_dirs.append(child.name)
    p_dirs = sorted(p_dirs, key=parse_p_from_folder)

    if not p_dirs:
        raise RuntimeError(f"No p-folders found under {ROUTE_ROOT}")

    total_jobs = 0
    for pdir in p_dirs:
        files = sorted(glob.glob(str(ROUTE_ROOT / pdir / f"porto_{DATE_TAG}_{pdir}.rou.xml")))
        if len(files) == 0:
            print(f"[Warn] {pdir}: no route files found, skipped.")
            continue
        total_jobs += len(files)

    summary_rows = []
    job_i = 0
    for pdir in p_dirs:
        p = parse_p_from_folder(pdir)
        route_files = sorted(glob.glob(str(ROUTE_ROOT / pdir / f"porto_{DATE_TAG}_{pdir}.rou.xml")))
        for route_file in route_files:
            route_path = Path(route_file)
            date = parse_date_from_route(route_file)
            job_i += 1
            print(f"[Run {job_i}/{total_jobs}] {pdir} {date} -> {route_path.name}")
            summary_rows.append(run_one(route_path, p, date))

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    summary_csv = OUT_ROOT / "energy_emissions_summary.csv"
    fields = [
        "date", "p",
        "hv_fuel_J", "hv_electricity_J", "hv_co2_g_final",
        "robotaxi_fuel_J", "robotaxi_electricity_J", "robotaxi_co2_g_final",
        "total_energy_J", "total_co2_g",
    ]
    with summary_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in summary_rows:
            for key in fields:
                row.setdefault(key, 0.0)
            writer.writerow(row)

    print("[OK] wrote summary:", summary_csv)
    print("[OK] done.")


if __name__ == "__main__":
    main()
