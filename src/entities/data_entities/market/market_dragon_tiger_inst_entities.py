"""龙虎榜机构明细（Tushare top_inst）。"""

from sqlalchemy import Column, Integer, Float, String, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TopInstEntities(Base):
    __tablename__ = "market_dragon_tiger_inst"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(String(8), comment="交易日期")
    ts_code = Column(String(20), comment="TS 代码")
    exalter = Column(String(256), comment="营业部名称")
    side = Column(String(2), comment="买卖类型 0=买入 1=卖出")
    buy = Column(Float, comment="买入额")
    buy_rate = Column(Float, comment="买入占比")
    sell = Column(Float, comment="卖出额")
    sell_rate = Column(Float, comment="卖出占比")
    net_buy = Column(Float, comment="净买入额")
    reason = Column(String(256), comment="上榜理由")

    __table_args__ = (
        Index("idx_dt_inst_trade_date", "trade_date"),
        Index("idx_dt_inst_unique", "ts_code", "trade_date", "exalter", "side", unique=True),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(TopInstEntities)
