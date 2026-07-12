"""Tushare stk_factor_pro Client。"""

from __future__ import annotations

import pandas as pd

from src.common.tushare_client import TushareClient
from src.entities.client_entities.tushare_entities import STK_FACTOR_PRO_FIELDS


class TushareFactorClient:
    def __init__(self) -> None:
        self._ts = TushareClient().ts

    def pull_by_date(self, trade_date: str) -> pd.DataFrame:
        return self._ts.stk_factor_pro(
            trade_date=trade_date,
            fields=STK_FACTOR_PRO_FIELDS,
        )
