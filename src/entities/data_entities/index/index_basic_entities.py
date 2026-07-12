"""指数基本信息 entities"""

from sqlalchemy import Column, Float, Index, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class IndexBasicEntities(Base):
    __tablename__ = "index_basic"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    ts_code = Column(String(20), comment="TS代码")
    name = Column(String(100), comment="简称")
    fullname = Column(String(200), comment="指数全称")
    market = Column(String(20), comment="市场")
    publisher = Column(String(100), comment="发布方")
    index_type = Column(String(50), comment="指数风格")
    category = Column(String(50), comment="指数类别")
    base_date = Column(String(8), comment="基期")
    base_point = Column(Float, comment="基点")
    list_date = Column(String(8), comment="发布日期")
    weight_rule = Column(String(100), comment="加权方式")
    desc = Column(Text, comment="描述")
    exp_date = Column(String(8), comment="终止日期")

    __table_args__ = (
        Index("idx_index_basic_unique", "ts_code", unique=True),
        Index("idx_index_basic_market", "market"),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(IndexBasicEntities)
