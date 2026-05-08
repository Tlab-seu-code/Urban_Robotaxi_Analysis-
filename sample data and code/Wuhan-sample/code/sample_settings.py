from pathlib import Path


SAMPLE_DATE = "20240708"
RATIOS = tuple(range(10, 101, 10))
RANDOM_STATE = 42

START_HOUR = 0
END_HOUR = 24
SEARCH_RADIUS = 1000
SIMULATION_END = 86400
STEP_LENGTH = 1

SAMPLE_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = SAMPLE_ROOT / "data"
OUTPUT_DIR = SAMPLE_ROOT / "outputs"

DAILY_TRAJ_FILE = DATA_DIR / "daily_trajs" / f"traj_{SAMPLE_DATE}.csv"
SUMO_DIR = DATA_DIR / "sumo"
NET_FILE = SUMO_DIR / "robust.net.xml"
VTYPE_FILE = SUMO_DIR / "basic.vtype.xml"

SPLIT_OUTPUT_DIR = OUTPUT_DIR / "split_output"
AV_PROCESSED_DIR = OUTPUT_DIR / "av_processed"
HV_PROCESSED_DIR = OUTPUT_DIR / "hv_processed"
AV_ROU_DIR = OUTPUT_DIR / "av_rous"
HV_ROU_DIR = OUTPUT_DIR / "hv_rous"

AV_TYPES = {
    "arcfox_alphaT": 1.0,
}

HV_TYPES = {
    "elysee_cng": 0.0841,
    "elysee_p": 0.0841,
    "citroen_triomphe": 0.0841,
    "dfpv_a60_hev_e": 0.0081,
    "dfpv_a60_hev_p": 0.0081,
    "dfpv_e70_bev": 0.7314,
}


def ensure_output_dirs():
    for path in (
        SPLIT_OUTPUT_DIR,
        AV_PROCESSED_DIR,
        HV_PROCESSED_DIR,
        AV_ROU_DIR,
        HV_ROU_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def parse_ratios(values):
    if not values:
        return RATIOS
    ratios = tuple(sorted({int(value) for value in values}))
    invalid = [ratio for ratio in ratios if ratio < 10 or ratio > 100 or ratio % 10 != 0]
    if invalid:
        raise ValueError(f"Ratios must be 10, 20, ..., 100. Invalid: {invalid}")
    return ratios


def rel_to_sample(path):
    return Path(path).relative_to(SAMPLE_ROOT).as_posix()
