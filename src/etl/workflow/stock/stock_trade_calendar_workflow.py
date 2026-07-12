from src.etl.extract.stock.stock_trade_calendar_extract import TradeCalExtract
from src.etl.load.stock.stock_trade_calendar_load import TradeCalLoad


class TradeCalWorkflow:
    def __init__(self) -> None:
        self.trade_cal_extract = TradeCalExtract()
        self.trade_cal_load = TradeCalLoad()

    def pull_trade_cal_range(
        self,
        *,
        exchange: str,
        start_date: str,
        end_date: str,
    ) -> int:
        df = self.trade_cal_extract.pull_trade_cal_range(
            exchange=exchange,
            start_date=start_date,
            end_date=end_date,
        )
        return self.trade_cal_load.load_trade_cal(df)
