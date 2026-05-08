import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd

from sample_settings import (
    DAILY_TRAJ_FILE,
    RANDOM_STATE,
    RATIOS,
    SPLIT_OUTPUT_DIR,
    ensure_output_dirs,
    parse_ratios,
    rel_to_sample,
)


def split_csv_by_vehicle(
    input_file=DAILY_TRAJ_FILE,
    ratios=RATIOS,
    output_dir=SPLIT_OUTPUT_DIR,
    random_state=RANDOM_STATE,
):
    """Split one-day taxi orders by vehicle_id for AV and HV samples.

    This mirrors the existing workflow:
    - AV ratio p uses the first p% vehicles from a fixed shuffled vehicle list.
    - HV ratio p uses the remaining p% vehicles from a complementary split.
    """
    input_file = Path(input_file)
    output_dir = Path(output_dir)
    ensure_output_dirs()
    output_dir.mkdir(parents=True, exist_ok=True)

    random.seed(random_state)
    np.random.seed(random_state)
    if hasattr(pd, "util") and hasattr(pd.util, "_random"):
        pd.util._random.seed(random_state)

    df = pd.read_csv(input_file)
    if "vehicle_id" not in df.columns:
        raise ValueError("CSV file does not contain required column: vehicle_id")

    vehicle_ids = df["vehicle_id"].drop_duplicates().tolist()
    random.shuffle(vehicle_ids)
    vehicle_count = len(vehicle_ids)
    base_name = input_file.stem

    print(f"Input: {rel_to_sample(input_file)}")
    print(f"Rows: {len(df)}, vehicles: {vehicle_count}")

    for ratio in ratios:
        av_count = int(vehicle_count * ratio / 100)
        hv_start = int(vehicle_count * (100 - ratio) / 100)

        av_ids = set(vehicle_ids[:av_count])
        hv_ids = set(vehicle_ids[hv_start:])

        av_df = df[df["vehicle_id"].isin(av_ids)]
        hv_df = df[df["vehicle_id"].isin(hv_ids)]

        av_file = output_dir / f"{base_name}_{ratio}_av.csv"
        hv_file = output_dir / f"{base_name}_{ratio}_hv.csv"

        av_df.to_csv(av_file, index=False, encoding="utf-8-sig")
        hv_df.to_csv(hv_file, index=False, encoding="utf-8-sig")

        print(
            f"{ratio:>3}% AV -> {rel_to_sample(av_file)} "
            f"({len(av_ids)} vehicles, {len(av_df)} rows)"
        )
        print(
            f"{ratio:>3}% HV -> {rel_to_sample(hv_file)} "
            f"({len(hv_ids)} vehicles, {len(hv_df)} rows)"
        )


def main():
    parser = argparse.ArgumentParser(description="Split the one-day sample by vehicle_id.")
    parser.add_argument("--ratios", nargs="*", help="Ratios to generate, e.g. 10 20 30")
    parser.add_argument("--random-state", type=int, default=RANDOM_STATE)
    args = parser.parse_args()

    split_csv_by_vehicle(
        ratios=parse_ratios(args.ratios),
        random_state=args.random_state,
    )


if __name__ == "__main__":
    main()
