"""沪深港通资金流向 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

MONEYFLOW_HSGT_COLUMNS: tuple[str, ...] = (
    "trade_date",
    "ggt_ss",
    "ggt_sz",
    "hgt",
    "sgt",
    "north_money",
    "south_money",
)

_NUMERIC_COLS = tuple(c for c in MONEYFLOW_HSGT_COLUMNS if c != "trade_date")


def _normalize_ymd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else ""


def finalize_moneyflow_hsgt(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "trade_date" in out.columns:
        out["trade_date"] = out["trade_date"].map(_normalize_ymd)

    for col in _NUMERIC_COLS:
        if col in out.columns:
            out[col] = out[col].replace({pd.NA: None, float("nan"): None})

    out = out[out["trade_date"].astype(str).str.len() == 8]

    for col in MONEYFLOW_HSGT_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA if col != "trade_date" else ""

    return out[list(MONEYFLOW_HSGT_COLUMNS)].reset_index(drop=True)
