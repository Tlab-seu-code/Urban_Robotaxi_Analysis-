# -*- coding: utf-8 -*-
"""
Run SUMO penetration-rate simulations and write vehicle-level aggregates.

Defaults match the existing 2024-11-01 experiment folder. Use --run-dir,
--penetrations, and --end to run a smaller or relocated sample.
"""

import argparse
import csv
import os
from pathlib import Path

import sumolib
import traci


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = str(ROOT / "runs" / "rou_20241101_multi_penetration_cached")
DEFAULT_NET_FILE = "../../net/osm.net.xml"
DEFAULT_SIMULATION_END = 86400
DEFAULT_PENETRATIONS = list(range(0, 101, 10))
DEFAULT_RATE = 1.0


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
        description="Run generated SUMO configs for penetration-rate experiments."
    )
    parser.add_argument("--run-dir", default=DEFAULT_RUN_DIR)
    parser.add_argument(
        "--net-file",
        default=DEFAULT_NET_FILE,
        help="Network path relative to --run-dir unless absolute.",
    )
    parser.add_argument("--end", type=int, default=DEFAULT_SIMULATION_END)
    parser.add_argument("--rate", type=float, default=DEFAULT_RATE)
    parser.add_argument(
        "--penetrations",
        type=parse_penetrations,
        default=DEFAULT_PENETRATIONS,
        help="Comma-separated percentages, e.g. 0,10,20,...,100.",
    )
    parser.add_argument("--debug", action="store_true", help="Use sumo-gui.")
    parser.add_argument(
        "--sumo-binary",
        help="Override SUMO binary. Defaults to sumo or sumo-gui with --debug.",
    )
    parser.add_argument(
        "--output-prefix",
        default="vehicle_stats_aggregated_hv",
        help="Prefix for generated aggregate CSV files.",
    )
    return parser.parse_args()


def update_speed(non_internal_edges, speed):
    for edge in non_internal_edges:
        traci.edge.setMaxSpeed(edge, speed)
    print(f"Speed limit updated to {speed} m/s")


def is_electric_type(veh_type):
    text = veh_type.lower()
    return any(
        token in text
        for token in (
            "ev",
            "ipace",
            "bev",
            "electric",
            "model3",
            "modely",
        )
    )


def run_simulation(pre, args):
    cfg_file = f"{pre}.sumocfg"
    if not os.path.exists(cfg_file):
        raise FileNotFoundError(f"Missing SUMO config: {cfg_file}")

    sumo_binary = args.sumo_binary or ("sumo-gui" if args.debug else "sumo")
    sumo_cmd = [
        sumo_binary,
        "-c",
        cfg_file,
        "--emission-output.geo",
        "True",
    ]

    traci.start(sumo_cmd)
    try:
        net = sumolib.net.readNet(args.net_file)
        all_edges = traci.edge.getIDList()
        non_internal_edges = [edge for edge in all_edges if not edge.startswith(":")]

        veh_stats = {}
        output_file = f"{args.output_prefix}_{pre}.csv"

        with open(output_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "vehicle_id",
                    "vehicle_type",
                    "depart_time(s)",
                    "arrival_time(s)",
                    "travel_time(s)",
                    "electricity(kWh)",
                    "fuel(g)",
                    "co2(g)",
                ]
            )

            speed_schedule = {
                10: 12 * args.rate,
                10 + 3600 * 7: 8 * args.rate,
                10 + 3600 * 10: 10 * args.rate,
                10 + 3600 * 17: 8 * args.rate,
                10 + 3600 * 20: 10 * args.rate,
                10 + 3600 * 22: 12 * args.rate,
            }

            while (t := traci.simulation.getTime()) <= args.end:
                if int(t) % 3600 == 0:
                    print(f"t = {t}")

                if t in speed_schedule:
                    update_speed(non_internal_edges, speed_schedule[t])

                for veh_id in traci.vehicle.getIDList():
                    if veh_id not in veh_stats:
                        veh_type = traci.vehicle.getTypeID(veh_id)
                        veh_stats[veh_id] = {
                            "veh_type": veh_type,
                            "depart": traci.vehicle.getDeparture(veh_id),
                            "electricity": 0.0,
                            "fuel": 0.0,
                            "co2": 0.0,
                        }

                    veh_type = veh_stats[veh_id]["veh_type"]
                    if is_electric_type(veh_type):
                        veh_stats[veh_id]["electricity"] += (
                            traci.vehicle.getElectricityConsumption(veh_id) / 1000.0
                        )
                    else:
                        veh_stats[veh_id]["fuel"] += (
                            traci.vehicle.getFuelConsumption(veh_id) / 1000.0
                        )
                        veh_stats[veh_id]["co2"] += (
                            traci.vehicle.getCO2Emission(veh_id) / 1000.0
                        )

                for veh_id in traci.simulation.getArrivedIDList():
                    if veh_id in veh_stats:
                        s = veh_stats.pop(veh_id)
                        arrival = t
                        writer.writerow(
                            [
                                veh_id,
                                s["veh_type"],
                                f"{s['depart']:.1f}",
                                f"{arrival:.1f}",
                                f"{arrival - s['depart']:.1f}",
                                f"{s['electricity']:.4f}",
                                f"{s['fuel']:.2f}",
                                f"{s['co2']:.2f}",
                            ]
                        )

                traci.simulationStep()

        print(f"Output complete: {output_file}")
    finally:
        traci.close()


def main():
    args = parse_args()
    run_dir = os.path.abspath(args.run_dir)
    if not os.path.isdir(run_dir):
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    os.chdir(run_dir)
    print("Current directory:", os.getcwd())

    if not os.path.exists(args.net_file):
        raise FileNotFoundError(f"Network file not found: {args.net_file}")

    for pre in args.penetrations:
        print(f"\n=== Start simulation av_{pre} ===")
        run_simulation(pre, args)
        print(f"=== Finished simulation av_{pre} ===\n")


if __name__ == "__main__":
    main()
