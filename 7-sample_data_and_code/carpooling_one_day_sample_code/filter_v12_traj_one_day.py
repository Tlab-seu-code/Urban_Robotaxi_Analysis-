#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filter v12-traj.csv to one target day without changing any columns.

Default input/output are designed for the Nature sample package:
- input : ./v12-traj.csv
- output: ./v12-traj_sample_2024-11-12.csv

Run:
python filter_v12_traj_one_day.py
python filter_v12_traj_one_day.py --target-date 2024/11/12
python filter_v12_traj_one_day.py --input v12-traj.csv --output v12-traj_sample_2024-11-12.csv
"""

import argparse
import csv
import os
from datetime import datetime

DEFAULT_TARGET_DATE = "2024/11/12"
DEFAULT_INPUT = "v12-traj.csv"
DEFAULT_OUTPUT = "v12-traj_sample_2024-11-12.csv"


def get_script_dir() -> str:
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()


def normalize_date_str(date_str: str) -> str:
    raw = str(date_str).strip()
    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            return f"{dt.year}/{dt.month}/{dt.day}"
        except ValueError:
            pass
    raise ValueError(f"Unsupported date format: {date_str}. Use YYYY/M/D or YYYY-MM-DD.")


def extract_order_date(row: dict) -> str:
    # The carpooling code uses 到达起点时间 to determine the processing date.
    # Fall back to 日期 only if 到达起点时间 is unavailable.
    if row.get("到达起点时间"):
        return normalize_date_str(str(row["到达起点时间"]).split(" ")[0])
    if row.get("日期"):
        return normalize_date_str(row["日期"])
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter v12-traj.csv to one target day.")
    parser.add_argument("--target-date", default=DEFAULT_TARGET_DATE, help="Target date, e.g. 2024/11/12 or 2024-11-12.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input v12 trajectory CSV path.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output one-day trajectory CSV path.")
    args = parser.parse_args()

    script_dir = get_script_dir()
    input_path = args.input if os.path.isabs(args.input) else os.path.join(script_dir, args.input)
    output_path = args.output if os.path.isabs(args.output) else os.path.join(script_dir, args.output)
    target_date = normalize_date_str(args.target_date)

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    total_rows = 0
    kept_rows = 0
    missing_date_rows = 0

    with open(input_path, "r", encoding="utf-8-sig", newline="") as fin, \
         open(output_path, "w", encoding="utf-8-sig", newline="") as fout:
        reader = csv.DictReader(fin)
        if not reader.fieldnames:
            raise ValueError(f"Input file has no header: {input_path}")

        writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
        writer.writeheader()

        for row in reader:
            total_rows += 1
            order_date = extract_order_date(row)
            if not order_date:
                missing_date_rows += 1
                continue
            if order_date == target_date:
                writer.writerow(row)
                kept_rows += 1

    print("Finished filtering v12 trajectory data.")
    print(f"Target date: {target_date}")
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"Total rows scanned: {total_rows}")
    print(f"Rows kept: {kept_rows}")
    print(f"Rows skipped due to missing date: {missing_date_rows}")


if __name__ == "__main__":
    main()
