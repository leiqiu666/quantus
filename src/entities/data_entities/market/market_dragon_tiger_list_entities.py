"""龙虎榜每日交易明细（Tushare top_list）。"""

from sqlalchemy import Column, Integer, Float, String, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TopListEntities(Base):
    __tablename__ = "market_dragon_tiger_list"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(String(8), comment="交易日期")
    ts_code = Column(String(20), comment="TS 代码")
    name = Column(String(40), comment="名称")
    close = Column(Float, comment="收盘价")
    pct_change = Column(Float, comment="涨跌幅")
    turnover_rate = Column(Float, comment="换手率")
    amount = Column(Float, comment="总成交额")
    l_sell = Column(Float, comment="龙虎榜卖出额")
    l_buy = Column(Float, comment="龙虎榜买入额")
    l_amount = Column(Float, comment="龙虎榜成交额")
    net_amount = Column(Float, comment="龙虎榜净买入额")
    net_rate = Column(Float, comment="龙虎榜净买额占比")
    amount_rate = Column(Float, comment="龙虎榜成交额占比")
    float_value = Column(Float, comment="流通市值")
    reason = Column(String(200), comment="上榜原因")

    __table_args__ = (
        Index("idx_dt_list_trade_date", "trade_date"),
        Index("idx_dt_list_unique", "ts_code", "trade_date", unique=True),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(TopListEntities)
