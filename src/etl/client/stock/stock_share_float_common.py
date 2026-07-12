"""限售股解禁 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

STOCK_SHARE_FLOAT_COLUMNS: tuple[str, ...] = (
    "ts_code",
    "ann_date",
    "float_date",
    "float_share",
    "float_ratio",
    "holder_name",
    "share_type",
)

_STR_COLS = ("ts_code", "holder_name", "share_type")
_DATE_COLS = ("ann_date", "float_date")
_NUM_COLS = ("float_share", "float_ratio")


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


def finalize_stock_share_float(df: pd.DataFrame | None) -> pd.DataFrame:
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

    for col in STOCK_SHARE_FLOAT_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA if col not in _DATE_COLS else ""

    return out[list(STOCK_SHARE_FLOAT_COLUMNS)].reset_index(drop=True)
