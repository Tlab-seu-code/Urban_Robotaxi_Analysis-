import argparse

from sample_settings import (
    AV_ROU_DIR,
    HV_ROU_DIR,
    NET_FILE,
    RATIOS,
    SIMULATION_END,
    STEP_LENGTH,
    VTYPE_FILE,
    ensure_output_dirs,
    parse_ratios,
    rel_to_sample,
)


SCENARIOS = {
    "av": {
        "output_dir": AV_ROU_DIR,
        "cfg_prefix": "av",
        "rou_prefix": "taxis_av",
    },
    "hv": {
        "output_dir": HV_ROU_DIR,
        "cfg_prefix": "hdv",
        "rou_prefix": "taxis_hv",
    },
}


TEMPLATE = """<configuration>
    <input>
        <net-file value="{net_file}"/>
        <route-files value="{rou_file}"/>
        <additional-files value="{additional_file}"/>
    </input>
    <time>
        <begin value="{begin}"/>
        <step-length value="{step_length}"/>
        <end value="{end}"/>
    </time>
</configuration>
"""


def batch_generate_sumocfg(
    scenario,
    ratios=RATIOS,
    begin=0,
    end=SIMULATION_END,
    step_length=STEP_LENGTH,
):
    settings = SCENARIOS[scenario]
    output_dir = settings["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    for ratio in ratios:
        rou_file = output_dir / f"{settings['rou_prefix']}_{ratio}.rou.xml"
        cfg_file = output_dir / f"{settings['cfg_prefix']}_{ratio}.sumocfg"

        cfg_content = TEMPLATE.format(
            net_file=rel_to_sample(NET_FILE),
            rou_file=rel_to_sample(rou_file),
            additional_file=rel_to_sample(VTYPE_FILE),
            begin=begin,
            step_length=step_length,
            end=end,
        )

        with open(cfg_file, "w", encoding="utf-8") as f:
            f.write(cfg_content)

        print(f"Generated: {rel_to_sample(cfg_file)}")


def main():
    parser = argparse.ArgumentParser(description="Generate SUMO configuration files.")
    parser.add_argument("--scenario", choices=("av", "hv", "both"), default="both")
    parser.add_argument("--ratios", nargs="*", help="Ratios to generate, e.g. 10 20 30")
    parser.add_argument("--begin", type=int, default=0)
    parser.add_argument("--end", type=int, default=SIMULATION_END)
    parser.add_argument("--step-length", type=float, default=STEP_LENGTH)
    args = parser.parse_args()

    ensure_output_dirs()
    ratios = parse_ratios(args.ratios) if args.ratios else RATIOS
    scenarios = ("av", "hv") if args.scenario == "both" else (args.scenario,)
    for scenario in scenarios:
        batch_generate_sumocfg(
            scenario=scenario,
            ratios=ratios,
            begin=args.begin,
            end=args.end,
            step_length=args.step_length,
        )


if __name__ == "__main__":
    main()
