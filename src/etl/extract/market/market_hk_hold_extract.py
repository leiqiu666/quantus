"""沪深港股通持股明细 Extract：编排 Tushare Client。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.market.market_hk_hold_tushare_client import TushareHkHoldClient


class HkHoldExtract:
    def __init__(self) -> None:
        self._client = TushareHkHoldClient()

    def pull_hk_hold_by_date(self, *, trade_date: str) -> pd.DataFrame:
        return self._client.pull_hk_hold_by_date(trade_date=trade_date)
