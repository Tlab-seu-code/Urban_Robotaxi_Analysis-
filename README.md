# Urban_Robotaxi_Analysis-

This repository contains a comprehensive framework for processing, analyzing, and simulating urban vehicle data (Autonomous Vehicles - AV and Human-Driven Vehicles - HDV). The project includes modules for data cleaning, fleet size optimization using bipartite matching, SUMO-based traffic simulation, environmental impact analysis, and publication-quality visualization.

## Project Structure

```text
final_code/
│
├── 1-av_data_process/          # AV Data Cleaning & Feature Engineering
│   ├── avg_speed.py            # Calculate average speeds and distributions
│   ├── combine.py              # Merge raw data files (e.g., monthly Excel to CSV)
│   ├── dist.py                 # District boundary handling (GeoJSON/Polygon)
│   ├── pre_av_process.py       # Core AV data cleaning pipeline
│   ├── pre_process.py          # Merge virtual/dispatch orders and handle cancellations
│   ├── price.py                # Taxi fare calculation logic (Time/Distance based)
│   ├── soc.py                  # State of Charge (Battery) interpolation
│   ├── traj.py                 # Map matching: GPS points to SUMO edges
│   └── zone_recog.py           # POI Zone classification (Residential/Commercial/etc.)
│
├── 2-hdv_data_process/         # HDV Data Processing Pipeline
│   ├── analy.py                # Convert raw tracking TXT data to CSV
│   ├── cont.py                 # Merge output files and filter by duration
│   ├── grid.py                 # Spatio-temporal grid mapping & non-run ratio calc
│   ├── merged_order.py         # Merge orders with calculated travel lengths
│   ├── pre_hdv_process.py      # Basic cleaning (outliers, bounds) for HDV
│   ├── speed_gen.py            # Speed anomaly filtering
│   ├── speed_rec.py            # Recompute speeds based on distance/time
│   ├── speed_tag.py            # Tag data with Peak/Off-peak and Workday/Weekend
│   ├── travel_len.py           # Calculate travel distances from trajectories
│   └── V1_ticket.py            # Extract trip "orders" from continuous trajectory streams
│
├── 3-old_fleet_optim/          # Fleet Size Optimization (Bipartite Matching)
│   ├── bi_1.py                 # Construct Bipartite Graph from orders
│   ├── bi_2.py                 # Solve Maximum Matching problem
│   ├── bi_3.py                 # Reconstruct vehicle chains & determine fleet size
│   ├── travel_time_calculator.py # Heuristic algorithm for road network speed estimation
│   └── [Helpers]               # dist.py, traj.py, etc. (Shared utilities)
│
├── 4-simulation/               # SUMO Traffic Simulation
│   ├── dynamic/                # Dynamic Dispatching Simulation
│   │   ├── run.py              # Basic simulation runner
│   │   ├── sim.py              # Main TraCI loop for dispatch algorithms
│   │   ├── add.py              # Inject passengers/orders into running sim
│   │   ├── adj.py              # Time synchronization analysis (Sim vs Real)
│   │   └── computation_time.py # Performance/Overhead analysis
│   └── static/                 # Historical Replay & Emission Analysis
│       ├── rou_gen.py          # Generate SUMO .rou.xml from CSV trajectories
│       ├── sim.py              # Run simulation for emission data collection
│       ├── eqaco2.py           # Calculate CO2/Energy based on vehicle types
│       └── basic.vtype.xml     # Vehicle physical definitions (EV/ICE parameters)
│
├── 5-equal/                    # Statistical Comparison & Analysis
│   ├── equal.py                # Demand-Supply correlation & "Non-run" ratio analysis
│   └── poi.py                  # POI data categorization
│
└── 6-figure/                   # Visualization (Nature-style Figures)
    ├── fig1a-d 2d.py           # Spatio-temporal distribution plots
    ├── fig1e-f2.py             # Emission heatmaps
    ├── fig1f-g.py              # Hourly CO2 distribution
    ├── fig2a-b.py              # Weekly order performance
    ├── fig2c.py                # Weather vs. Waiting time boxplots
    ├── fig3.py                 # District-level analysis
    ├── fig4.py                 # Vehicle status heatmaps (Idle/Dispatch/Charge/Passenger)
    ├── figure4a.py             # AV vs HV order comparison (POP baseline vs CTX baseline)
    └── figure5b.py             # Robotaxi order analysis (CTX model vs POP+SNE model)
```

## Prerequisites

### Software

- **Python 3.8+**
- **SUMO (Simulation of Urban MObility)**: Must be installed and added to system PATH.

### Python Libraries

Install dependencies using pip:

```bash
pip install pandas numpy matplotlib seaborn networkx shapely scipy sumolib traci lxml plotly adjustText pypinyin
```

## Workflow Guide

### Phase 1: Data Processing

1. HDV Processing (`2-hdv_data_process/`)

   :

   - Run `analy.py` to convert raw tracking data.
   - Run `V1_ticket.py` to extract individual trips.
   - Run `travel_len.py` and `speed_rec.py` to calculate distances and speeds.
   - Run `grid.py` to map data to spatial grids.

2. AV Processing (`1-av_data_process/`)

   :

   - Run `pre_process.py` to handle order logic.
   - Run `traj.py` to match GPS coordinates to the road network.
   - Run `zone_recog.py` to classify trip start/end points.
   - Run `price.py` and `soc.py` for fare and battery analysis.

### Phase 2: Fleet Optimization (`3-old_fleet_optim/`)

1. **Graph Construction**: Run `bi_1.py` to create a directed acyclic graph (DAG) where nodes are trips and edges represent feasible connections.
2. **Matching**: Run `bi_2.py` to perform maximum bipartite matching.
3. **Chaining**: Run `bi_3.py` to minimize the number of vehicles required to serve all orders (Minimum Fleet Problem).

### Phase 3: Simulation (`4-simulation/`)

- **Route Generation**: Use `static/rou_gen.py` to convert processed CSV data into SUMO `*.rou.xml` files using shortest-path algorithms on `robust.net.xml`.
- **Emission Analysis**: Run `static/sim.py` to collect fuel/electricity consumption data, then refine with `eqaco2.py`.
- **Dynamic Dispatch**: Use `dynamic/sim.py` to test real-time dispatching strategies via TraCI interface.

### Phase 4: Visualization (`6-figure/`)

- Execute specific scripts (e.g., `fig4.py`, `fig1e-f2.py`) to generate SVG/PDF figures.
- Note: These scripts contain specific styling configurations (fonts, sizes) to match academic journal standards (e.g., Nature style).

## Key File Descriptions

- **`district_boundaries.json`**: Contains the polygon coordinates for administrative districts (used by `dist.py`).
- **`robust.net.xml`**: The SUMO road network file (required for `sumolib` operations).
- **`equal.py`**: A critical script for comparing the supply-demand balance between AVs and HDVs, often used to generate "Vehicle Shortage Ratio" metrics.

## Notes

- **Path Handling**: Ensure that file paths (e.g., `../dataV3/`) in the scripts match your local directory structure.
- **Fonts**: The plotting scripts use `Arial` or `Microsoft YaHei`. Ensure these fonts are installed on your system to avoid warnings.
- **SUMO Environment**: Ensure the `SUMO_HOME` environment variable is set correctly for `traci` and `sumolib` to work.

------

*Created by TLab Team.*
