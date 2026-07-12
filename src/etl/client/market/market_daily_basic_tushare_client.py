"""Tushare 每日基本面指标 Client。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.entities.client_entities.tushare_entities import tushare_entities
from src.etl.client.market.market_daily_basic_common import finalize_daily_basic
from src.etl.client.base import call_with_network_retry

_acquire_daily_basic_rate_limit = create_rate_limiter(500)


class TushareDailyBasicClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts
        self.daily_basic_fields = tushare_entities.daily_basic

    def pull_daily_basic_by_date(self, *, trade_date: str) -> pd.DataFrame:
        """
        按交易日拉取全市场每日基本面指标。

        参考：https://tushare.pro/document/2?doc_id=32
        """
        td = (trade_date or "").strip()
        if not td:
            return pd.DataFrame()

        _acquire_daily_basic_rate_limit()
        df = call_with_network_retry(
            self.ts.daily_basic,
            trade_date=td,
            fields=self.daily_basic_fields,
        )
        return finalize_daily_basic(df)
