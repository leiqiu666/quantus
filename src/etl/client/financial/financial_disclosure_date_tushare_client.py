"""财报披露计划 Tushare Client（disclosure_date）。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry

DISCLOSURE_DATE_COLUMNS: tuple[str, ...] = (
    "ts_code",
    "ann_date",
    "end_date",
    "pre_date",
    "actual_date",
    "modify_date",
)

_DATE_COLS = ("ann_date", "end_date", "pre_date", "actual_date", "modify_date")

_acquire_rate_limit = create_rate_limiter(200)


def _normalize_ymd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else ""


def finalize_disclosure_date(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "ts_code" in out.columns:
        out["ts_code"] = out["ts_code"].astype(str).str.strip()

    for col in _DATE_COLS:
        if col in out.columns:
            out[col] = out[col].map(_normalize_ymd)
        else:
            out[col] = ""

    for col in DISCLOSURE_DATE_COLUMNS:
        if col not in out.columns:
            out[col] = "" if col in _DATE_COLS else pd.NA

    return out[list(DISCLOSURE_DATE_COLUMNS)].reset_index(drop=True)


class TushareDisclosureDateClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_disclosure_date_by_period(self, period: str) -> pd.DataFrame:
        p = (period or "").strip()
        if not p:
            return pd.DataFrame()

        _acquire_rate_limit()
        df = call_with_network_retry(
            self.ts.disclosure_date,
            end_date=p,
            fields=",".join(DISCLOSURE_DATE_COLUMNS),
        )
        return finalize_disclosure_date(df)
