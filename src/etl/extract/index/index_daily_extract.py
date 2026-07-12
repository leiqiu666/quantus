"""指数日线 Extract。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.index.index_daily_tushare_client import TushareIndexDailyClient


class IndexDailyExtract:
    def __init__(self) -> None:
        self._client = TushareIndexDailyClient()

    def pull_index_daily(
        self,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        return self._client.pull_index_daily(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )
