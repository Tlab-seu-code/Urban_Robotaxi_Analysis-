# -*- coding: utf-8 -*-
"""
Run the self-contained one-day NYC penetration-rate sample.

Default mode starts from the included one-day route cache, generates SUMO route
files/configs for all penetration levels, then runs the one-day simulations.
Use --rebuild-cache to rerun the raw-orders -> edge mapping -> route cache steps.
"""

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the one-day NYC penetration-rate sample experiment."
    )
    parser.add_argument(
        "--penetrations",
        default="0,10,20,30,40,50,60,70,80,90,100",
        help="Comma-separated penetration percentages.",
    )
    parser.add_argument("--end", type=int, default=86400)
    parser.add_argument(
        "--rebuild-cache",
        action="store_true",
        help="Rebuild edge mapping and route cache from the included raw sample orders.",
    )
    parser.add_argument(
        "--skip-simulation",
        action="store_true",
        help="Only generate .rou.xml and .sumocfg files.",
    )
    parser.add_argument(
        "--max-orders",
        type=int,
        help="Optional smoke-test limit for route-file generation.",
    )
    return parser.parse_args()


def run(cmd):
    print("\n[RUN]", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def main():
    args = parse_args()

    if args.rebuild_cache:
        run([sys.executable, str(SCRIPTS / "traj.py")])
        run([sys.executable, str(SCRIPTS / "route_cache_gen.py")])

    gen_cmd = [
        sys.executable,
        str(SCRIPTS / "rou_gen_opt.py"),
        "--penetrations",
        args.penetrations,
        "--end",
        str(args.end),
    ]
    if args.max_orders:
        gen_cmd.extend(["--max-orders", str(args.max_orders)])
    run(gen_cmd)

    if not args.skip_simulation:
        run(
            [
                sys.executable,
                str(SCRIPTS / "sim.py"),
                "--penetrations",
                args.penetrations,
                "--end",
                str(args.end),
            ]
        )


if __name__ == "__main__":
    main()
