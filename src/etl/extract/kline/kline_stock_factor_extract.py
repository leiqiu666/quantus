"""技术面因子 Extract：编排 Tushare Client。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.kline.kline_stock_factor_tushare_client import TushareStkFactorClient


class StkFactorExtract:
    def __init__(self) -> None:
        self._client = TushareStkFactorClient()

    def pull_stk_factor_by_date(self, *, trade_date: str) -> pd.DataFrame:
        return self._client.pull_stk_factor_by_date(trade_date=trade_date)

    def pull_stk_factor_by_ts_code(
        self,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        return self._client.pull_stk_factor_by_ts_code(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )
