# -*- coding: utf-8 -*-
"""
Map NYC taxi orders to nearest SUMO edges.

Default behavior keeps the original dataset/output. Pass --date to build a
one-day sample without editing the script.
"""

import argparse
import os
from pathlib import Path

import pandas as pd
import sumolib


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NET_FILE = str(ROOT / "net" / "osm_sim.net.xml")
DEFAULT_ORDER_FILE = str(ROOT / "data" / "yellow_orders_20241101_sample.csv")
DEFAULT_OUTPUT_DIR = str(ROOT / "data" / "daily_orders_with_sumo")
DEFAULT_DATE = "2024-11-01"
DATE_COL = "start_time"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Attach nearest SUMO start/end edges to NYC order records."
    )
    parser.add_argument("--net-file", default=DEFAULT_NET_FILE)
    parser.add_argument("--order-file", default=DEFAULT_ORDER_FILE)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--date",
        default=DEFAULT_DATE,
        help="Only process one day, e.g. 2024-11-01.",
    )
    parser.add_argument(
        "--radius",
        type=float,
        default=1500.0,
        help="Neighboring-edge search radius in meters.",
    )
    return parser.parse_args()


def find_nearest_edge(net, x, y, radius):
    try:
        candidates = net.getNeighboringEdges(x, y, radius)
    except Exception:
        return None, -1.0

    if not candidates:
        return None, -1.0

    edge, _ = min(candidates, key=lambda e: e[1])

    fx, fy = edge.getFromNode().getCoord()
    tx, ty = edge.getToNode().getCoord()
    edge_len = edge.getLength()

    vx, vy = tx - fx, ty - fy
    wx, wy = x - fx, y - fy
    denom = vx * vx + vy * vy
    if denom == 0:
        return edge.getID(), 0.0

    proj = (vx * wx + vy * wy) / denom
    proj = max(0.0, min(1.0, proj))
    return edge.getID(), proj * edge_len


def process_day(net, df_day, date, output_dir, radius):
    print(f"\nProcessing date: {date}, orders: {len(df_day)}")

    df_day = df_day.copy()
    df_day["start_edge_id"] = None
    df_day["end_edge_id"] = None
    df_day["start_edge_pos"] = -1.0
    df_day["end_edge_pos"] = -1.0

    total = len(df_day)
    for done, (idx, row) in enumerate(df_day.iterrows(), start=1):
        if done == 1 or done % 100 == 0:
            print(f"  {done}/{total}")

        try:
            sx, sy = net.convertLonLat2XY(row["start_lon"], row["start_lat"])
            ex, ey = net.convertLonLat2XY(row["end_lon"], row["end_lat"])
        except Exception:
            continue

        s_edge, s_pos = find_nearest_edge(net, sx, sy, radius)
        e_edge, e_pos = find_nearest_edge(net, ex, ey, radius)

        df_day.at[idx, "start_edge_id"] = s_edge
        df_day.at[idx, "start_edge_pos"] = s_pos
        df_day.at[idx, "end_edge_id"] = e_edge
        df_day.at[idx, "end_edge_pos"] = e_pos

    df_day = df_day[
        df_day["start_edge_id"].notna() & df_day["end_edge_id"].notna()
    ]

    date_str = pd.to_datetime(date).strftime("%Y%m%d")
    out_file = os.path.join(
        output_dir,
        f"nyc_orders_{date_str}_with_sumo_edges.csv",
    )

    df_day.to_csv(out_file, index=False, encoding="utf-8-sig")
    print(f"Saved: {out_file} ({len(df_day)} mapped orders)")


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    net = sumolib.net.readNet(args.net_file)
    df = pd.read_csv(args.order_file)

    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df = df[df[DATE_COL].notna()].copy()
    df["date"] = df[DATE_COL].dt.date

    if args.date:
        target_date = pd.to_datetime(args.date).date()
        df = df[df["date"] == target_date].copy()
        if df.empty:
            raise ValueError(f"No orders found for {args.date}")

    for date, df_day in df.groupby("date"):
        process_day(net, df_day, date, args.output_dir, args.radius)

    print("\nAll requested days processed.")


if __name__ == "__main__":
    main()
