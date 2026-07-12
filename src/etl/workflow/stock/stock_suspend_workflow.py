"""停复牌 Workflow：单日 Extract→Load。"""

from __future__ import annotations

from src.etl.extract.stock.stock_suspend_extract import SuspendExtract
from src.etl.load.stock.stock_suspend_load import SuspendLoad


class SuspendWorkflow:
    def __init__(self) -> None:
        self.extract = SuspendExtract()
        self.load = SuspendLoad()

    def pull_suspend_by_date(self, trade_date: str) -> int:
        df = self.extract.pull_suspend_by_date(trade_date)
        return self.load.load_suspend(df)
