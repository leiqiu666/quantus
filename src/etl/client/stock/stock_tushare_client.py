"""Tushare 股票列表 Client。"""

from src.common.tushare_client import TushareClient
from src.entities.client_entities.tushare_entities import tushare_entities
from src.etl.client.base import call_with_network_retry


class TushareStockClient:
    def __init__(self):
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts
        self.stock_basic_fields = tushare_entities.stock_basic

    def pull_stock_list_a(self, **kwargs):
        stock_list = call_with_network_retry(
            self.ts.stock_basic, fields=self.stock_basic_fields, **kwargs
        )
        return stock_list
