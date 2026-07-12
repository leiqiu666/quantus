"""每日基本面指标 Workflow：单日 Extract→Load 串联。"""

from __future__ import annotations

from src.etl.extract.market.market_daily_basic_extract import DailyBasicExtract
from src.etl.load.market.market_daily_basic_load import DailyBasicLoad


class DailyBasicWorkflow:
    def __init__(self) -> None:
        self.daily_basic_extract = DailyBasicExtract()
        self.daily_basic_load = DailyBasicLoad()

    def pull_daily_basic_by_date(self, *, trade_date: str) -> int:
        df = self.daily_basic_extract.pull_daily_basic_by_date(trade_date=trade_date)
        return self.daily_basic_load.load_daily_basic(df)
