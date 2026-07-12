"""指数成分权重 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

INDEX_WEIGHT_COLUMNS: tuple[str, ...] = (
    "index_code", "con_code", "trade_date", "weight",
)

INDEX_CODES: tuple[str, ...] = (
    "000300.SH",  # 沪深300
    "000905.SH",  # 中证500
    "000852.SH",  # 中证1000
    "399006.SZ",  # 创业板指
)


def _normalize_ymd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else ""


def finalize_index_weight(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "index_code" in out.columns:
        out["index_code"] = out["index_code"].astype(str).str.strip()
    if "con_code" in out.columns:
        out["con_code"] = out["con_code"].astype(str).str.strip()
    if "trade_date" in out.columns:
        out["trade_date"] = out["trade_date"].map(_normalize_ymd)
    if "weight" in out.columns:
        out["weight"] = out["weight"].replace({pd.NA: None, float("nan"): None})

    out = out[out["trade_date"].astype(str).str.len() == 8]

    for col in INDEX_WEIGHT_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA if col not in ("index_code", "con_code", "trade_date") else ""

    return out[list(INDEX_WEIGHT_COLUMNS)].reset_index(drop=True)
