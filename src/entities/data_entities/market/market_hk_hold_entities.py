"""沪深港股通持股明细 entities"""

from sqlalchemy import Column, Integer, String, Float, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class HkHoldEntities(Base):
    __tablename__ = "market_hk_hold"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    code = Column(String(20), comment="原始代码")
    trade_date = Column(String(8), comment="交易日期")
    ts_code = Column(String(20), comment="TS股票代码")
    name = Column(String(50), comment="股票名称")
    vol = Column(Integer, comment="持股数量(股)")
    ratio = Column(Float, comment="持股占比(%)")
    exchange = Column(String(8), comment="交易所类型(SH/SZ/HK)")

    __table_args__ = (
        Index("idx_hk_hold_trade_date", "trade_date"),
        Index("idx_hk_hold_unique", "trade_date", "ts_code", "exchange", unique=True),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(HkHoldEntities)
