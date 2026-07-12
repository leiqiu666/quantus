"""盘前股本（Tushare stk_premarket）。"""

from sqlalchemy import Column, Float, Index, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class StockPremarketEntities(Base):
    __tablename__ = "stock_premarket"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(String(8), comment="交易日期")
    ts_code = Column(String(20), comment="TS 代码")
    total_share = Column(Float, comment="总股本（万股）")
    float_share = Column(Float, comment="流通股本（万股）")
    pre_close = Column(Float, comment="昨日收盘价")
    up_limit = Column(Float, comment="今日涨停价")
    down_limit = Column(Float, comment="今日跌停价")

    __table_args__ = (
        Index("idx_stock_premarket_trade_date", "trade_date"),
        Index("idx_stock_premarket_unique", "trade_date", "ts_code", unique=True),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(StockPremarketEntities)
