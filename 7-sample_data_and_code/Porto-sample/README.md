# Porto single-day penetration sample

This sample keeps the same experimental logic as the parent Porto project, but only uses one day:

- Date: `2013-11-28`
- Penetration levels: `p0.00, p0.10, ..., p1.00`
- Route assignment logic: `round(number_of_unique_vehicle_ids * p)` vehicles are selected with the same stable seed logic and changed to `robotaxi`; the rest remain `hv`.
- SUMO/TraCI settings, energy constants, CO2 constants, teleport setting, and aggregation columns match the parent experiment.

All paths in the scripts are derived from this folder, so the sample can be moved to another computer as a folder. SUMO must still be installed and `sumo`, `duarouter`, and TraCI must be available in the environment.

## Main files

- `data/porto_trajectories_20131128.csv`: one-day raw Porto trajectory subset.
- `process/daily/porto_20131128.csv`: processed one-day trip table.
- `process/trips_xml/porto_20131128.trips.xml`: SUMO trip input.
- `process/routes_raw/porto_20131128.rou.xml`: duarouter output before penetration assignment.
- `process/routes_by_p/p*/porto_20131128_p*.rou.xml`: one-day routes for every penetration level.
- `net/robust.net.xml`: SUMO network file.
- `process/vtypes/porto.vtype.xml`: `hv` and `robotaxi` vehicle definitions.
- `sim_porto_sample_day_energy.py`: one-day simulation over all penetration levels.
- `plot_sample_energy_co2.py`: plotting logic matching the parent plot script.

## Run

From this `sample` folder:

```powershell
python .\scripts\preprocess_one_day.py
python .\scripts\build_trips_xml.py
powershell -ExecutionPolicy Bypass -File .\scripts\run_duarouter_day.ps1
python .\scripts\split_routes_by_penetration.py
python .\sim_porto_sample_day_energy.py
python .\plot_sample_energy_co2.py
```

Or run the whole pipeline:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_sample_pipeline.ps1
```

The repository already includes the one-day processed files and route files, so you can skip directly to:

```powershell
python .\sim_porto_sample_day_energy.py
python .\plot_sample_energy_co2.py
```

The main outputs are written under `output/p*/20131128/`, plus `output/energy_emissions_summary.csv` and `output/fig_d_porto_sample.png`.
