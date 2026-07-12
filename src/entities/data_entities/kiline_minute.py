"""Kline daily entities"""

from sqlalchemy import Column, Integer, String, Float, Index
from sqlalchemy.orm import declarative_base
from src.common.setting import settings

Base = declarative_base()

class KlineMinuteEntities(Base):
    __tablename__ = "kline_minute"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    ts_code = Column(String(20),comment="股票代码")
    trade_time = Column(String(10),comment="交易时间")
    open = Column(Float,comment="开盘价")
    high = Column(Float,comment="最高价")
    low = Column(Float,comment="最低价")
    close = Column(Float,comment="收盘价")
    pre_close = Column(Float,comment="前收盘价")
    change = Column(Float,comment="涨跌额")
    pct_chg = Column(Float,comment="涨跌幅")
    vol = Column(Float,comment="成交量")
    amount = Column(Float,comment="成交额")

    __table_args__ = (
        Index('idx_kline_minute_ts_code', 'ts_code'),
        Index('idx_kline_minute_trade_time', 'trade_time'),
        Index('idx_kline_minute_open', 'open'),
        Index('idx_kline_minute_high', 'high'),
        Index('idx_kline_minute_low', 'low'),
        Index('idx_kline_minute_close', 'close'),
        Index('idx_kline_minute_pre_close', 'pre_close'),
        Index('idx_kline_minute_change', 'change'),
        Index('idx_kline_minute_pct_chg', 'pct_chg'),
        Index('idx_kline_minute_vol', 'vol'),
        Index('idx_kline_minute_amount', 'amount'),
        # 复合唯一索引：ts_code + trade_time
        Index('idx_kline_minute_unique', 'ts_code', 'trade_time', unique=True),
    )

if __name__ == "__main__":
    from src.common.database import sync_table
    sync_table(KlineMinuteEntities)