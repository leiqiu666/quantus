"""股东户数 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

STK_HOLDERNUMBER_COLUMNS: tuple[str, ...] = (
    "ts_code", "ann_date", "end_date", "holder_num",
)


def _normalize_ymd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else ""


def finalize_stk_holdernumber(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "ts_code" in out.columns:
        out["ts_code"] = out["ts_code"].astype(str).str.strip()
    for date_col in ("ann_date", "end_date"):
        if date_col in out.columns:
            out[date_col] = out[date_col].map(_normalize_ymd)

    if "holder_num" in out.columns:
        out["holder_num"] = out["holder_num"].replace({pd.NA: None, float("nan"): None})

    out = out[out["end_date"].astype(str).str.len() == 8]

    for col in STK_HOLDERNUMBER_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA if col != "ts_code" else ""

    return out[list(STK_HOLDERNUMBER_COLUMNS)].reset_index(drop=True)
