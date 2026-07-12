"""指数日线 Workflow。"""

from __future__ import annotations

from src.etl.extract.index.index_daily_extract import IndexDailyExtract
from src.etl.load.index.index_daily_load import IndexDailyLoad


class IndexDailyWorkflow:
    def __init__(self) -> None:
        self.extract = IndexDailyExtract()
        self.load = IndexDailyLoad()

    def pull_index_daily(
        self,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> int:
        df = self.extract.pull_index_daily(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )
        return self.load.load_index_daily(df)
