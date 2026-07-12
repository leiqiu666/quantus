"""交易日历 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

# Tushare trade_cal 文档列：exchange, cal_date, is_open, pretrade_date
TRADE_CAL_COLUMNS: tuple[str, ...] = (
    "exchange",
    "cal_date",
    "is_open",
    "pretrade_date",
)

# https://tushare.pro/document/2?doc_id=26
TRADE_CAL_EXCHANGES: tuple[str, ...] = (
    "SSE",
    "SZSE",
    "CFFEX",
    "SHFE",
    "CZCE",
    "DCE",
    "INE",
)


def _normalize_ymd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else ""


def is_usable_trade_cal(df: pd.DataFrame | None) -> bool:
    if df is None or df.empty:
        return False
    return "exchange" in df.columns and "cal_date" in df.columns


def finalize_trade_cal(df: pd.DataFrame | None) -> pd.DataFrame:
    """对齐 trade_cal 实体列，日期归一化为 YYYYMMDD。"""
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    out["cal_date"] = out["cal_date"].map(_normalize_ymd)
    if "pretrade_date" in out.columns:
        out["pretrade_date"] = out["pretrade_date"].map(_normalize_ymd)
    if "is_open" in out.columns:
        out["is_open"] = out["is_open"].astype(str).str.strip()
    if "exchange" in out.columns:
        out["exchange"] = out["exchange"].astype(str).str.strip().str.upper()

    out = out[out["cal_date"].astype(str).str.len() == 8]
    for col in TRADE_CAL_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[list(TRADE_CAL_COLUMNS)].reset_index(drop=True)
