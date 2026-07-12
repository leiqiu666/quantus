"""Kline daily entities"""

from sqlalchemy import Column, Integer, String, Float, Index
from sqlalchemy.orm import declarative_base
from src.common.setting import settings

Base = declarative_base()

class KlineDailyEntities(Base):
    __tablename__ = "kline_daily"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    ts_code = Column(String(20),comment="股票代码")
    trade_date = Column(String(8),comment="交易日期")
    open = Column(Float,comment="开盘价")
    high = Column(Float,comment="最高价")
    low = Column(Float,comment="最低价")
    close = Column(Float,comment="收盘价")
    pre_close = Column(Float,comment="前收盘价")
    change = Column(Float,comment="涨跌额")
    pct_chg = Column(Float,comment="涨跌幅")
    vol = Column(Float,comment="成交量")
    amount = Column(Float,comment="成交额")
    adj_factor = Column(Float, comment="复权因子")
    up_limit = Column(Float, comment="涨停价")
    down_limit = Column(Float, comment="跌停价")

    __table_args__ = (
        Index('idx_kline_daily_trade_date', 'trade_date'),
        Index('idx_kline_daily_unique', 'ts_code', 'trade_date', unique=True),
    )

if __name__ == "__main__":
    from src.common.database import sync_table
    sync_table(KlineDailyEntities)