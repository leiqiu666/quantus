"""业绩预告 Workflow。"""

from src.etl.extract.financial.financial_forecast_extract import ForecastExtract
from src.etl.load.financial.financial_forecast_load import ForecastLoad


class ForecastWorkflow:
    def __init__(self):
        self.extract = ForecastExtract()
        self.load = ForecastLoad()

    def pull_forecast_by_period(self, period: str) -> int:
        df = self.extract.pull_forecast_vip_by_period(period)
        return self.load.load_forecast(df)
