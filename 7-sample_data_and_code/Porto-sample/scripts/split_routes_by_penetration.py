from pathlib import Path
import hashlib
import random
import re
import shutil
import xml.etree.ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IN_DIR = PROJECT_ROOT / "process" / "routes_raw"
OUT_DIR = PROJECT_ROOT / "process" / "routes_by_p"
DATE_TAG = "20131128"

BASE_SEED = 20251229
P_LIST = [i / 10 for i in range(11)]


def clean_out_dir(out_dir: Path):
    if not out_dir.is_dir():
        return
    for child in out_dir.iterdir():
        if child.is_dir() and re.fullmatch(r"p\d+\.\d{2}", child.name):
            shutil.rmtree(child)


def get_date_from_name(filename: str) -> str:
    match = re.search(r"porto_(\d{8})", filename)
    return match.group(1) if match else "unknown"


def stable_rng(date_str: str, p: float) -> random.Random:
    key = f"{BASE_SEED}_{date_str}_{p:.2f}"
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    seed = int(digest[:8], 16)
    return random.Random(seed)


def split_one_file(path_in: Path, out_subdir: Path, p: float, date_str: str):
    tree = ET.parse(path_in)
    root = tree.getroot()

    vehicles = root.findall("vehicle")
    vid_list = [v.get("id") for v in vehicles if v.get("id") is not None]
    uniq_vid = sorted(set(vid_list))

    rnd = stable_rng(date_str, p)
    n_av = int(round(len(uniq_vid) * p))
    av_set = set(rnd.sample(uniq_vid, n_av)) if n_av > 0 else set()

    for v in vehicles:
        vid = v.get("id")
        if vid is not None:
            v.set("type", "robotaxi" if vid in av_set else "hv")

    for tag in ("trip", "flow"):
        for v in root.findall(tag):
            vid = v.get("id")
            if vid is not None:
                v.set("type", "robotaxi" if vid in av_set else "hv")
            else:
                v.set("type", "robotaxi" if rnd.random() < p else "hv")

    base = re.sub(r"\.rou\.xml$", "", path_in.name)
    out_path = out_subdir / f"{base}_p{p:.2f}.rou.xml"
    tree.write(out_path, encoding="utf-8", xml_declaration=True)
    return out_path, len(uniq_vid), len(av_set)


def main():
    if not IN_DIR.is_dir():
        raise SystemExit(f"[ERR] IN_DIR not found: {IN_DIR}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    clean_out_dir(OUT_DIR)

    files = sorted(
        path for path in IN_DIR.iterdir()
        if path.name == f"porto_{DATE_TAG}.rou.xml"
    )
    if not files:
        raise SystemExit(f"[ERR] No route file found: {IN_DIR / f'porto_{DATE_TAG}.rou.xml'}")

    print(f"[INFO] IN_DIR : {IN_DIR}")
    print(f"[INFO] OUT_DIR: {OUT_DIR}")
    print(f"[INFO] Files  : {len(files)}")
    print(f"[INFO] P_LIST : {', '.join(f'{p:.2f}' for p in P_LIST)}")

    for path_in in files:
        date = get_date_from_name(path_in.name)
        for p in P_LIST:
            out_sub = OUT_DIR / f"p{p:.2f}"
            out_sub.mkdir(parents=True, exist_ok=True)
            out_path, n_all, n_av = split_one_file(path_in, out_sub, p, date)
            print(f"[OK] {date} p={p:.2f}: vehicles={n_all}, AV={n_av} -> {out_path}")

    print("[DONE] Decile routes generated.")


if __name__ == "__main__":
    main()
