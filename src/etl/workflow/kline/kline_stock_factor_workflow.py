"""技术面因子 Workflow：单股 Extract→Load 串联。"""

from __future__ import annotations

from src.etl.extract.kline.kline_stock_factor_extract import StkFactorExtract
from src.etl.load.kline.kline_stock_factor_load import StkFactorLoad


class StkFactorWorkflow:
    def __init__(self) -> None:
        self.stk_factor_extract = StkFactorExtract()
        self.stk_factor_load = StkFactorLoad()

    def pull_stk_factor_by_date(self, *, trade_date: str) -> int:
        df = self.stk_factor_extract.pull_stk_factor_by_date(trade_date=trade_date)
        return self.stk_factor_load.load_stk_factor(df)

    def pull_stk_factor_by_ts_code(
        self,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> int:
        df = self.stk_factor_extract.pull_stk_factor_by_ts_code(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )
        return self.stk_factor_load.load_stk_factor(df)
