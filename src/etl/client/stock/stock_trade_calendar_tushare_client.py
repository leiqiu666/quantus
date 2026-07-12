"""Tushare 交易日历 Client。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.entities.client_entities.tushare_entities import tushare_entities
from src.etl.client.stock.stock_trade_calendar_common import finalize_trade_cal
from src.etl.client.base import call_with_network_retry

_acquire_trade_cal_rate_limit = create_rate_limiter(200)


class TushareTradeCalClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts
        self.trade_cal_fields = tushare_entities.trade_cal

    def pull_trade_cal_range(
        self,
        *,
        exchange: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        拉取 [start_date, end_date] 交易日历（含休市日，不限 is_open）。

        参考：https://tushare.pro/document/2?doc_id=26
        """
        ex = (exchange or "").strip().upper()
        start = (start_date or "").strip()
        end = (end_date or "").strip()
        if not ex or not start or not end or start > end:
            return pd.DataFrame()

        _acquire_trade_cal_rate_limit()
        df = call_with_network_retry(
            self.ts.trade_cal,
            exchange=ex,
            start_date=start,
            end_date=end,
            fields=self.trade_cal_fields,
        )
        return finalize_trade_cal(df)
