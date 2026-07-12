"""Tushare 指数日线 Client。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry
from src.etl.client.index.index_daily_common import INDEX_DAILY_COLUMNS, finalize_index_daily

_acquire_index_daily_rate_limit = create_rate_limiter(200)


class TushareIndexDailyClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_index_daily(
        self,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        ts_code = (ts_code or "").strip()
        start_date = (start_date or "").strip()
        end_date = (end_date or "").strip()
        if not ts_code or not start_date or not end_date or start_date > end_date:
            return pd.DataFrame()

        _acquire_index_daily_rate_limit()
        df = call_with_network_retry(
            self.ts.index_daily,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields=",".join(INDEX_DAILY_COLUMNS),
        )
        return finalize_index_daily(df)
