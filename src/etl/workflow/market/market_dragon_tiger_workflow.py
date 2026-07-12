"""龙虎榜 单日工作流：拉 top_list + top_inst 并入库。"""

from __future__ import annotations

from src.etl.extract.market.market_dragon_tiger_extract import DragonTigerExtract
from src.etl.load.market.market_dragon_tiger_load import DragonTigerLoad


class DragonTigerWorkflow:
    def __init__(self) -> None:
        self.dragon_tiger_extract = DragonTigerExtract()
        self.dragon_tiger_load = DragonTigerLoad()

    def pull_dragon_tiger_by_date(self, trade_date: str) -> tuple[int, int]:
        list_df = self.dragon_tiger_extract.pull_top_list_by_date(trade_date)
        inst_df = self.dragon_tiger_extract.pull_top_inst_by_date(trade_date)

        list_count = self.dragon_tiger_load.load_top_list(list_df)
        inst_count = self.dragon_tiger_load.load_top_inst(inst_df)

        return list_count, inst_count
