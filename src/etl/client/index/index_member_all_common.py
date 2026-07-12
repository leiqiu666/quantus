"""申万行业成分 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

INDEX_MEMBER_ALL_COLUMNS: tuple[str, ...] = (
    "l1_code",
    "l1_name",
    "l2_code",
    "l2_name",
    "l3_code",
    "l3_name",
    "ts_code",
    "name",
    "in_date",
    "out_date",
    "is_new",
)


def _normalize_ymd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else ""


def _normalize_str(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def finalize_index_member_all(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    for col in (
        "l1_code",
        "l1_name",
        "l2_code",
        "l2_name",
        "l3_code",
        "l3_name",
        "ts_code",
        "name",
        "is_new",
    ):
        if col in out.columns:
            out[col] = out[col].map(_normalize_str)
    for col in ("in_date", "out_date"):
        if col in out.columns:
            out[col] = out[col].map(_normalize_ymd)

    out = out[out["ts_code"].astype(str).str.len() > 0]

    for col in INDEX_MEMBER_ALL_COLUMNS:
        if col not in out.columns:
            out[col] = ""

    return out[list(INDEX_MEMBER_ALL_COLUMNS)].reset_index(drop=True)
