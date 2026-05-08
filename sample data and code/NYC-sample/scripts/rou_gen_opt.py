# -*- coding: utf-8 -*-
"""
Generate SUMO route files for penetration-rate experiments from a route cache.

The default inputs preserve the existing 2024-11-01 experiment. Command-line
arguments make it easy to create a one-day sample in a separate output folder.
"""

import argparse
import os
import random
import shutil
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree as ET

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE_FILE = str(ROOT / "data" / "nyc_20241101_route_cache.csv")
DEFAULT_OUT_DIR = str(ROOT / "runs" / "rou_20241101_multi_penetration_cached")
DEFAULT_DATE_LABEL = "20241101"
DEFAULT_PENETRATIONS = list(range(0, 101, 10))
DEFAULT_BASE_SEED = 42
DEFAULT_VTYPE_FILE = str(ROOT / "data" / "basic.vtype.xml")

HV_VEHICLE_TYPES = {
    "hv_camry_fuel": 0.616,
    "hv_rav4_fuel": 0.264,
    "hv_model3_ev": 0.0972,
    "hv_modely_ev": 0.0228,
}
AV_VEHICLE_TYPES = {"robotaxi_ipace": 1.0}

SUMOCFG_TEMPLATE = """<configuration>
    <input>
        <net-file value="{net_file}"/>
        <route-files value="{route_file}"/>
        <additional-files value="{additional_file}"/>
    </input>
    <time>
        <begin value="{begin}"/>
        <step-length value="{step_length}"/>
        <end value="{end}"/>
    </time>
</configuration>
"""


def parse_penetrations(value):
    if not value:
        return DEFAULT_PENETRATIONS

    penetrations = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        percent = int(part)
        if percent < 0 or percent > 100:
            raise argparse.ArgumentTypeError(
                f"Penetration must be between 0 and 100: {percent}"
            )
        penetrations.append(percent)

    if not penetrations:
        raise argparse.ArgumentTypeError("No valid penetration values supplied")
    return penetrations


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate penetration-rate .rou.xml and .sumocfg files."
    )
    parser.add_argument("--cache-file", default=DEFAULT_CACHE_FILE)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--date-label", default=DEFAULT_DATE_LABEL)
    parser.add_argument(
        "--penetrations",
        type=parse_penetrations,
        default=DEFAULT_PENETRATIONS,
        help="Comma-separated percentages, e.g. 0,10,20,...,100.",
    )
    parser.add_argument("--base-seed", type=int, default=DEFAULT_BASE_SEED)
    parser.add_argument(
        "--vtype-file",
        default=DEFAULT_VTYPE_FILE,
        help="Vehicle type XML copied into the output folder as basic.vtype.xml.",
    )
    parser.add_argument(
        "--sumocfg-net-file",
        default="../../net/osm.net.xml",
        help="Net-file path written inside generated .sumocfg files.",
    )
    parser.add_argument("--begin", type=int, default=0)
    parser.add_argument("--end", type=int, default=86400)
    parser.add_argument("--step-length", type=float, default=1)
    parser.add_argument(
        "--max-orders",
        type=int,
        help="Optional smoke-test limit. Omit it for the full one-day sample.",
    )
    parser.add_argument(
        "--skip-sumocfg",
        action="store_true",
        help="Only write .rou.xml files.",
    )
    return parser.parse_args()


def weighted_choice(weights):
    return random.choices(list(weights.keys()), list(weights.values()))[0]


def route_filename(date_label, percent):
    return f"nyc_{date_label}_penetration_{percent}_cached.rou.xml"


def copy_vtype_file(src, out_dir):
    if not src:
        return "basic.vtype.xml"

    dst = os.path.join(out_dir, "basic.vtype.xml")
    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copyfile(src, dst)
    return os.path.basename(dst)


def write_sumocfg(out_dir, percent, route_file, net_file, additional_file, args):
    cfg_content = SUMOCFG_TEMPLATE.format(
        net_file=net_file,
        route_file=route_file,
        additional_file=additional_file,
        begin=args.begin,
        step_length=args.step_length,
        end=args.end,
    )
    cfg_file = os.path.join(out_dir, f"{percent}.sumocfg")
    with open(cfg_file, "w", encoding="utf-8") as f:
        f.write(cfg_content)
    return cfg_file


def build_routes(df, percent, seed):
    random.seed(seed)
    p = percent / 100.0
    root = ET.Element("routes")

    total = len(df)
    for done, row in enumerate(df.itertuples(index=False), start=1):
        if done == 1 or done % 1000 == 0:
            print(f"[PROGRESS] {done}/{total}")

        if random.random() < p:
            vtype = weighted_choice(AV_VEHICLE_TYPES)
        else:
            vtype = weighted_choice(HV_VEHICLE_TYPES)

        veh = ET.SubElement(
            root,
            "vehicle",
            id=f"veh_{row.order_id}",
            type=vtype,
            depart=str(int(row.depart)),
        )
        ET.SubElement(veh, "route", edges=row.route_edges)

    return root


def main():
    args = parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    df = pd.read_csv(args.cache_file)
    required = {"order_id", "depart", "route_edges"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Route cache missing columns: {sorted(missing)}")

    df = df.sort_values("depart").reset_index(drop=True)
    if args.max_orders:
        df = df.head(args.max_orders).copy()

    print(f"[INFO] loaded {len(df)} cached routes from {args.cache_file}")
    additional_file = copy_vtype_file(args.vtype_file, args.out_dir)

    for percent in args.penetrations:
        print(f"\n[INFO] penetration={percent}%")
        root = build_routes(df, percent, args.base_seed + percent)
        xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")

        rou_name = route_filename(args.date_label, percent)
        rou_path = os.path.join(args.out_dir, rou_name)
        with open(rou_path, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"[DONE] {rou_path}")

        if not args.skip_sumocfg:
            cfg_path = write_sumocfg(
                args.out_dir,
                percent,
                rou_name,
                args.sumocfg_net_file,
                additional_file,
                args,
            )
            print(f"[DONE] {cfg_path}")

    print("\n[ALL DONE]")


if __name__ == "__main__":
    main()
