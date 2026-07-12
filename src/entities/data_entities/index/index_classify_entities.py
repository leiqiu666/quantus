"""申万行业分类 entities"""

from sqlalchemy import Column, Index, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class IndexClassifyEntities(Base):
    __tablename__ = "index_classify"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    index_code = Column(String(20), comment="指数代码")
    industry_name = Column(String(100), comment="行业名称")
    level = Column(String(4), comment="行业层级")
    industry_code = Column(String(20), comment="行业代码")
    src = Column(String(20), comment="分类来源")
    is_pub = Column(String(4), comment="是否发布")
    parent_code = Column(String(20), comment="父级代码")

    __table_args__ = (
        Index(
            "idx_index_classify_unique",
            "index_code",
            "level",
            "src",
            unique=True,
        ),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(IndexClassifyEntities)
