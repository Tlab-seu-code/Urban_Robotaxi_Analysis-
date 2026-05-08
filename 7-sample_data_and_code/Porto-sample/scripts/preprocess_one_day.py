from pathlib import Path
import re

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "porto_trajectories_20131128.csv"
OUT_DIR = PROJECT_ROOT / "process" / "daily"
START_DATE = "2013-11-28"
END_DATE = "2013-11-28"

POINT_RE = re.compile(r"POINT\(\s*([-\d\.]+)\s+([-\d\.]+)\s*\)")


def extract_lonlat(series: pd.Series):
    tmp = series.astype(str).str.extract(POINT_RE)
    lon = tmp[0].astype(float)
    lat = tmp[1].astype(float)
    return lon, lat


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(
        CSV_PATH,
        usecols=["taxi_id", "trajectory_id", "timestamp", "source_point", "target_point"],
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).copy()

    start = pd.to_datetime(START_DATE)
    end = pd.to_datetime(END_DATE) + pd.Timedelta(days=1)
    df = df[(df["timestamp"] >= start) & (df["timestamp"] < end)].copy()

    slon, slat = extract_lonlat(df["source_point"])
    tlon, tlat = extract_lonlat(df["target_point"])
    df["from_lon"], df["from_lat"] = slon, slat
    df["to_lon"], df["to_lat"] = tlon, tlat
    df = df.dropna(subset=["from_lon", "from_lat", "to_lon", "to_lat"]).copy()

    df["date"] = df["timestamp"].dt.strftime("%Y%m%d")
    df["sec"] = (df["timestamp"] - df["timestamp"].dt.floor("D")).dt.total_seconds().astype(int)

    for day, group in df.groupby("date"):
        out = group[
            ["trajectory_id", "taxi_id", "timestamp", "sec", "from_lon", "from_lat", "to_lon", "to_lat"]
        ].copy()
        out = out.sort_values("sec")
        out_path = OUT_DIR / f"porto_{day}.csv"
        out.to_csv(out_path, index=False)
        print(f"[OK] {day}: trips={len(out)} -> {out_path}")


if __name__ == "__main__":
    main()
