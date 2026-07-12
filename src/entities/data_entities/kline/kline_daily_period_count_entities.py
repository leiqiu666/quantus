"""Kline daily period count entities"""

from sqlalchemy import Column, Integer, String, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class KlineDailyPeriodCountEntities(Base):
    __tablename__ = "kline_daily_period_count"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    trade_date = Column(String(8), comment="交易日期")
    period_stock_count = Column(Integer, comment="该日应在市股票数")
    kline_daily_count = Column(Integer, comment="日线该日记录数")
    kline_adj_factor_count = Column(Integer, comment="复权因子该日记录数")
    kline_stk_limit_count = Column(Integer, comment="涨跌停该日记录数")

    __table_args__ = (
        Index(
            "idx_kline_daily_period_count_trade_date",
            "trade_date",
            unique=True,
        ),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(KlineDailyPeriodCountEntities)
