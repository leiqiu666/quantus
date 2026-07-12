"""停复牌 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

SUSPEND_COLUMNS: tuple[str, ...] = (
    "ts_code",
    "trade_date",
    "suspend_timing",
    "suspend_type",
)

_VALID_SUSPEND_TYPES = frozenset({"S", "R"})


def _normalize_ymd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else ""


def finalize_suspend(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "ts_code" in out.columns:
        out["ts_code"] = out["ts_code"].astype(str).str.strip()

    if "trade_date" in out.columns:
        out["trade_date"] = out["trade_date"].map(_normalize_ymd)

    if "suspend_type" in out.columns:
        out["suspend_type"] = (
            out["suspend_type"].astype(str).str.strip().str.upper()
        )

    if "suspend_timing" in out.columns:
        out["suspend_timing"] = out["suspend_timing"].apply(
            lambda v: ""
            if v is None or (isinstance(v, float) and pd.isna(v))
            else str(v).strip()
        )

    out = out[out["trade_date"].astype(str).str.len() == 8]
    out = out[out["suspend_type"].isin(_VALID_SUSPEND_TYPES)]

    for col in SUSPEND_COLUMNS:
        if col not in out.columns:
            out[col] = "" if col in ("suspend_timing",) else pd.NA

    return out[list(SUSPEND_COLUMNS)].reset_index(drop=True)
