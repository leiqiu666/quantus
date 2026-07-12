"""申万行业成分构成 entities"""

from sqlalchemy import Column, Index, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class IndexMemberAllEntities(Base):
    __tablename__ = "index_member_all"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    l1_code = Column(String(20), comment="一级行业代码")
    l1_name = Column(String(100), comment="一级行业名称")
    l2_code = Column(String(20), comment="二级行业代码")
    l2_name = Column(String(100), comment="二级行业名称")
    l3_code = Column(String(20), comment="三级行业代码")
    l3_name = Column(String(100), comment="三级行业名称")
    ts_code = Column(String(20), comment="成分股票代码")
    name = Column(String(100), comment="成分股票名称")
    in_date = Column(String(8), comment="纳入日期")
    out_date = Column(String(8), comment="剔除日期")
    is_new = Column(String(4), comment="是否最新")

    __table_args__ = (
        Index(
            "idx_index_member_all_unique",
            "ts_code",
            "l1_code",
            "l2_code",
            "l3_code",
            "in_date",
            unique=True,
        ),
        Index("idx_index_member_all_ts_code", "ts_code"),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(IndexMemberAllEntities)
