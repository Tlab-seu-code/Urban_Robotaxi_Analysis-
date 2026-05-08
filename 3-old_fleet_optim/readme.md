# 附表：程序、数据意义说明

| 文件名                           | 意义                              |
|----------------------------------|-----------------------------------|
| **Code**                         |                                   |
| dist.py                          | 处理武汉市的行政区域              |
| map.py                           | 绘制动态地图                      |
| plot/v3/v4.py                    | （部分）画图文件                  |
| pre_process.py                   | 数据预处理文件                    |
| traj.py                          | 用于计算路段速度的数据预处理文件   |
| travel_time_calculator.py                          | 启发式算法计算路段速度文件   |
| taxi_orders_sampled_map.html     | 订单动态示意图（需要 VPN）        |
| zone_recog.py                    | 区域性质识别文件                  |
| bi_1.py                          | 二部图生成                        |
| bi_2.py                          | 二部图匹配                        |
| bi_3.py                          | 车队规模与车辆轨迹复现            |
| **Data**                         |                                   |
| original.csv                     | 原始数据（仅保留前十条）          |
| district_boundaries.json         | 武汉行政区域边界 polygon          |
| **Result**                       |                                   |
| bipartite_graph_2024-XX-XX_matching_chains.json | 求解获得的车辆和出行链文件 |
| order_list_X.0_map.html          | 车辆路径可视化动态文件            |
| car.csv                          | 求解结果文件                      |

此外，**osm路网地图**的下载地址为：https://www.openstreetmap.org/
