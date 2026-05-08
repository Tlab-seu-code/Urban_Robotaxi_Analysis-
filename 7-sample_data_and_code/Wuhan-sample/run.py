import argparse
import shutil
import sys
from pathlib import Path

SAMPLE_ROOT = Path(__file__).resolve().parent
CODE_DIR = SAMPLE_ROOT / "code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from add_relocation_sample import batch_process_scenario
from generate_routes_sample import batch_create_routes_for_scenario
from generate_sumocfg_sample import batch_generate_sumocfg
from sample_settings import OUTPUT_DIR, RATIOS, ensure_output_dirs, parse_ratios, rel_to_sample
from split_by_vehicle_sample import split_csv_by_vehicle


def clean_outputs():
    output_dir = OUTPUT_DIR.resolve()
    sample_root = OUTPUT_DIR.parent.resolve()

    if output_dir == sample_root or sample_root not in output_dir.parents:
        raise RuntimeError(f"Refusing to clean unsafe output directory: {output_dir}")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    ensure_output_dirs()
    print(f"Cleaned: {rel_to_sample(OUTPUT_DIR)}")


def run_pipeline(ratios, scenarios, clean=True, with_simulation=False):
    if clean:
        clean_outputs()
    else:
        ensure_output_dirs()

    print("Stage 1/4: split by vehicle")
    split_csv_by_vehicle(ratios=ratios)

    print("Stage 2/4: add empty relocation trips")
    for scenario in scenarios:
        batch_process_scenario(scenario, ratios=ratios)

    print("Stage 3/4: generate SUMO routes")
    for scenario in scenarios:
        batch_create_routes_for_scenario(scenario, ratios=ratios)

    print("Stage 4/4: generate SUMO configs")
    for scenario in scenarios:
        batch_generate_sumocfg(scenario, ratios=ratios)

    if with_simulation:
        from run_simulation_sample import run_simulation

        print("Stage 5/5: run SUMO simulations")
        for scenario in scenarios:
            for ratio in ratios:
                print(f"=== Start {scenario.upper()} {ratio}% ===")
                run_simulation(scenario, ratio)
                print(f"=== Done {scenario.upper()} {ratio}% ===")

    print("Sample experiment finished.")


def main():
    parser = argparse.ArgumentParser(description="One-command runner for the sample experiment.")
    parser.add_argument("--scenario", choices=("av", "hv", "both"), default="both")
    parser.add_argument("--ratios", nargs="*", help="Ratios to run, for example: 10 20 30")
    parser.add_argument(
        "--with-simulation",
        action="store_true",
        help="Run SUMO simulations after generating routes and configs.",
    )
    parser.add_argument(
        "--keep-outputs",
        action="store_true",
        help="Do not clean sample/outputs before running.",
    )
    args = parser.parse_args()

    ratios = parse_ratios(args.ratios) if args.ratios else RATIOS
    scenarios = ("av", "hv") if args.scenario == "both" else (args.scenario,)
    run_pipeline(
        ratios=ratios,
        scenarios=scenarios,
        clean=not args.keep_outputs,
        with_simulation=args.with_simulation,
    )


if __name__ == "__main__":
    main()
