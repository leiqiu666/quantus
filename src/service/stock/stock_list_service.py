"""股票列表查询服务。"""

from __future__ import annotations

from typing import List

from src.entities.data_entities.stock.stock_list_entities import StockListEntities
from src.model.stock.stock_list_model import StockListModel


class StockListService:
    def __init__(self) -> None:
        self._model = StockListModel()

    def get_stock_list(
        self,
        *,
        period: str | None = None,
        market: str | None = None,
        exchange: str | None = None,
        name: str | None = None,
        symbol: str | None = None,
        is_hs: str | None = None,
        **filters: str | None,
    ) -> List[StockListEntities]:
        """
        可选条件与 model.search_stock_list 一致；以下为常用筛选项封装。

        Args:
            period: 报告期/参考日。不传或为 \"0\"/空表示不筛上市状态；\
                \"1\" 表示以今天为参考日筛选「当时在上市未退市」；\
                否则为 YYYYMMDD，筛在该日「已上市且未退市」（与 StockTransform.period_stock_count 规则一致；trade_date_stock_count 已整体排除退市股）。
            market: 上市板（主板、创业板等），列 market，模糊匹配。
            exchange: 交易所代码等值匹配（如 BSE、SSE、SZSE）。
            name: 股票名称，模糊匹配。
            symbol: 股票代码（语义对应列 ts_code，模糊）。
            is_hs: 是否沪港通/沪深港通标的；库内多为 1/0，亦可传 Y/N。
        """
        merged: dict[str, str | None] = dict(filters)
        explicit = (
            ("period", period),
            ("market", market),
            ("exchange", exchange),
            ("name", name),
            ("symbol", symbol),
            ("is_hs", is_hs),
        )
        for k, v in explicit:
            if v is not None:
                merged[k] = v
        return self._model.search_stock_list(**merged)


if __name__ == "__main__":
    s = StockListService()
    print(len(s.get_stock_list()))
