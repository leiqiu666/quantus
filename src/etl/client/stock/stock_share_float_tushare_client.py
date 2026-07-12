"""Tushare 限售股解禁 Client：按解禁日全市场拉取。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry
from src.etl.client.stock.stock_share_float_common import (
    STOCK_SHARE_FLOAT_COLUMNS,
    finalize_stock_share_float,
)

_acquire_rate_limit = create_rate_limiter(200)

_PAGE_SIZE = 6000


class TushareStockShareFloatClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_share_float_by_float_date(self, *, float_date: str) -> pd.DataFrame:
        fd = (float_date or "").strip()
        if not fd:
            return pd.DataFrame()

        frames: list[pd.DataFrame] = []
        offset = 0
        while True:
            _acquire_rate_limit()
            page = call_with_network_retry(
                self.ts.share_float,
                float_date=fd,
                fields=",".join(STOCK_SHARE_FLOAT_COLUMNS),
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

        return finalize_stock_share_float(pd.concat(frames, ignore_index=True))
