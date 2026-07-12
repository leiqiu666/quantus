"""龙虎榜 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

TOP_LIST_COLUMNS: tuple[str, ...] = (
    "trade_date", "ts_code", "name", "close", "pct_change",
    "turnover_rate", "amount", "l_sell", "l_buy", "l_amount",
    "net_amount", "net_rate", "amount_rate", "float_value", "reason",
)

TOP_INST_COLUMNS: tuple[str, ...] = (
    "trade_date", "ts_code", "exalter", "side",
    "buy", "buy_rate", "sell", "sell_rate", "net_buy", "reason",
)

_TOP_LIST_STR_COLS = ("ts_code", "name", "reason")
_TOP_LIST_NUM_COLS = tuple(
    c for c in TOP_LIST_COLUMNS
    if c not in ("trade_date",) and c not in _TOP_LIST_STR_COLS
)

_TOP_INST_STR_COLS = ("ts_code", "exalter", "side", "reason")
_TOP_INST_NUM_COLS = tuple(
    c for c in TOP_INST_COLUMNS
    if c not in ("trade_date",) and c not in _TOP_INST_STR_COLS
)


def _normalize_ymd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else ""


def _normalize_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    s = str(value).strip()
    if s.lower() in ("none", "nan", "null"):
        return ""
    return s


def _finalize(df: pd.DataFrame | None, columns: tuple[str, ...], str_cols: tuple[str, ...], num_cols: tuple[str, ...]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "trade_date" in out.columns:
        out["trade_date"] = out["trade_date"].map(_normalize_ymd)

    for col in str_cols:
        if col in out.columns:
            out[col] = out[col].map(_normalize_str)

    for col in num_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").where(
                out[col].notna(), None
            )

    out = out[out["trade_date"].astype(str).str.len() == 8]

    for col in columns:
        if col not in out.columns:
            out[col] = pd.NA if col != "trade_date" else ""

    return out[list(columns)].reset_index(drop=True)


def finalize_top_list(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is not None and not df.empty and "float_values" in df.columns:
        df = df.rename(columns={"float_values": "float_value"})
    return _finalize(df, TOP_LIST_COLUMNS, _TOP_LIST_STR_COLS, _TOP_LIST_NUM_COLS)


def finalize_top_inst(df: pd.DataFrame | None) -> pd.DataFrame:
    return _finalize(df, TOP_INST_COLUMNS, _TOP_INST_STR_COLS, _TOP_INST_NUM_COLS)
