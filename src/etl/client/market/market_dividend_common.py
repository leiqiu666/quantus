"""分红送股 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

DIVIDEND_COLUMNS: tuple[str, ...] = (
    "ts_code",
    "end_date",
    "ann_date",
    "div_proc",
    "stk_div",
    "stk_bo_rate",
    "stk_co_rate",
    "cash_div",
    "cash_div_tax",
    "record_date",
    "ex_date",
    "pay_date",
    "div_listdate",
    "imp_ann_date",
    "base_date",
    "base_share",
)


def _normalize_ymd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else ""


_DATE_COLS = ("end_date", "ann_date", "record_date", "ex_date", "pay_date", "div_listdate", "imp_ann_date", "base_date")

_NUMERIC_COLS = ("stk_div", "stk_bo_rate", "stk_co_rate", "cash_div", "cash_div_tax", "base_share")


def finalize_dividend(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "ts_code" in out.columns:
        out["ts_code"] = out["ts_code"].astype(str).str.strip()
    if "div_proc" in out.columns:
        out["div_proc"] = out["div_proc"].astype(str).str.strip()

    for col in _DATE_COLS:
        if col in out.columns:
            out[col] = out[col].map(_normalize_ymd)

    for col in _NUMERIC_COLS:
        if col in out.columns:
            out[col] = out[col].replace({pd.NA: None, float("nan"): None})

    out = out[out["end_date"].astype(str).str.len() == 8]

    for col in DIVIDEND_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA if col not in ("ts_code", "end_date", "div_proc") else ""

    return out[list(DIVIDEND_COLUMNS)].reset_index(drop=True)
