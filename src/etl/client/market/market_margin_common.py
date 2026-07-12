"""融资融券明细 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

MARGIN_DETAIL_COLUMNS: tuple[str, ...] = (
    "trade_date", "ts_code",
    "rzye", "rzmre", "rzche", "rzrqye",
    "rqye", "rqyl", "rqmcl", "rqchl",
)

_NUMERIC_COLS = tuple(c for c in MARGIN_DETAIL_COLUMNS if c not in ("ts_code", "trade_date"))


def _normalize_ymd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else ""


def finalize_margin_detail(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "ts_code" in out.columns:
        out["ts_code"] = out["ts_code"].astype(str).str.strip()
    if "trade_date" in out.columns:
        out["trade_date"] = out["trade_date"].map(_normalize_ymd)

    for col in _NUMERIC_COLS:
        if col in out.columns:
            out[col] = out[col].replace({pd.NA: None, float("nan"): None})

    out = out[out["trade_date"].astype(str).str.len() == 8]

    for col in MARGIN_DETAIL_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA if col not in ("ts_code", "trade_date") else ""

    return out[list(MARGIN_DETAIL_COLUMNS)].reset_index(drop=True)
