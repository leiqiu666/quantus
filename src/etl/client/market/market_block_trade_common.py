"""大宗交易 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

BLOCK_TRADE_COLUMNS: tuple[str, ...] = (
    "ts_code", "trade_date", "price", "vol", "amount", "buyer", "seller",
)

_STR_COLS = ("ts_code", "buyer", "seller")
_NUM_COLS = ("price", "vol", "amount")


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


def finalize_block_trade(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "trade_date" in out.columns:
        out["trade_date"] = out["trade_date"].map(_normalize_ymd)

    for col in _STR_COLS:
        if col in out.columns:
            out[col] = out[col].map(_normalize_str)

    for col in _NUM_COLS:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").where(
                out[col].notna(), None
            )

    out = out[out["trade_date"].astype(str).str.len() == 8]

    for col in BLOCK_TRADE_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA if col != "trade_date" else ""

    return out[list(BLOCK_TRADE_COLUMNS)].reset_index(drop=True)
