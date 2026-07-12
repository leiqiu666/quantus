"""每日基本面指标 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

# Tushare daily_basic 字段列表（与 tushare_entities.daily_basic 保持一致）
DAILY_BASIC_COLUMNS: tuple[str, ...] = (
    "ts_code",
    "trade_date",
    "close",
    "turnover_rate",
    "turnover_rate_f",
    "volume_ratio",
    "pe",
    "pe_ttm",
    "pb",
    "ps",
    "ps_ttm",
    "dv_ratio",
    "dv_ttm",
    "total_share",
    "float_share",
    "free_share",
    "total_mv",
    "circ_mv",
)


def _normalize_ymd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else ""


def finalize_daily_basic(df: pd.DataFrame | None) -> pd.DataFrame:
    """对齐 daily_basic 实体列，日期归一化，数值列 NaN 转 None。"""
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    # 字符串列处理
    if "ts_code" in out.columns:
        out["ts_code"] = out["ts_code"].astype(str).str.strip()

    # 日期列归一化
    if "trade_date" in out.columns:
        out["trade_date"] = out["trade_date"].map(_normalize_ymd)

    # 数值列 NaN 转 None（保持 PG NULL 语义）
    numeric_cols = [
        "close", "turnover_rate", "turnover_rate_f", "volume_ratio",
        "pe", "pe_ttm", "pb", "ps", "ps_ttm",
        "dv_ratio", "dv_ttm",
        "total_share", "float_share", "free_share",
        "total_mv", "circ_mv",
    ]
    for col in numeric_cols:
        if col in out.columns:
            out[col] = out[col].replace({pd.NA: None, float("nan"): None})

    # 过滤掉 trade_date 不合法的行
    out = out[out["trade_date"].astype(str).str.len() == 8]

    # 确保所有必需列存在
    for col in DAILY_BASIC_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA if col not in ("ts_code", "trade_date") else ""

    return out[list(DAILY_BASIC_COLUMNS)].reset_index(drop=True)
