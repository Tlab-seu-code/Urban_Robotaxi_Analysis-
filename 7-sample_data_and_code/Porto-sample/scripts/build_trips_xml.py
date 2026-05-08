from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DAILY_DIR = PROJECT_ROOT / "process" / "daily"
OUT_DIR = PROJECT_ROOT / "process" / "trips_xml"
START_SEC_CLIP = (0, 86399)


def write_trips_xml(df: pd.DataFrame, out_path: Path):
    with out_path.open("w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write("<routes>\n")
        for row in df.itertuples(index=False):
            trip_id = escape(str(row.trajectory_id))
            depart = int(row.sec)
            if depart < START_SEC_CLIP[0]:
                depart = START_SEC_CLIP[0]
            if depart > START_SEC_CLIP[1]:
                depart = START_SEC_CLIP[1]
            f.write(
                f'  <trip id="{trip_id}" depart="{depart}" '
                f'fromLonLat="{row.from_lon},{row.from_lat}" '
                f'toLonLat="{row.to_lon},{row.to_lat}" />\n'
            )
        f.write("</routes>\n")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(
        f for f in DAILY_DIR.iterdir()
        if f.is_file() and f.name.lower().endswith(".csv") and f.name.startswith("porto_")
    )
    for path in files:
        df = pd.read_csv(path)
        need = ["trajectory_id", "sec", "from_lon", "from_lat", "to_lon", "to_lat"]
        df = df[need].dropna().copy()
        out_xml = OUT_DIR / path.name.replace(".csv", ".trips.xml")
        write_trips_xml(df, out_xml)
        print(f"[OK] {path.name} -> {out_xml} (n={len(df)})")


if __name__ == "__main__":
    main()
