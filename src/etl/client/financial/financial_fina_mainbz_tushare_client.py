"""主营业务构成 Tushare Client（fina_mainbz_vip 按报告期全市场）。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry

FINA_MAINBZ_COLUMNS: tuple[str, ...] = (
    "ts_code",
    "end_date",
    "bz_item",
    "bz_code",
    "bz_sales",
    "bz_profit",
    "bz_cost",
    "curr_type",
    "update_flag",
)

_STR_COLS = ("ts_code", "bz_item", "bz_code", "curr_type", "update_flag")
_DATE_COLS = ("end_date",)
_NUM_COLS = ("bz_sales", "bz_profit", "bz_cost")

_acquire_rate_limit = create_rate_limiter(200)

_PAGE_SIZE = 100
_BZ_TYPES = ("P", "D", "I")


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


def finalize_fina_mainbz(df: pd.DataFrame | None) -> pd.DataFrame:
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

    for col in FINA_MAINBZ_COLUMNS:
        if col not in out.columns:
            out[col] = "" if col in _DATE_COLS or col in ("bz_item", "bz_code") else pd.NA

    return out[list(FINA_MAINBZ_COLUMNS)].reset_index(drop=True)


class TushareFinaMainbzClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def _pull_vip_type(self, period: str, bz_type: str) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        offset = 0
        while True:
            _acquire_rate_limit()
            page = call_with_network_retry(
                self.ts.fina_mainbz_vip,
                period=period,
                type=bz_type,
                fields=",".join(FINA_MAINBZ_COLUMNS),
                offset=offset,
                limit=_PAGE_SIZE,
            )
            if page is None or page.empty:
                break
            frames.append(page)
            if len(page) < _PAGE_SIZE:
                break
            offset += _PAGE_SIZE

        if not frames:
            return pd.DataFrame()
        return finalize_fina_mainbz(pd.concat(frames, ignore_index=True))

    def pull_fina_mainbz_vip_by_period(self, period: str) -> pd.DataFrame:
        """按报告期全市场拉取（产品 P / 地区 D / 行业 I 各一次分页序列）。"""
        p = (period or "").strip()
        if not p:
            return pd.DataFrame()

        frames = [self._pull_vip_type(p, t) for t in _BZ_TYPES]
        frames = [f for f in frames if not f.empty]
        if not frames:
            return pd.DataFrame()
        return finalize_fina_mainbz(pd.concat(frames, ignore_index=True))
