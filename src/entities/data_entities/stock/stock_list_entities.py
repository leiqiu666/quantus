"""Stock List data model."""

from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, create_engine, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from datetime import datetime
from src.common.setting import settings

# create base class (模块级别，可被其他模块导入使用)
Base = declarative_base()

class StockListEntities(Base):
    __tablename__ = "stock_list"
    id = Column(Integer, primary_key=True,autoincrement=True,comment="ID")
    ts_code = Column(String(20),comment="股票代码")
    symbol = Column(String(20),comment="股票简称")
    name = Column(String(20),comment="股票名称")
    fullname = Column(String(100),comment="全称")
    enname = Column(String(100),comment="英文名称")
    cnspell = Column(String(20),comment="拼音简称")
    market = Column(String(20),comment="市场类型(主板/中小板/创业板/科创板/港股通/北交所)")
    exchange = Column(String(20),comment="交易所代码")
    curr_type = Column(String(20),comment="交易货币")
    list_status = Column(String(20),comment="	上市状态 L上市 D退市 G过会未交易 P暂停上市")
    list_date = Column(String(20),comment="上市日期")
    delist_date = Column(String(20),comment="退市日期")
    # stock industry and concept information
    is_hs = Column(String(20),comment="是否沪深港通标的(1是/0否)")
    is_ggt = Column(String(20),comment="是否港股通标的(1是/0否)")
    shenwan_1 = Column(String(20),comment="申万一及行业代码")
    shenwan_2 = Column(String(20),comment="申万二及行业名称")
    shenwan_3 = Column(String(20),comment="申万三及行业代码")
    zhengjian_1 = Column(String(20),comment="证监会一级行业代码")
    zhengjian_2 = Column(String(20),comment="证监会二级行业名称")
    concept = Column(String(20),comment="概念代码")
    area = Column(String(20),comment="地区")
    city = Column(String(20),comment="城市")
    country = Column(String(20),comment="国家")
    # data update deadline 
    kline_day_ddl = Column(DateTime,comment="日线数据更新截止日期")
    kline_min_ddl = Column(DateTime,comment="分钟线数据更新截止日期")
    report_income_ddl = Column(DateTime,comment="财报数据更新截止日期")
    report_cashflow_ddl = Column(DateTime,comment="现金流量表数据更新截止日期")
    report_profit_ddl = Column(DateTime,comment="利润表数据更新截止日期")
    report_balance_ddl = Column(DateTime,comment="资产负债表数据更新截止日期")
    # ts_code，market， 增加索引
    # 注意：PostgreSQL 索引名是数据库全局唯一的，需加表名前缀
    __table_args__ = (
        Index('idx_stock_list_ts_code', 'ts_code'),
        Index('idx_stock_list_cnspell', 'cnspell'),
        Index('idx_stock_list_name', 'name'),
        Index('idx_stock_list_market', 'market'),
        Index('idx_stock_list_shenwan_1', 'shenwan_1'),
        Index('idx_stock_list_shenwan_2', 'shenwan_2'),
        Index('idx_stock_list_shenwan_3', 'shenwan_3'),
        Index('idx_stock_list_zhengjian_1', 'zhengjian_1'),
        Index('idx_stock_list_zhengjian_2', 'zhengjian_2'),
        Index('idx_stock_list_concept', 'concept'),
        Index('idx_stock_list_area', 'area'),
        Index('idx_stock_list_city', 'city'),
        Index('idx_stock_list_country', 'country'),
        Index('idx_stock_list_is_ggt', 'is_ggt'),
        Index('idx_stock_list_is_hs', 'is_hs'),
    )

if __name__ == "__main__":
    from src.common.database import sync_table
    
    # 使用通用函数同步表结构
    sync_table(StockListEntities, interactive=True)