"""Tushare 技术面因子 Client（基于 stk_factor_pro 后复权字段）。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry
from src.etl.client.kline.kline_stock_factor_common import STK_FACTOR_PRO_FIELDS, finalize_stk_factor

_acquire_stk_factor_rate_limit = create_rate_limiter(100)


class TushareStkFactorClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_stk_factor_by_date(self, *, trade_date: str) -> pd.DataFrame:
        td = (trade_date or "").strip()
        if not td:
            return pd.DataFrame()

        _acquire_stk_factor_rate_limit()
        df = call_with_network_retry(
            self.ts.stk_factor_pro,
            trade_date=td,
            fields=STK_FACTOR_PRO_FIELDS,
        )
        return finalize_stk_factor(df)

    def pull_stk_factor_by_ts_code(
        self,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        if not (ts_code or "").strip():
            return pd.DataFrame()

        _acquire_stk_factor_rate_limit()
        df = call_with_network_retry(
            self.ts.stk_factor_pro,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields=STK_FACTOR_PRO_FIELDS,
        )
        return finalize_stk_factor(df)
