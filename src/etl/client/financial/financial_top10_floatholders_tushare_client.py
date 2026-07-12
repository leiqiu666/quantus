"""Tushare 前十大流通股东 Client：按公告日全市场拉取。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry
from src.etl.client.financial.financial_top10_floatholders_common import (
    TOP10_FLOATHOLDERS_COLUMNS,
    finalize_top10_floatholders,
)

_acquire_rate_limit = create_rate_limiter(200)

_PAGE_SIZE = 3000


class TushareTop10FloatholdersClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_top10_floatholders_by_ann_date(self, *, ann_date: str) -> pd.DataFrame:
        ad = (ann_date or "").strip()
        if not ad:
            return pd.DataFrame()

        frames: list[pd.DataFrame] = []
        offset = 0
        while True:
            _acquire_rate_limit()
            page = call_with_network_retry(
                self.ts.top10_floatholders,
                ann_date=ad,
                fields=",".join(TOP10_FLOATHOLDERS_COLUMNS),
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

        return finalize_top10_floatholders(pd.concat(frames, ignore_index=True))
