"""业绩快报 Extract。"""

from src.etl.client.financial.financial_express_tushare_client import TushareExpressClient
import pandas as pd


class ExpressExtract:
    def __init__(self):
        self.tushare_client = TushareExpressClient()

    def pull_express_vip_by_period(self, period: str) -> pd.DataFrame:
        return self.tushare_client.pull_express_vip_by_period(period)
