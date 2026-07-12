"""指数日线行情 entities"""

from sqlalchemy import Column, Float, Index, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class IndexDailyEntities(Base):
    __tablename__ = "index_daily"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    ts_code = Column(String(20), comment="TS指数代码")
    trade_date = Column(String(8), comment="交易日")
    close = Column(Float, comment="收盘点位")
    open = Column(Float, comment="开盘点位")
    high = Column(Float, comment="最高点位")
    low = Column(Float, comment="最低点位")
    pre_close = Column(Float, comment="昨日收盘点")
    change = Column(Float, comment="涨跌点")
    pct_chg = Column(Float, comment="涨跌幅")
    vol = Column(Float, comment="成交量")
    amount = Column(Float, comment="成交额")

    __table_args__ = (
        Index("idx_index_daily_trade_date", "trade_date"),
        Index("idx_index_daily_unique", "ts_code", "trade_date", unique=True),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(IndexDailyEntities)
