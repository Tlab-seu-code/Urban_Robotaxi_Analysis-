import argparse
import uuid

import pandas as pd

from sample_settings import (
    AV_PROCESSED_DIR,
    HV_PROCESSED_DIR,
    SPLIT_OUTPUT_DIR,
    ensure_output_dirs,
    parse_ratios,
    rel_to_sample,
)


REQUIRED_COLUMNS = [
    "order_id",
    "start_lon",
    "start_lat",
    "end_lon",
    "end_lat",
    "start_time",
    "end_time",
    "vehicle_id",
]


SCENARIOS = {
    "av": ("*_av.csv", AV_PROCESSED_DIR),
    "hv": ("*_hv.csv", HV_PROCESSED_DIR),
}


def process_taxi_orders(input_file, output_file):
    """Insert empty relocation trips between consecutive orders of the same vehicle."""
    df = pd.read_csv(input_file)

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])
    df = df.sort_values(["vehicle_id", "start_time"])

    processed_orders = []
    empty_rides_count = 0

    for vehicle_id, group in df.groupby("vehicle_id"):
        group = group.sort_values("start_time").reset_index(drop=True)
        if group.empty:
            continue

        processed_orders.append(group.iloc[0].to_dict())

        for i in range(1, len(group)):
            prev_order = group.iloc[i - 1]
            curr_order = group.iloc[i]

            prev_end_time = prev_order["end_time"]
            curr_start_time = curr_order["start_time"]

            if (
                curr_start_time > prev_end_time
                and (
                    prev_order["end_lon"] != curr_order["start_lon"]
                    or prev_order["end_lat"] != curr_order["start_lat"]
                )
            ):
                empty_ride = {column: pd.NA for column in df.columns}
                empty_ride.update(
                    {
                        "order_id": f"{vehicle_id}_{uuid.uuid4().hex[:16]}",
                        "start_lon": prev_order["end_lon"],
                        "start_lat": prev_order["end_lat"],
                        "end_lon": curr_order["start_lon"],
                        "end_lat": curr_order["start_lat"],
                        "start_time": prev_end_time,
                        "end_time": curr_start_time,
                        "vehicle_id": vehicle_id,
                    }
                )
                processed_orders.append(empty_ride)
                empty_rides_count += 1

            processed_orders.append(curr_order.to_dict())

    result_df = pd.DataFrame(processed_orders, columns=df.columns)
    result_df = result_df.sort_values("start_time").reset_index(drop=True)
    result_df.to_csv(output_file, index=False, encoding="utf-8-sig")

    print(f"Processed: {rel_to_sample(input_file)}")
    print(f"  original rows: {len(df)}")
    print(f"  empty relocation rows: {empty_rides_count}")
    print(f"  output rows: {len(result_df)}")
    print(f"  vehicles: {df['vehicle_id'].nunique()}")
    print(f"  output: {rel_to_sample(output_file)}")


def batch_process_scenario(scenario, ratios=None):
    pattern, output_dir = SCENARIOS[scenario]
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(SPLIT_OUTPUT_DIR.glob(pattern))
    if ratios:
        ratio_tokens = {f"_{ratio}_{scenario}.csv" for ratio in ratios}
        files = [path for path in files if any(token in path.name for token in ratio_tokens)]

    if not files:
        print(f"No {scenario.upper()} split files found in {rel_to_sample(SPLIT_OUTPUT_DIR)}")
        return

    for input_file in files:
        output_file = output_dir / input_file.name.replace(".csv", "_processed.csv")
        process_taxi_orders(input_file, output_file)


def main():
    parser = argparse.ArgumentParser(description="Add relocation trips to split samples.")
    parser.add_argument("--scenario", choices=("av", "hv", "both"), default="both")
    parser.add_argument("--ratios", nargs="*", help="Ratios to process, e.g. 10 20 30")
    args = parser.parse_args()

    ensure_output_dirs()
    ratios = parse_ratios(args.ratios) if args.ratios else None
    scenarios = ("av", "hv") if args.scenario == "both" else (args.scenario,)
    for scenario in scenarios:
        batch_process_scenario(scenario, ratios=ratios)


if __name__ == "__main__":
    main()
