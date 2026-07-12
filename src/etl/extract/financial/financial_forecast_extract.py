"""业绩预告 Extract。"""

from src.etl.client.financial.financial_forecast_tushare_client import TushareForecastClient
import pandas as pd


class ForecastExtract:
    def __init__(self):
        self.tushare_client = TushareForecastClient()

    def pull_forecast_vip_by_period(self, period: str) -> pd.DataFrame:
        return self.tushare_client.pull_forecast_vip_by_period(period)
