# -*- coding: utf-8 -*-
"""
Build a route cache from a one-day order-with-SUMO-edges CSV.

This is the executable version of the routing step that was previously kept as
commented code in rou_gen_opt.py.
"""

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
import traci


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_FILE = str(
    ROOT / "data" / "daily_orders_with_sumo" / "nyc_orders_20241101_with_sumo_edges.csv"
)
DEFAULT_NET_FILE = str(ROOT / "net" / "osm.net.xml")
DEFAULT_OUT_CACHE = str(ROOT / "data" / "nyc_20241101_route_cache.csv")
DEFAULT_DATE = "2024-11-01"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create route cache CSV by routing mapped orders through SUMO."
    )
    parser.add_argument("--csv-file", default=DEFAULT_CSV_FILE)
    parser.add_argument("--net-file", default=DEFAULT_NET_FILE)
    parser.add_argument("--out-cache", default=DEFAULT_OUT_CACHE)
    parser.add_argument(
        "--date",
        default=DEFAULT_DATE,
        help="Filter by day, e.g. 2024-11-01.",
    )
    parser.add_argument("--sumo-binary", default="sumo")
    parser.add_argument(
        "--max-orders",
        type=int,
        help="Optional smoke-test limit. Omit it for the full one-day sample.",
    )
    return parser.parse_args()


def depart_seconds(start_time):
    t = datetime.strptime(str(start_time), "%Y-%m-%d %H:%M:%S")
    midnight = t.replace(hour=0, minute=0, second=0, microsecond=0)
    return int((t - midnight).total_seconds())


def main():
    args = parse_args()
    df = pd.read_csv(args.csv_file)
    df["date"] = pd.to_datetime(df["start_time"], errors="coerce").dt.strftime(
        "%Y-%m-%d"
    )

    if args.date:
        df = df[df["date"] == args.date].copy()
        if df.empty:
            raise ValueError(f"No orders found for {args.date}")

    if args.max_orders:
        df = df.head(args.max_orders).copy()

    total = len(df)
    print(f"[INFO] total orders: {total}")

    records = []
    traci.start([args.sumo_binary, "-n", args.net_file, "--start"])
    try:
        for done, row in enumerate(df.itertuples(index=False), start=1):
            if done == 1 or done % 100 == 0:
                print(f"[PROGRESS] routing {done}/{total}")

            order_id = row.order_id
            start_edge = row.start_edge_id
            end_edge = row.end_edge_id

            try:
                depart = depart_seconds(row.start_time)
                if depart < 0:
                    print(f"[SKIP][TIME] {order_id}")
                    continue
            except Exception:
                print(f"[SKIP][TIME] {order_id}")
                continue

            if pd.isna(start_edge) or pd.isna(end_edge):
                print(f"[SKIP][EDGE] {order_id}")
                continue

            try:
                stage = traci.simulation.findRoute(
                    fromEdge=start_edge,
                    toEdge=end_edge,
                    depart=depart,
                    routingMode=0,
                )
                if not stage.edges:
                    print(f"[SKIP][ROUTE] {order_id}")
                    continue
                route_edges = " ".join(stage.edges)
            except Exception as exc:
                print(f"[SKIP][ROUTE] {order_id} -> {exc}")
                continue

            records.append(
                {
                    "order_id": order_id,
                    "depart": depart,
                    "route_edges": route_edges,
                }
            )
    finally:
        traci.close()

    print(f"[INFO] valid routes: {len(records)} / {total}")
    pd.DataFrame(records).to_csv(args.out_cache, index=False)
    print(f"[DONE] route cache saved to {args.out_cache}")


if __name__ == "__main__":
    main()
