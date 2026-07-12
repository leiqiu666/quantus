"""Tushare 指数基本信息 Client。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry
from src.etl.client.index.index_basic_common import (
    INDEX_BASIC_COLUMNS,
    INDEX_BASIC_MARKETS,
    finalize_index_basic,
)

_acquire_index_basic_rate_limit = create_rate_limiter(200)


class TushareIndexBasicClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_index_basic_by_market(self, *, market: str) -> pd.DataFrame:
        market = (market or "").strip()
        if not market:
            return pd.DataFrame()

        _acquire_index_basic_rate_limit()
        df = call_with_network_retry(
            self.ts.index_basic,
            market=market,
            fields=",".join(INDEX_BASIC_COLUMNS),
        )
        return finalize_index_basic(df)

    def pull_index_basic_all_markets(self) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        for market in INDEX_BASIC_MARKETS:
            df = self.pull_index_basic_by_market(market=market)
            if df is not None and not df.empty:
                frames.append(df)
        if not frames:
            return pd.DataFrame()
        merged = pd.concat(frames, ignore_index=True)
        return merged.drop_duplicates(subset=["ts_code"], keep="first").reset_index(drop=True)
