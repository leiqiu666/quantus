"""Tushare 大宗交易 Client：支持分页（单次 1000 条）。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry
from src.etl.client.market.market_block_trade_common import (
    BLOCK_TRADE_COLUMNS,
    finalize_block_trade,
)

_acquire_rate_limit = create_rate_limiter(200)

_PAGE_SIZE = 1000


class TushareBlockTradeClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_block_trade_by_date(self, trade_date: str) -> pd.DataFrame:
        td = (trade_date or "").strip()
        if not td:
            return pd.DataFrame()

        frames: list[pd.DataFrame] = []
        offset = 0
        while True:
            _acquire_rate_limit()
            page = call_with_network_retry(
                self.ts.block_trade,
                trade_date=td,
                fields=",".join(BLOCK_TRADE_COLUMNS),
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

        return finalize_block_trade(pd.concat(frames, ignore_index=True))
