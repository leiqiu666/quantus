"""沪深港股通持股明细 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

HK_HOLD_COLUMNS: tuple[str, ...] = (
    "code",
    "trade_date",
    "ts_code",
    "name",
    "vol",
    "ratio",
    "exchange",
)

_NUMERIC_COLS = ("vol", "ratio")
_STRING_COLS = ("code", "ts_code", "name", "exchange")


def _normalize_ymd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else ""


def _normalize_str(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip()
    return "" if s in ("nan", "None", "") else s


def finalize_hk_hold(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "trade_date" in out.columns:
        out["trade_date"] = out["trade_date"].map(_normalize_ymd)
    for col in _STRING_COLS:
        if col in out.columns:
            out[col] = out[col].map(_normalize_str)

    for col in _NUMERIC_COLS:
        if col in out.columns:
            out[col] = out[col].replace({pd.NA: None, float("nan"): None})

    out = out[out["trade_date"].astype(str).str.len() == 8]

    for col in HK_HOLD_COLUMNS:
        if col not in out.columns:
            if col in _STRING_COLS:
                out[col] = ""
            else:
                out[col] = pd.NA

    return out[list(HK_HOLD_COLUMNS)].reset_index(drop=True)
