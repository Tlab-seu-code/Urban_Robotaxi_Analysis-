# Urban_Robotaxi_Analysis-

This repository contains a comprehensive framework for processing, analyzing, and simulating urban vehicle data (Autonomous Vehicles - AV and Human-Driven Vehicles - HDV). The project includes modules for data cleaning, fleet size optimization using bipartite matching, SUMO-based traffic simulation, environmental impact analysis, and publication-quality visualization.

## Project Structure

```text
final_code/
│
├── 1-av_data_process/                    # AV Data Cleaning & Feature Engineering
│   ├── avg_speed.py                      # Calculate average speeds and distributions
│   ├── dist.py                           # District boundary handling (GeoJSON/Polygon)
│   ├── pre_av_process.py                 # Core AV data cleaning pipeline
│   ├── pre_process.py                    # Merge virtual/dispatch orders and handle cancellations
│   ├── soc.py                            # State of Charge (Battery) interpolation
│   ├── traj.py                           # Map matching: GPS points to SUMO edges
│   └── zone_recog.py                     # POI Zone classification (Residential/Commercial/etc.)
│
├── 2-hdv_data_process/                   # HDV Data Processing Pipeline
│   ├── analy.py                          # Convert raw tracking TXT data to CSV
│   ├── cont.py                           # Merge output files and filter by duration
│   ├── grid.py                           # Spatio-temporal grid mapping & non-run ratio calc
│   ├── merged_order.py                   # Merge orders with calculated travel lengths
│   ├── pre_hdv_process.py                # Basic cleaning (outliers, bounds) for HDV
│   ├── speed_gen.py                      # Speed anomaly filtering
│   ├── speed_rec.py                      # Recompute speeds based on distance/time
│   ├── speed_tag.py                      # Tag data with Peak/Off-peak and Workday/Weekend
│   ├── travel_len.py                     # Calculate travel distances from trajectories
│   └── V1_ticket.py                      # Extract trip "orders" from continuous trajectory streams
│
├── 3-fleet_optim/                        # Fleet Size Optimization (Bipartite Matching)
│   ├── bi_1.py                           # Construct Bipartite Graph from orders
│   ├── bi_2.py                           # Solve Maximum Matching problem
│   ├── bi_3.py                           # Reconstruct vehicle chains & determine fleet size
│   ├── travel_time_calculator.py         # Heuristic algorithm for road network speed estimation
│   └── [Helpers]                         # dist.py, traj.py, etc. (Shared utilities)
│
├── 4-simulation/                         # SUMO Traffic Simulation
│   ├── rou_gen.py                        # Generate SUMO .rou.xml from CSV trajectories
│   ├── sim.py                            # Run simulation for emission data collection
│   ├── eqaco2.py                         # Calculate CO2/Energy based on vehicle types
│   └── basic.vtype.xml                   # Vehicle physical definitions (EV/ICE parameters)
│
├── 5-cci_and_sne/                        # Calculate the CCI and SNE
│   ├── cci_distribution.py               # calculate the distribution of CCI
│   ├── cci_percentile.py                 # calculate the percentile of CCI
│   ├── compute_grid_sne_wuhan.py         # calculate the SNE of Wuhan city
│   └── ntl.py                            # calculate the center of the city and the CCI
│
├── 6-figure/                             # Visualization (Nature-style Figures)
│    ├── fig1a.py                         # Spatio-temporal distribution plots
│    ├── fig1b.R                          # The orders distribution of four periods
│    ├── fig1c.py                         # 4-panel Sankey diagram
│    ├── fig1d_pie.py                     # Pie chart showing feature importance distribution from SHAP values
│    ├── fig1d_shap.py                    # Beeswarm summary plot
│    ├── fig1e.py                         # Emission heatmaps
│    ├── fig1f.py                         # Boxplot showing the hourly distribution of EV charging energy (kWh)
│    ├── fig1g.py                         # Hourly CO2 emissions from autonomous vehicles
│    ├── fig2a-b.py                       # Weekly order performance
│    ├── fig2c.py                         # top k index
│    ├── fig2c_SA.py                      # Sensitive analysis of top k index
│    ├── fig3a.py                         # POP and CTX model
│    ├── fig3b.py                         # CCI distribution
│    ├── fig4a.py                         # Histogram comparing the OPCI distribution
│    ├── fig4b.py                         # Robotaxi orders across the CCI percentile bins
│    ├── fig4c.py                         # Weekly fleet dynamics time series
│    ├── fig4d.py                         # Lorenz curves
│    └── fig4e.py                         # Dual-axis hourly comparison chart
│
└──7-sample_data_and_code/                # Samples
     ├── NYC-sample/                      # Sample of NYC
     ├── Porto-sample/                    # Sample of Porto
     ├── Wuhan-sample/                    # Sample of Wuhan
     └── carpooling_one_day_sample_code/  # carpool sample of one day
```

## Prerequisites

### Software

- **Python 3.8+**
- **SUMO (Simulation of Urban MObility) 1.20.0**: Must be installed and added to system PATH.

### Python Libraries and Versions the Software has been Tested on

Install dependencies using pip:

```bash
pip install pandas==2.0.3 numpy==1.23.5 matplotlib==3.8.4 seaborn==0.13.2 networkx==2.8.4 shapely==2.0.7 scipy==1.13.1 lxml==4.9.1 plotly==5.9.0 adjustText==1.3.0 pypinyin==0.55.0 sumolib traci
```

## Workflow Guide

### Phase 0: Installation

1. Clone the repository to your local machine:

   ```bash
   git clone https://github.com/Tlab-seu-code/Urban_Robotaxi_Analysis-.git
   cd Urban_Robotaxi_Analysis-
   ```
   
2. Create the virtual environment and install the dependencies.
   
3. Typical installation time: Approximately 5 minutes on a standard desktop computer.

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

- Execute specific scripts (e.g., `fig4b.py`) to generate SVG/PDF figures:

```bash
cd ..\Urban_Robotaxi_Analysis-/6-figure
python fig4b.py
```

- Note: These scripts contain specific styling configurations (fonts, sizes) to match academic journal standards (e.g., Nature style).

### Phase 5: Sample Data and Code (`7-sample_data_and_code/`)

1. Choose one of the samples, e.g., ../Urban_Robotaxi_Analysis-/7-sample_data_and_code/NYC-sample:

```bash
cd ../Urban_Robotaxi_Analysis-/7-sample_data_and_code/NYC-sample
```
   
2. Run the python file:

```bash
python scripts/run_sample.py
```

3. After the operation is completed, the corresponding results will be output in the folder, such as the results of the penetration experiment or the carpooling experiment.

4. The case operation is likely to take several hours.

5. An example to show that how to run the python files on your data:

```bash
python scripts/run_sample.py --penetrations 0,50,100 --end 3600 --max-orders 200
```

You need to set the parameters as described above after you have replaced your dataset.

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
