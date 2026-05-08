import argparse
import csv
import os

from sample_settings import (
    AV_ROU_DIR,
    HV_ROU_DIR,
    NET_FILE,
    RATIOS,
    SAMPLE_ROOT,
    SIMULATION_END,
    parse_ratios,
    rel_to_sample,
)


DEBUG_MODE = 0
RATE = 1


SCENARIOS = {
    "av": {
        "output_dir": AV_ROU_DIR,
        "cfg_prefix": "av",
        "stats_prefix": "vehicle_stats_aggregated_av",
    },
    "hv": {
        "output_dir": HV_ROU_DIR,
        "cfg_prefix": "hdv",
        "stats_prefix": "vehicle_stats_aggregated_hv",
    },
}


def update_speed(traci, non_internal_edges, speed):
    for edge in non_internal_edges:
        traci.edge.setMaxSpeed(edge, speed)
    print(f"Speed limit updated to {speed} m/s")


def run_simulation(scenario, ratio, debug_mode=DEBUG_MODE):
    import sumolib
    import traci

    settings = SCENARIOS[scenario]
    output_dir = settings["output_dir"]
    cfg_file = output_dir / f"{settings['cfg_prefix']}_{ratio}.sumocfg"
    output_file = output_dir / f"{settings['stats_prefix']}_{ratio}.csv"

    if not cfg_file.exists():
        raise FileNotFoundError(
            f"Missing config file: {rel_to_sample(cfg_file)}. "
            "Run generate_sumocfg_sample.py first."
        )
    if not NET_FILE.exists():
        raise FileNotFoundError(f"Missing network file: {rel_to_sample(NET_FILE)}")

    old_cwd = os.getcwd()
    os.chdir(SAMPLE_ROOT)
    try:
        sumo_cmd = [
            "sumo-gui" if debug_mode else "sumo",
            "-c",
            rel_to_sample(cfg_file),
            "--emission-output.geo",
            "True",
        ]

        traci.start(sumo_cmd)
        net = sumolib.net.readNet(rel_to_sample(NET_FILE))

        all_edges = traci.edge.getIDList()
        non_internal_edges = [edge for edge in all_edges if not edge.startswith(":")]
        vehicle_stats = {}

        with open(rel_to_sample(output_file), "w", newline="", encoding="utf-8") as f:
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

            while (t := traci.simulation.getTime()) <= SIMULATION_END:
                if int(t) % 3600 == 0:
                    print(f"t = {t}")

                if t == 10:
                    update_speed(traci, non_internal_edges, 12 * RATE)
                if t == 10 + 3600 * 7:
                    update_speed(traci, non_internal_edges, 8 * RATE)
                if t == 10 + 3600 * 10:
                    update_speed(traci, non_internal_edges, 10 * RATE)
                if t == 10 + 3600 * 17:
                    update_speed(traci, non_internal_edges, 8 * RATE)
                if t == 10 + 3600 * 20:
                    update_speed(traci, non_internal_edges, 10 * RATE)
                if t == 10 + 3600 * 22:
                    update_speed(traci, non_internal_edges, 12 * RATE)

                for vehicle_id in traci.vehicle.getIDList():
                    if vehicle_id not in vehicle_stats:
                        vehicle_type = traci.vehicle.getTypeID(vehicle_id)
                        vehicle_stats[vehicle_id] = {
                            "vehicle_type": vehicle_type,
                            "depart": traci.vehicle.getDeparture(vehicle_id),
                            "electricity": 0.0,
                            "fuel": 0.0,
                            "co2": 0.0,
                        }

                    vehicle_type = vehicle_stats[vehicle_id]["vehicle_type"]
                    is_electric = any(
                        key in vehicle_type.lower() for key in ("bev", "hev_e", "fox")
                    )

                    if is_electric:
                        vehicle_stats[vehicle_id]["electricity"] += (
                            traci.vehicle.getElectricityConsumption(vehicle_id) / 1000.0
                        )
                    else:
                        vehicle_stats[vehicle_id]["fuel"] += (
                            traci.vehicle.getFuelConsumption(vehicle_id) / 1000.0
                        )
                        vehicle_stats[vehicle_id]["co2"] += (
                            traci.vehicle.getCO2Emission(vehicle_id) / 1000.0
                        )

                for vehicle_id in traci.simulation.getArrivedIDList():
                    if vehicle_id in vehicle_stats:
                        stats = vehicle_stats.pop(vehicle_id)
                        arrival = t
                        writer.writerow(
                            [
                                vehicle_id,
                                stats["vehicle_type"],
                                f"{stats['depart']:.1f}",
                                f"{arrival:.1f}",
                                f"{arrival - stats['depart']:.1f}",
                                f"{stats['electricity']:.4f}",
                                f"{stats['fuel']:.2f}",
                                f"{stats['co2']:.2f}",
                            ]
                        )

                traci.simulationStep()

        traci.close()
        print(f"Output complete: {rel_to_sample(output_file)}")
    finally:
        os.chdir(old_cwd)

def main():
    parser = argparse.ArgumentParser(description="Run SUMO simulation for sample routes.")
    parser.add_argument("--scenario", choices=("av", "hv", "both"), default="both")
    parser.add_argument("--ratios", nargs="*", help="Ratios to simulate, e.g. 10 20 30")
    parser.add_argument("--debug-gui", action="store_true")
    args = parser.parse_args()

    ratios = parse_ratios(args.ratios) if args.ratios else RATIOS
    scenarios = ("av", "hv") if args.scenario == "both" else (args.scenario,)
    for scenario in scenarios:
        for ratio in ratios:
            print(f"=== Start {scenario.upper()} {ratio}% ===")
            run_simulation(scenario, ratio, debug_mode=1 if args.debug_gui else DEBUG_MODE)
            print(f"=== Done {scenario.upper()} {ratio}% ===")


if __name__ == "__main__":
    main()
