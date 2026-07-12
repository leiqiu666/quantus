"""大宗交易明细（Tushare block_trade）。"""

from sqlalchemy import Column, Integer, Float, String, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BlockTradeEntities(Base):
    __tablename__ = "market_block_trade"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), comment="TS 代码")
    trade_date = Column(String(8), comment="交易日期")
    price = Column(Float, comment="成交价")
    vol = Column(Float, comment="成交量（万股）")
    amount = Column(Float, comment="成交金额")
    buyer = Column(String(200), comment="买方营业部")
    seller = Column(String(200), comment="卖方营业部")

    __table_args__ = (
        Index("idx_block_trade_trade_date", "trade_date"),
        Index("idx_block_trade_ts_code", "ts_code"),
        Index("idx_block_trade_unique", "ts_code", "trade_date", "buyer", "seller", unique=True),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(BlockTradeEntities)
