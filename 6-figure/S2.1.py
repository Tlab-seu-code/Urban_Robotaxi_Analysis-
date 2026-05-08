# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from datetime import timedelta

def compute_hourly_state_share(
    csv_path: str,
    date: str | None = None,       # 例如 "2024-12-02"；None 时自动选择数据中最常见的日期
    interval_minutes: int = 10,    # 与你热力图一致的粒度
    save_csv_path: str | None = None
) -> pd.DataFrame:
    """
    统计指定日期（或数据中最常见日期）内，每小时所有车辆处于
    Passenger / Charging / Dispatch / Idle 的车辆-时间占比（0..1）。

    返回包含每小时占比与百分比的 DataFrame（24 行）。
    若 save_csv_path 不为 None，则保存为 CSV（UTF-8-SIG）。
    """
    # 1) 读取 CSV（尝试多种编码以兼容中文）
    last_err = None
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            df_raw = pd.read_csv(csv_path, encoding=enc)
            break
        except Exception as e:
            last_err = e
            df_raw = None
    if df_raw is None:
        raise RuntimeError(f"读取 CSV 失败：{csv_path}，错误：{last_err}")

    df = df_raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # 2) 基础清洗与时间解析
    # 过滤取消单（若存在“订单状态”列）
    if "订单状态" in df.columns:
        df = df[df["订单状态"] != "取消"].copy()

    # 解析时间列
    for col in ("呼单时间", "取消时间", "完成时间"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    essential = ["车辆id", "呼单时间"]
    for c in essential:
        if c not in df.columns:
            raise ValueError(f"缺少必要列：{c}；当前列为：{list(df.columns)}")

    if df["呼单时间"].notna().sum() == 0:
        raise ValueError("‘呼单时间’全为 NaT，无法统计。")

    # 3) 确定目标日期
    if date is None:
        # 取数据中最常见的日期
        target_date = df["呼单时间"].dt.normalize().mode().iloc[0]
    else:
        target_date = pd.to_datetime(date).normalize()

    # 只保留该日订单（以呼单时间所在日判断）
    df_day = df[df["呼单时间"].dt.date == target_date.date()].copy()
    if df_day.empty:
        raise ValueError(f"在 {target_date.date()} 当天无数据。可尝试将 date=None 让程序自动选取。")

    # 4) 搭建时间网格（10 分钟粒度）
    day_start = target_date
    day_end = target_date + pd.Timedelta(days=1)
    time_bins = pd.date_range(start=day_start, end=day_end, freq=f"{interval_minutes}T")
    # searchsorted 需要右边界，再补一个 day_end 作为最后右端点
    if time_bins[-1] != day_end:
        time_bins = time_bins.append(pd.Index([day_end]))

    # 车辆全集
    vehicles = df_day["车辆id"].dropna().unique()
    if vehicles.size == 0:
        raise ValueError(f"{target_date.date()} 当天没有有效车辆。")

    num_slots = len(time_bins) - 1
    status_matrix = np.zeros((num_slots, vehicles.size), dtype=np.uint8)  # 0=Idle

    # 订单来源 -> 状态编码（可按需扩展）
    # 1=Dispatch, 2=Charging, 3=Passenger
    source_to_code = {
        "调度单": 1,
        "充电单": 2,
        "app": 3,
        "小程序": 3,
        "百度地图": 3,
    }

    # 5) 将每条订单映射到时间槽，按优先级更新状态矩阵
    for vidx, v in enumerate(vehicles):
        orders = df_day[df_day["车辆id"] == v]
        if orders.empty:
            continue

        for _, row in orders.iterrows():
            start = row["呼单时间"]
            # 确定结束时间：优先“取消时间”或“完成时间”，否则取一个默认时长（interval）
            if pd.notna(row.get("取消时间", pd.NaT)):
                end = row["取消时间"]
            elif pd.notna(row.get("完成时间", pd.NaT)):
                end = row["完成时间"]
            else:
                end = start + timedelta(minutes=interval_minutes)

            # 裁剪到当天范围
            if pd.isna(start) or pd.isna(end):
                continue
            if end <= start:
                continue
            start = max(start, day_start)
            end = min(end, day_end)
            if end <= start:
                continue

            # 找到时间槽区间
            left = np.searchsorted(time_bins, start, side="right") - 1
            right = np.searchsorted(time_bins, end, side="left")
            if right <= left:
                continue
            slots = slice(max(0, left), min(num_slots, right))

            # 映射来源到状态；未知来源默认按 Passenger 处理（你也可改为 Dispatch 或 Idle）
            src = str(row.get("订单来源", "")).strip()
            code = source_to_code.get(src, 3)
            # 优先级覆盖：取最大值（3>2>1>0）
            np.maximum(status_matrix[slots, vidx], code, out=status_matrix[slots, vidx])

    # 6) 聚合为“每小时车辆-时间占比”
    slots_per_hour = 60 // interval_minutes
    records = []
    for h in range(24):
        r0 = h * slots_per_hour
        r1 = min((h + 1) * slots_per_hour, num_slots)
        window = status_matrix[r0:r1, :]

        # 总单元=槽数×车辆数
        total_cells = window.size
        if total_cells == 0:
            total_cells = vehicles.size * slots_per_hour  # 理论值兜底

        idle = np.count_nonzero(window == 0)
        dispatch = np.count_nonzero(window == 1)
        charging = np.count_nonzero(window == 2)
        passenger = np.count_nonzero(window == 3)

        rec = {
            "date": target_date.date().isoformat(),
            "hour": h,
            "Idle_share": idle / total_cells,
            "Dispatch_share": dispatch / total_cells,
            "Charging_share": charging / total_cells,
            "Passenger_share": passenger / total_cells,
        }
        records.append(rec)

    hourly_df = pd.DataFrame(records)
    # 同时给出百分比列（0..100）
    for c in ("Idle_share", "Dispatch_share", "Charging_share", "Passenger_share"):
        hourly_df[c.replace("_share", "_pct")] = (hourly_df[c] * 100).round(2)

    if save_csv_path:
        hourly_df.to_csv(save_csv_path, index=False, encoding="utf-8-sig")

    return hourly_df


# ===== 使用示例 =====
if __name__ == "__main__":
    # 方式一：指定日期
    out = compute_hourly_state_share(
        csv_path="v3-districts.csv",
        date="2024-12-02",                 # 或者 "2024/12/2" 也可被解析
        interval_minutes=10,
        save_csv_path="hourly_state_share.csv"
    )
    print(out)
    out.to_csv('hourly_state_share.csv', index=False, encoding='utf-8-sig')

    # 方式二：不指定日期，自动选择数据中最常见日期
    # out = compute_hourly_state_share("网约车订单数据.csv", date=None, save_csv_path=None)
    # print(out)
    # 100% 堆叠柱状图（纵轴为百分比，横轴为 0:00–23:00）
    import matplotlib.pyplot as plt
        # 若已有 out，就用 out；否则从 CSV 读取
    try:
        df = out.copy()
    except NameError:
        df = pd.read_csv("hourly_state_share.csv")

    df = df.sort_values("hour").reset_index(drop=True)

    # 取百分比列（0..1）
    if {"Passenger_pct","Charging_pct","Dispatch_pct","Idle_pct"}.issubset(df.columns):
        P = df["Passenger_pct"] / 100.0
        C = df["Charging_pct"]  / 100.0
        D = df["Dispatch_pct"]  / 100.0
        I = df["Idle_pct"]      / 100.0
    else:
        P = df["Passenger_share"]; C = df["Charging_share"]
        D = df["Dispatch_share"];  I = df["Idle_share"]

    x = np.arange(len(df))        # 0..23
    width = 0.85

    # —— 指定颜色（可按需替换十六进制）——
    # palette = {
    #     "Passenger": "#E97051",  # 红
    #     "Charging":  "#F3A361",  # 橙
    #     "Dispatch":  "#EAC56B",  # 黄
    #     "Idle":      "#67AC96",  # 青
    # }
    #反转颜色
    palette = {
        "Passenger": "#67AC96",  # 红
        "Charging":  "#EAC56B",  # 橙
        "Dispatch":  "#F3A361",  # 黄
        "Idle":      "#E97051",  # 青
    }

    plt.figure(figsize=(6, 4))
    plt.rcParams.update({
        'font.family': 'Calibri'
    })
    bottom = np.zeros_like(x, dtype=float)
    for y, lab in [(P, "Passenger"), (C, "Charging"), (D, "Dispatch"), (I, "Idle")]:
        plt.bar(
            x, y, width=width, bottom=bottom, label=lab,
            color=palette[lab], linewidth=0.1
        )
        bottom += y

    # # —— 标注数值：只标 Passenger 与 Idle，白色字体 ——
    # # Passenger 在最底层：中心 y = P/2
    # for xi, y in enumerate(P):
    #     if y > 0:
    #         plt.text(xi, y / 2, f"{y * 100:.0f}%", ha="center", va="center",
    #                  color="white", fontsize=9, fontweight="bold")
    #
    # # Idle 在最上层：底部 = P+C+D，中心 y = 底部 + I/2
    # top_base = P + C + D
    # for xi, (b, y) in enumerate(zip(top_base, I)):
    #     if y > 0:
    #         plt.text(xi, b + y / 2, f"{y * 100:.0f}%", ha="center", va="center",
    #                  color="white", fontsize=9, fontweight="bold")

    plt.ylim(0, 1)
    plt.ylabel("Percentage")
    plt.xlabel("Time")
    sel = [0, 6, 12, 18, 23]
    plt.xticks(sel, [f"{h}:00" for h in sel])

    plt.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.15),fontsize=12)
    plt.tight_layout()
    # 在 y=0.5 处画一条黑色虚线
    plt.axhline(0.5, color="black", linestyle="--", linewidth=1)
    plt.yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax = plt.gca()
    ax.margins(x=0.02)  # 完全去掉 x 方向自动留白
    # 或者留一点点
    # ax.margins(x=0.01)

    plt.savefig("hourly_state_share_stacked.pdf", dpi=2000, bbox_inches="tight")
    plt.savefig("hourly_state_share_stacked.svg", bbox_inches="tight")
    plt.show()

