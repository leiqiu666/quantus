"""K 线 Client 共用：实体列定义、结果归一化与校验。"""

from __future__ import annotations

import pandas as pd

# 与 kline_daily 实体 / Tushare daily 字段对齐
KLINE_DAILY_COLUMNS: tuple[str, ...] = (
    "ts_code",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "pre_close",
    "change",
    "pct_chg",
    "vol",
    "amount",
)

KLINE_ADJ_FACTOR_COLUMNS: tuple[str, ...] = ("ts_code", "trade_date", "adj_factor")
KLINE_STK_LIMIT_COLUMNS: tuple[str, ...] = ("ts_code", "trade_date", "up_limit", "down_limit")
KLINE_DAILY_SATELLITE_COLUMNS: tuple[str, ...] = (
    "adj_factor",
    "up_limit",
    "down_limit",
)


def is_usable_kline_daily(df: pd.DataFrame | None) -> bool:
    """日线结果是否可入库：非空且含 ts_code、trade_date。"""
    if df is None or df.empty:
        return False
    return "ts_code" in df.columns and "trade_date" in df.columns


def is_usable_kline_adj_factor(df: pd.DataFrame | None) -> bool:
    """复权因子结果是否可入库。"""
    if not is_usable_kline_daily(df):
        return False
    return "adj_factor" in df.columns


def finalize_kline_daily(
    df: pd.DataFrame | None,
    *,
    amount_in_wan_yuan: bool = False,
) -> pd.DataFrame:
    """
    将 Client 原始 DataFrame 整理为 kline_daily 实体可写入格式。

    Args:
        df: 原始结果。
        amount_in_wan_yuan: TDX 的 amount 为万元，乘 10 转为千元（与 Tushare 一致）。
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    if amount_in_wan_yuan and "amount" in out.columns:
        out["amount"] = pd.to_numeric(out["amount"], errors="coerce") * 10
    for col in ("pre_close", "change", "pct_chg"):
        if col not in out.columns:
            out[col] = pd.NA
    for col in KLINE_DAILY_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    result = out[list(KLINE_DAILY_COLUMNS)].copy()
    return result if is_usable_kline_daily(result) else pd.DataFrame()


def is_usable_kline_stk_limit(df: pd.DataFrame | None) -> bool:
    """涨跌停结果是否可入库。"""
    if not is_usable_kline_daily(df):
        return False
    return "up_limit" in df.columns and "down_limit" in df.columns


def finalize_kline_adj_factor(df: pd.DataFrame | None) -> pd.DataFrame:
    """将 Client 原始 DataFrame 整理为 kline_daily.adj_factor 可写入格式。"""
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    for col in KLINE_ADJ_FACTOR_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    result = out[list(KLINE_ADJ_FACTOR_COLUMNS)].copy()
    return result if is_usable_kline_adj_factor(result) else pd.DataFrame()


def finalize_kline_stk_limit(df: pd.DataFrame | None) -> pd.DataFrame:
    """将 Client 原始 DataFrame 整理为 kline_daily 涨跌停字段可写入格式。"""
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    for col in KLINE_STK_LIMIT_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    result = out[list(KLINE_STK_LIMIT_COLUMNS)].copy()
    return result if is_usable_kline_stk_limit(result) else pd.DataFrame()
