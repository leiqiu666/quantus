"""指数基本信息 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

INDEX_BASIC_COLUMNS: tuple[str, ...] = (
    "ts_code",
    "name",
    "fullname",
    "market",
    "publisher",
    "index_type",
    "category",
    "base_date",
    "base_point",
    "list_date",
    "weight_rule",
    "desc",
    "exp_date",
)

INDEX_BASIC_MARKETS: tuple[str, ...] = (
    "MSCI",
    "CSI",
    "SSE",
    "SZSE",
    "CICC",
    "SW",
    "OTH",
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


def finalize_index_basic(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    for col in ("ts_code", "name", "fullname", "market", "publisher", "index_type", "category", "weight_rule", "desc"):
        if col in out.columns:
            out[col] = out[col].map(_normalize_str)
    for col in ("base_date", "list_date", "exp_date"):
        if col in out.columns:
            out[col] = out[col].map(_normalize_ymd)
    if "base_point" in out.columns:
        out["base_point"] = out["base_point"].replace({pd.NA: None, float("nan"): None})

    out = out[out["ts_code"].astype(str).str.len() > 0]

    for col in INDEX_BASIC_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA if col == "base_point" else ""

    return out[list(INDEX_BASIC_COLUMNS)].reset_index(drop=True)
