"""前十大股东 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

TOP10_HOLDERS_COLUMNS: tuple[str, ...] = (
    "ts_code", "ann_date", "end_date", "holder_name",
    "hold_amount", "hold_ratio", "hold_float_ratio",
    "hold_change", "holder_type",
)

_STR_COLS = ("ts_code", "holder_name", "holder_type")
_DATE_COLS = ("ann_date", "end_date")
_NUM_COLS = ("hold_amount", "hold_ratio", "hold_float_ratio", "hold_change")


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


def finalize_top10_holders(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    for col in _DATE_COLS:
        if col in out.columns:
            out[col] = out[col].map(_normalize_ymd)

    for col in _STR_COLS:
        if col in out.columns:
            out[col] = out[col].map(_normalize_str)

    for col in _NUM_COLS:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").where(
                out[col].notna(), None
            )

    for col in TOP10_HOLDERS_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA if col not in _DATE_COLS else ""

    return out[list(TOP10_HOLDERS_COLUMNS)].reset_index(drop=True)
