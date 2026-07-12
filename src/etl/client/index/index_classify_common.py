"""申万行业分类 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

INDEX_CLASSIFY_COLUMNS: tuple[str, ...] = (
    "index_code",
    "industry_name",
    "level",
    "industry_code",
    "src",
    "is_pub",
    "parent_code",
)

INDEX_CLASSIFY_LEVELS: tuple[str, ...] = ("L1", "L2", "L3")
INDEX_CLASSIFY_SRC = "SW2021"


def _normalize_str(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def finalize_index_classify(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    for col in INDEX_CLASSIFY_COLUMNS:
        if col in out.columns:
            out[col] = out[col].map(_normalize_str)

    out = out[out["index_code"].astype(str).str.len() > 0]

    for col in INDEX_CLASSIFY_COLUMNS:
        if col not in out.columns:
            out[col] = ""

    if "src" in out.columns:
        out["src"] = out["src"].replace("", INDEX_CLASSIFY_SRC)

    return out[list(INDEX_CLASSIFY_COLUMNS)].reset_index(drop=True)
