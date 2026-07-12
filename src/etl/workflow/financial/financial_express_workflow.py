"""业绩快报 Workflow。"""

from src.etl.extract.financial.financial_express_extract import ExpressExtract
from src.etl.load.financial.financial_express_load import ExpressLoad


class ExpressWorkflow:
    def __init__(self):
        self.extract = ExpressExtract()
        self.load = ExpressLoad()

    def pull_express_by_period(self, period: str) -> int:
        df = self.extract.pull_express_vip_by_period(period)
        return self.load.load_express(df)
