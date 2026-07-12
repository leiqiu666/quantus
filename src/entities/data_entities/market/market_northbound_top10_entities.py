"""沪深股通十大成交股 entities"""

from sqlalchemy import Column, Integer, String, Float, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class HsgtTop10Entities(Base):
    __tablename__ = "market_northbound_top10"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    trade_date = Column(String(8), comment="交易日期")
    ts_code = Column(String(20), comment="股票代码")
    name = Column(String(50), comment="股票名称")
    close = Column(Float, comment="收盘价")
    change = Column(Float, comment="涨跌额")
    rank = Column(Integer, comment="排名")
    market_type = Column(Integer, comment="市场类型(1=沪/3=深)")
    amount = Column(Float, comment="成交额(万元)")
    net_amount = Column(Float, comment="净成交额(万元)")
    buy = Column(Float, comment="买入额(万元)")
    sell = Column(Float, comment="卖出额(万元)")

    __table_args__ = (
        Index('idx_hsgt_top10_trade_date', 'trade_date'),
        Index('idx_hsgt_top10_unique', 'ts_code', 'trade_date', 'market_type', unique=True),
    )

if __name__ == "__main__":
    from src.common.database import sync_table
    sync_table(HsgtTop10Entities)
