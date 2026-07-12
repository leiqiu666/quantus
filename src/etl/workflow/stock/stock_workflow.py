from src.etl.extract.stock.stock_extract import StockExtract
from src.etl.load.stock.stock_load import StockLoad


class StockWorkflow:
    def __init__(self):
        self.stock_extract = StockExtract()
        self.stock_load = StockLoad()

    def pull_stock_list_a(self):
        """Tushare stock_basic：L/D/P/G 四态分别拉取、合并后 upsert 到 stock_list。"""
        stock_list = self.stock_extract.pull_stock_list_a_all_statuses()
        saved_count = self.stock_load.load_stock(stock_list)
        return saved_count


if __name__ == "__main__":
    stock_workflow = StockWorkflow()
    stock_workflow.pull_stock_list_a()
