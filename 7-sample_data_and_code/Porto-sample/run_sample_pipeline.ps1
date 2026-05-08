$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

python .\scripts\preprocess_one_day.py
python .\scripts\build_trips_xml.py
& .\scripts\run_duarouter_day.ps1
python .\scripts\split_routes_by_penetration.py
python .\sim_porto_sample_day_energy.py
python .\plot_sample_energy_co2.py
