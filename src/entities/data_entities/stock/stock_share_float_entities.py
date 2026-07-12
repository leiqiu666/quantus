"""限售股解禁（Tushare share_float）。"""

from sqlalchemy import Column, Float, Index, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class StockShareFloatEntities(Base):
    __tablename__ = "stock_share_float"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), comment="TS 代码")
    ann_date = Column(String(8), comment="公告日期")
    float_date = Column(String(8), comment="解禁日期")
    float_share = Column(Float, comment="流通股份（股）")
    float_ratio = Column(Float, comment="流通股份占总股本比率")
    holder_name = Column(String(200), comment="股东名称")
    share_type = Column(String(40), comment="股份类型")

    __table_args__ = (
        Index("idx_stock_share_float_float_date", "float_date"),
        Index("idx_stock_share_float_ts_code", "ts_code"),
        Index(
            "idx_stock_share_float_unique",
            "ts_code",
            "float_date",
            "holder_name",
            "share_type",
            unique=True,
        ),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(StockShareFloatEntities)
