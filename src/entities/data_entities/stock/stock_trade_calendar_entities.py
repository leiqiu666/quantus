"""交易日历实体（Tushare trade_cal）。"""

from sqlalchemy import Column, Integer, String, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TradeCalEntities(Base):
    __tablename__ = "stock_trade_calendar"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    exchange = Column(String(10), comment="交易所 SSE/SZSE/CFFEX/SHFE/CZCE/DCE/INE")
    cal_date = Column(String(8), comment="日历日期 YYYYMMDD")
    is_open = Column(String(1), comment="是否交易 0休市 1交易")
    pretrade_date = Column(String(8), comment="上一个交易日 YYYYMMDD")

    __table_args__ = (
        Index("idx_trade_cal_unique", "exchange", "cal_date", unique=True),
        Index("idx_trade_cal_exchange_open", "exchange", "is_open", "cal_date"),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(TradeCalEntities)
