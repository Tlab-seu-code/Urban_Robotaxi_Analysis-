# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path

IN_FILE = "武汉市POI数据.csv"   # 与本脚本位于同一文件夹
OUT_FILE = None               # 留空将自动生成 “_六类” 后缀

# === 映射：原始 -> 六类 ===
MAP = {
    '旅游景点': 'leisure',
    '酒店住宿': 'home',
    '休闲娱乐': 'leisure',
    '科教文化': 'education',
    '购物消费': 'leisure',
    '生活服务': 'leisure',
    '医疗保健': 'healthcare',
    '公司企业': 'work',
    '交通设施': 'traffic',
    '餐饮美食': 'leisure',
    '运动健身': 'leisure',
    '汽车相关': 'work',
    '金融机构': 'work',
    '商务住宅': 'home',
}

# 如果你清楚原始分类列名（比如 "POI大类"），可以在这里写上；否则留空让程序自动识别
SOURCE_COL_MANUAL = None  # 例如： "POI大类"

def read_csv_cn(path):
    try:
        return pd.read_csv(path)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="gb18030")

def detect_source_col(df, manual=None):
    if manual and manual in df.columns:
        return manual
    candidates = [
        "POI大类","POI分类","一级分类","大类","类别","类型",
        "行业大类","分类","poi大类","poi类别",
        "category","class","type"
    ]
    for c in candidates:
        if c in df.columns:
            return c
    raise ValueError(
        "未能自动识别原始分类列名。请将 SOURCE_COL_MANUAL 设置为正确列名。\n"
        f"表头示例：{list(df.columns)[:20]}"
    )

def normalize_cell(x):
    if pd.isna(x):
        return x
    return str(x).strip()

def main():
    df = read_csv_cn(IN_FILE)
    src = detect_source_col(df, manual=SOURCE_COL_MANUAL)

    # 轻量规范化：去除前后空格
    src_series = df[src].apply(normalize_cell)

    # 映射为六类并新增列 “POI类型”
    df["POI类型"] = src_series.map(MAP)

    # 将“POI类型”放到最后一列
    cols = [c for c in df.columns if c != "POI类型"] + ["POI类型"]
    df = df[cols]

    # 输出路径
    if OUT_FILE is None:
        p = Path(IN_FILE)
        out_path = p.with_name(p.stem + "_六类" + p.suffix)
    else:
        out_path = Path(OUT_FILE)

    # 保存（UTF-8-SIG 便于 Excel 打开中文）
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    # 小结统计（包含缺失）
    vc = df["POI类型"].value_counts(dropna=False)
    print("已保存：", out_path)
    print("\nPOI类型分布（含缺失）：")
    print(vc.to_string())

if __name__ == "__main__":
    main()
