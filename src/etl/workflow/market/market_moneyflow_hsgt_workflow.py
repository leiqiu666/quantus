"""沪深港通资金流向 Workflow：单日 Extract→Load 串联。"""

from __future__ import annotations

from src.etl.extract.market.market_moneyflow_hsgt_extract import MoneyflowHsgtExtract
from src.etl.load.market.market_moneyflow_hsgt_load import MoneyflowHsgtLoad


class MoneyflowHsgtWorkflow:
    def __init__(self) -> None:
        self.moneyflow_hsgt_extract = MoneyflowHsgtExtract()
        self.moneyflow_hsgt_load = MoneyflowHsgtLoad()

    def pull_moneyflow_hsgt_by_date(self, *, trade_date: str) -> int:
        df = self.moneyflow_hsgt_extract.pull_moneyflow_hsgt_by_date(trade_date=trade_date)
        return self.moneyflow_hsgt_load.load_moneyflow_hsgt(df)
