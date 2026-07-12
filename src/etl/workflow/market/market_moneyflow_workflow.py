"""个股资金流向 Workflow：单日 Extract→Load 串联。"""

from __future__ import annotations

from src.etl.extract.market.market_moneyflow_extract import MoneyflowExtract
from src.etl.load.market.market_moneyflow_load import MoneyflowLoad


class MoneyflowWorkflow:
    def __init__(self) -> None:
        self.moneyflow_extract = MoneyflowExtract()
        self.moneyflow_load = MoneyflowLoad()

    def pull_moneyflow_by_date(self, *, trade_date: str) -> int:
        df = self.moneyflow_extract.pull_moneyflow_by_date(trade_date=trade_date)
        return self.moneyflow_load.load_moneyflow(df)
