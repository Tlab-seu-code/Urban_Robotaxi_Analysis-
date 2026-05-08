import argparse
import csv
import os
import random
import re
from datetime import datetime
from xml.dom import minidom
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd
import sumolib

from sample_settings import (
    AV_PROCESSED_DIR,
    AV_ROU_DIR,
    AV_TYPES,
    END_HOUR,
    HV_PROCESSED_DIR,
    HV_ROU_DIR,
    HV_TYPES,
    NET_FILE,
    RANDOM_STATE,
    RATIOS,
    SAMPLE_DATE,
    SEARCH_RADIUS,
    START_HOUR,
    ensure_output_dirs,
    parse_ratios,
    rel_to_sample,
)


SCENARIOS = {
    "av": {
        "processed_dir": AV_PROCESSED_DIR,
        "output_dir": AV_ROU_DIR,
        "patterns": ("*_av_processed.csv", "*_av.csv"),
        "rou_prefix": "taxis_av",
        "vehicle_types": AV_TYPES,
    },
    "hv": {
        "processed_dir": HV_PROCESSED_DIR,
        "output_dir": HV_ROU_DIR,
        "patterns": ("*_hv_processed.csv", "*_hv.csv"),
        "rou_prefix": "taxis_hv",
        "vehicle_types": HV_TYPES,
    },
}


def generate_vehicle_id(order_id):
    return str(order_id)[1:]


def normalize_date(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if "-" in text:
        parsed = pd.to_datetime(text, errors="coerce")
        if not pd.isna(parsed):
            return parsed.strftime("%Y%m%d")
    return text


def load_network(net_file):
    if not net_file.exists():
        raise FileNotFoundError(f"Network file not found: {rel_to_sample(net_file)}")
    return sumolib.net.readNet(str(net_file))


def find_nearest_edge(net, lon, lat, search_radius=100):
    try:
        x, y = net.convertLonLat2XY(float(lon), float(lat))
        candidate_edges = net.getNeighboringEdges(x, y, search_radius)
        if not candidate_edges:
            return None
        return min(candidate_edges, key=lambda edge: edge[1])[0].getID()
    except Exception as exc:
        print(f"Coordinate conversion failed ({lon}, {lat}): {exc}")
        return None


def calculate_route(net, origin_edge, destination_edge):
    try:
        path = net.getShortestPath(
            net.getEdge(origin_edge),
            net.getEdge(destination_edge),
            vClass="passenger",
        )[0]
        return [edge.getID() for edge in path] if path else None
    except sumolib.SumoException:
        return None


def create_route_file(
    input_csv,
    target_date,
    net_file,
    output_file,
    vehicle_types=None,
    search_radius=100,
    random_state=RANDOM_STATE,
):
    random.seed(random_state)
    np.random.seed(random_state)
    if hasattr(pd, "util") and hasattr(pd.util, "_random"):
        pd.util._random.seed(random_state)

    vehicle_types = vehicle_types or {"elysee_cng": 1.0}
    total_weight = sum(vehicle_types.values())
    if total_weight <= 0:
        raise ValueError("Invalid vehicle type weights.")

    type_names = list(vehicle_types.keys())
    type_weights = [weight / total_weight for weight in vehicle_types.values()]

    net = load_network(net_file)
    valid_orders = []

    with open(input_csv, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        matching_rows = [
            row for row in reader if normalize_date(row.get("date")) == target_date
        ]

    print(f"Routing {len(matching_rows)} rows from {rel_to_sample(input_csv)}")

    for idx, row in enumerate(matching_rows):
        try:
            vehicle_id = generate_vehicle_id(row["order_id"])
        except KeyError:
            print(f"Missing order_id: {row}")
            continue

        try:
            depart_time = datetime.strptime(row["start_time"], "%Y-%m-%d %H:%M:%S")
            base_time = depart_time.replace(hour=0, minute=0, second=0, microsecond=0)
            depart_seconds = int((depart_time - base_time).total_seconds())
            if depart_seconds < 0:
                continue
        except Exception:
            print(f"Invalid start_time: {row.get('start_time')}")
            continue

        origin_edge = find_nearest_edge(
            net, row.get("start_lon"), row.get("start_lat"), search_radius
        )
        dest_edge = find_nearest_edge(
            net, row.get("end_lon"), row.get("end_lat"), search_radius
        )
        if not origin_edge or not dest_edge:
            print(
                f"Order {row.get('order_id')} edge match failed "
                f"(origin: {origin_edge}, dest: {dest_edge})"
            )
            continue

        route = calculate_route(net, origin_edge, dest_edge)
        if not route:
            print(f"Order {row.get('order_id')} has no valid route")
            continue

        selected_type = random.choices(type_names, weights=type_weights, k=1)[0]
        valid_orders.append(
            {
                "vid": vehicle_id,
                "depart": depart_seconds,
                "route": route,
                "vtype": selected_type,
            }
        )

        if (idx + 1) % 100 == 0:
            print(f"Processed {idx + 1}/{len(matching_rows)} rows")

    valid_orders.sort(key=lambda order: order["depart"])

    root = ET.Element("routes")
    for order in valid_orders:
        vehicle = ET.SubElement(
            root,
            "vehicle",
            id=order["vid"],
            type=order["vtype"],
            depart=str(order["depart"]),
        )
        ET.SubElement(vehicle, "route", edges=" ".join(order["route"]))

    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"Generated {len(valid_orders)} vehicles: {rel_to_sample(output_file)}")


def prepare_for_routing(input_file, output_dir, target_date, start_hour, end_hour):
    df = pd.read_csv(input_file, dtype=str)
    if "start_time" not in df.columns:
        raise ValueError(f"Missing start_time in {rel_to_sample(input_file)}")

    if "date" not in df.columns or df["date"].isnull().any():
        df["date"] = pd.to_datetime(df["start_time"], errors="coerce").dt.strftime("%Y%m%d")
    else:
        df["date"] = df["date"].map(normalize_date)

    df = df[df["date"] == target_date].copy()
    df["dt"] = pd.to_datetime(df["start_time"], errors="coerce")
    df = df[(df["dt"].dt.hour >= start_hour) & (df["dt"].dt.hour < end_hour)]
    df = df.drop(columns=["dt"])

    if df.empty:
        return None

    tmp_csv = output_dir / f"tmp_for_rou_{input_file.name}"
    df.to_csv(tmp_csv, index=False, encoding="utf-8-sig")
    return tmp_csv


def batch_create_routes_for_scenario(
    scenario,
    ratios=RATIOS,
    target_date=SAMPLE_DATE,
    search_radius=SEARCH_RADIUS,
    start_hour=START_HOUR,
    end_hour=END_HOUR,
    random_state=RANDOM_STATE,
):
    settings = SCENARIOS[scenario]
    processed_dir = settings["processed_dir"]
    output_dir = settings["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    files = []
    for pattern in settings["patterns"]:
        files.extend(processed_dir.glob(pattern))
    files = sorted(set(files))

    if ratios:
        ratio_tokens = {f"_{ratio}_{scenario}" for ratio in ratios}
        files = [path for path in files if any(token in path.name for token in ratio_tokens)]

    if not files:
        print(f"No {scenario.upper()} processed files found in {rel_to_sample(processed_dir)}")
        return

    for input_file in files:
        match = re.search(fr"_(\d+)_{scenario}", input_file.name)
        ratio = match.group(1) if match else "unknown"

        tmp_csv = prepare_for_routing(
            input_file=input_file,
            output_dir=output_dir,
            target_date=target_date,
            start_hour=start_hour,
            end_hour=end_hour,
        )
        if tmp_csv is None:
            print(f"No data in requested window: {rel_to_sample(input_file)}")
            continue

        output_rou = output_dir / f"{settings['rou_prefix']}_{ratio}.rou.xml"
        try:
            create_route_file(
                input_csv=tmp_csv,
                target_date=target_date,
                net_file=NET_FILE,
                output_file=output_rou,
                vehicle_types=settings["vehicle_types"],
                search_radius=search_radius,
                random_state=random_state,
            )
        finally:
            try:
                os.remove(tmp_csv)
            except OSError:
                pass


def main():
    parser = argparse.ArgumentParser(description="Generate SUMO route files.")
    parser.add_argument("--scenario", choices=("av", "hv", "both"), default="both")
    parser.add_argument("--ratios", nargs="*", help="Ratios to process, e.g. 10 20 30")
    parser.add_argument("--search-radius", type=int, default=SEARCH_RADIUS)
    parser.add_argument("--start-hour", type=int, default=START_HOUR)
    parser.add_argument("--end-hour", type=int, default=END_HOUR)
    parser.add_argument("--random-state", type=int, default=RANDOM_STATE)
    args = parser.parse_args()

    ensure_output_dirs()
    ratios = parse_ratios(args.ratios) if args.ratios else RATIOS
    scenarios = ("av", "hv") if args.scenario == "both" else (args.scenario,)
    for scenario in scenarios:
        batch_create_routes_for_scenario(
            scenario=scenario,
            ratios=ratios,
            search_radius=args.search_radius,
            start_hour=args.start_hour,
            end_hour=args.end_hour,
            random_state=args.random_state,
        )


if __name__ == "__main__":
    main()
