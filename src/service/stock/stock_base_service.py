from src.common.database import Database
from src.entities.data_entities.stock.stock_list_entities import StockListEntities


class StockBaseService:
    def __init__(self):
        self.db = Database()

    def get_all_stock_list_a(self, *, verbose: bool = False):
        """获取所有 A 股股票列表（exchange 为 SSE/SZSE/BSE）。"""
        stock_list_df = self.db.get_all(StockListEntities, exchange=["SSE", "SZSE", "BSE"])
        if verbose:
            print(f"[信息] 获取到 {len(stock_list_df)} 条股票列表数据")
        return stock_list_df


if __name__ == "__main__":
    stock_base_service = StockBaseService()
    stock_base_service.get_all_stock_list_a()
