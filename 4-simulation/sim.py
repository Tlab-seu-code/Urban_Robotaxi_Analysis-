# -*- coding: utf-8 -*-
"""
Created on Mon Jun  9 14:37:16 2025

@author: WuxiTlab
"""

import traci
import sumolib
import csv
import os

# 配置参数
DEBUG_MODE = 0
NET_FILE = "robust.net.xml"  # 请替换为实际路网文件
SIMULATION_END = 90000

def update_speed(non_internal_edges, speed):
    # 修改所有非内部边的限速为 10 m/s
    for edge in non_internal_edges:
        traci.edge.setMaxSpeed(edge, speed)
    print(f"限速已修改为 {speed} m/s")

def run_simulation():
    # 初始化SUMO配置
    sumo_cmd = [
        "sumo-gui" if DEBUG_MODE else "sumo",
        "-c", "hdv.sumocfg",
        "--emission-output", "hdv.xml",  # 禁用SUMO内置CO2计算
        "--emission-output.geo", "True"
    ]

    # 启动TraCI连接
    traci.start(sumo_cmd)
    net = sumolib.net.readNet(NET_FILE)
    
    all_edges = traci.edge.getIDList()
    non_internal_edges = [edge for edge in all_edges if not edge.startswith(':')]
    
    # 创建数据文件
    with open('vehicle_stats_detail_hdv.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'Timestamp(s)', 'VehicleID', 'Longitude', 'Latitude',
            'VehicleType', 'Electricity(kWh)', 'Fuel(g)', 'CO2(g)'
        ])

        # 主循环
        while (current_time := traci.simulation.getTime()) <= SIMULATION_END:
            if int(current_time) % 10 == 0:
                print(current_time)
                
            if current_time == 10:
                update_speed(non_internal_edges, 12)
            if current_time == 10 + 3600 * 7:
                update_speed(non_internal_edges, 8)
            if current_time == 10 + 3600 * 10:
                update_speed(non_internal_edges, 10)
            if current_time == 10 + 3600 * 17:
                update_speed(non_internal_edges, 8)
            if current_time == 10 + 3600 * 20:
                update_speed(non_internal_edges, 10)
            if current_time == 10 + 3600 * 22:
                update_speed(non_internal_edges, 12)
            
            for veh_id in traci.vehicle.getIDList():
                try:
                    # 基础信息获取
                    x, y = traci.vehicle.getPosition(veh_id)
                    lon, lat = net.convertXY2LonLat(x, y)
                    veh_type = traci.vehicle.getTypeID(veh_id)
                    
                    # 能耗类型判断
                    is_electric = any(kw in veh_type.lower() for kw in {'bev', 'hev_e', 'fox'})

                    # 初始化数据容器
                    electricity = -1.0
                    fuel = -1.0
                    co2 = -1.0

                    # 电动车数据处理
                    if is_electric:
                        electricity = traci.vehicle.getElectricityConsumption(veh_id) * 1 / 1000  # Wh->kWh
                        co2 = 0.0
                    # 燃油车数据处理
                    else:
                        fuel = traci.vehicle.getFuelConsumption(veh_id) * 1 / 1000  # mg->g
                        co2 = traci.vehicle.getCO2Emission(veh_id) * 1 / 1000  # mg->g

                    # 写入记录
                    writer.writerow([
                        f"{current_time:.1f}", veh_id,
                        f"{lon:.6f}", f"{lat:.6f}",
                        veh_type,
                        f"{electricity:.4f}" if electricity != -1 else "-",
                        f"{fuel:.2f}" if fuel != -1 else "-",
                        f"{co2:.2f}"
                    ])

                except traci.TraCIException as e:
                    print(f"Error processing vehicle {veh_id}: {str(e)}")

            # 推进仿真
            traci.simulationStep()

    traci.close()

if __name__ == "__main__":
    # 检查路网文件是否存在
    if not os.path.exists(NET_FILE):
        print(f"Error: Network file {NET_FILE} not found!")
        exit(1)
        
    # 执行仿真
    run_simulation()