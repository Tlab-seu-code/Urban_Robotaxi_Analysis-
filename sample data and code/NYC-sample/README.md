# NYC One-Day Penetration Sample

This folder is self-contained. It includes the one-day sample data, SUMO network
files, vehicle types, and runnable scripts needed to reproduce the 2024-11-01
penetration experiment with the same logic as the full workflow.

## Contents

```text
data/yellow_orders_20241101_sample.csv
data/daily_orders_with_sumo/nyc_orders_20241101_with_sumo_edges.csv
data/nyc_20241101_route_cache.csv
data/basic.vtype.xml
net/osm.net.xml
net/osm_sim.net.xml
scripts/traj.py
scripts/route_cache_gen.py
scripts/rou_gen_opt.py
scripts/sim.py
run_sample.py
```

## Run The Sample

From this folder:

```powershell
python run_sample.py
```

The runner resolves paths relative to its own location, so it can also be
called by absolute path from another working directory.

This uses the included one-day route cache, generates route files and SUMO
configs under `runs/rou_20241101_multi_penetration_cached`, then runs the
0%-100% penetration simulations for 86400 seconds.

For a quick smoke test:

```powershell
python run_sample.py --penetrations 0,100 --max-orders 5 --end 3600
```

## Rebuild From Raw One-Day Orders

To rerun the full sample pipeline from the included raw one-day orders:

```powershell
python run_sample.py --rebuild-cache
```

That runs:

1. `scripts/traj.py`
2. `scripts/route_cache_gen.py`
3. `scripts/rou_gen_opt.py`
4. `scripts/sim.py`

The vehicle type weights, penetration levels, random seed behavior, dynamic
speed schedule, SUMO routing, and output aggregation logic match the full
experiment. The only intended reduction is that the input orders are limited to
2024-11-01.
