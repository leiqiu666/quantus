from __future__ import annotations

from typing import List

from src.entities.data_entities.stock.stock_list_entities import StockListEntities
from src.service.stock.stock_list_service import StockListService


class StockExtract:
    """从本库 service 读取股票列表（非 Tushare 等外部拉取）。"""

    def __init__(self) -> None:
        self._stock_list_service = StockListService()

    def get_stock_list(self, **filters: str | None) -> List[StockListEntities]:
        """
        调用 service 层 StockListService.get_stock_list 获取股票列表（ORM，已加载 stock_list 全列）。

        可选筛选键与 API / model 一致：period、exchange、symbol（代码→ts_code）、
        ts_code、cnspell、name、market、shenwan_*、zhengjian_*、concept、area、city、
        country、is_ggt、is_hs（支持 Y/N）等；未传或空串不参与过滤（period 也可用 \"0\" 表示不限）。

        Returns:
            StockListEntities 实例列表。
        """
        return self._stock_list_service.get_stock_list(**filters)
