"""沪深港股通持股明细 Workflow：单日 Extract→Load 串联。"""

from __future__ import annotations

from src.etl.extract.market.market_hk_hold_extract import HkHoldExtract
from src.etl.load.market.market_hk_hold_load import HkHoldLoad


class HkHoldWorkflow:
    def __init__(self) -> None:
        self.hk_hold_extract = HkHoldExtract()
        self.hk_hold_load = HkHoldLoad()

    def pull_hk_hold_by_date(self, *, trade_date: str) -> int:
        df = self.hk_hold_extract.pull_hk_hold_by_date(trade_date=trade_date)
        return self.hk_hold_load.load_hk_hold(df)
