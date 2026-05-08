# Robotaxi penetration sample experiment

这个 `sample` 文件夹是一份一日数据量的独立 sample 实验。数据取自 `20240708`，代码沿用现有实验流程：按 `vehicle_id` 做固定随机拆分，插入同一车辆相邻订单之间的空驶行程，基于 SUMO 路网匹配最近边并计算最短路，生成 `.rou.xml` 和 `.sumocfg`，最后按车辆聚合仿真能耗/排放统计。

## 目录

- `data/daily_trajs/traj_20240708.csv`：一日轨迹样本。
- `data/sumo/robust.net.xml`：SUMO 路网。
- `data/sumo/basic.vtype.xml`：车辆类型参数。
- `code/`：sample 实验代码，全部通过相对目录组织，不包含本机绝对路径。
- `outputs/`：脚本运行后生成拆分数据、补空驶数据、route 文件、config 文件和仿真结果。

## 一键运行

在 `sample` 目录中运行：

```powershell
python .\run.py
```

默认会先清空 `outputs/`，再生成拆分数据、补空驶数据、SUMO route 文件和 SUMO config 文件。需要同时启动 SUMO 仿真时运行：

```powershell
python .\run.py --with-simulation
```

只跑某个渗透率可以加 `--ratios`，例如：

```powershell
python .\run.py --ratios 10 --scenario both
```

## 分步运行

在 `sample` 目录中运行：

```powershell
python .\code\split_by_vehicle_sample.py
python .\code\add_relocation_sample.py
python .\code\generate_routes_sample.py
python .\code\generate_sumocfg_sample.py
python .\code\run_simulation_sample.py
```

仿真依赖本机已安装 SUMO，并且 Python 环境中可导入 `pandas`、`numpy`、`sumolib`、`traci`。
