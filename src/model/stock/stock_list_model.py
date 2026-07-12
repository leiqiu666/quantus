"""stock_list 表查询。"""

from __future__ import annotations

from datetime import date
from typing import Any, List

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from src.common.database import Database
from src.entities.data_entities.stock.stock_list_entities import StockListEntities

_ILIKE_FIELDS = (
    "ts_code",
    "cnspell",
    "name",
    "market",
    "shenwan_1",
    "shenwan_2",
    "shenwan_3",
    "zhengjian_1",
    "zhengjian_2",
    "concept",
    "area",
    "city",
    "country",
)
_EQ_FIELDS = ("is_ggt", "is_hs", "exchange")


def _norm_yyyymmdd(value: object) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) >= 8:
        return digits[:8]
    return None


def _normalize_hs_equity_flag(val: str) -> str:
    """is_hs / is_ggt：库内多为 1/0；兼容 API 传的 Y/N。"""
    v = val.strip().upper()
    if v == "Y":
        return "1"
    if v == "N":
        return "0"
    return val.strip()


def _escape_ilike(pattern: str) -> str:
    return (
        pattern.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _reference_date_from_period(val: str | None) -> str | None:
    """period：未填/空/'0' 不限制；'1' 表示截止今天在市的参考日（今天日期 YYYYMMDD）；否则解析为报告期 YYYYMMDD。"""
    if val is None:
        return None
    s = val.strip()
    if not s or s == "0":
        return None
    if s == "1":
        return date.today().strftime("%Y%m%d")
    return _norm_yyyymmdd(s)


def _apply_listing_period_filter(query: Query[Any], ref_date: str) -> Query[Any]:
    """
    报告期在市：list_date <= ref_date，且退市日为空或未在 ref_date 当日及之前（delist_date 为空或 > ref_date）。
    list_date/delist_date 按 YYYYMMDD 字串可比。
    """
    ld = StockListEntities.list_date
    dd = StockListEntities.delist_date
    return query.filter(
        ld.isnot(None),
        ld != "",
        ld <= ref_date,
        or_(dd.is_(None), dd == "", dd > ref_date),
    )


def _apply_ts_code_via_symbol(query: Query[Any], symbol_pat: str) -> Query[Any]:
    """symbol 请求参数语义为股票代码，对应列 ts_code（模糊匹配）。"""
    esc = _escape_ilike(symbol_pat.strip())
    return query.filter(
        StockListEntities.ts_code.ilike(f"%{esc}%", escape="\\")
    )


def _apply_search_filters(query: Query[Any], **kw: str | None) -> Query[Any]:
    # period 已在 search_stock_list 中单独处理并从 kw 中剔除
    # symbol → ts_code（与实体列 symbol 简称区分）
    sym = kw.get("symbol")
    if sym is not None and str(sym).strip() != "":
        query = _apply_ts_code_via_symbol(query, str(sym))

    for name in _ILIKE_FIELDS:
        val = kw.get(name)
        if val is None or val == "":
            continue
        col = getattr(StockListEntities, name)
        esc = _escape_ilike(val)
        query = query.filter(col.ilike(f"%{esc}%", escape="\\"))
    for name in _EQ_FIELDS:
        val = kw.get(name)
        if val is None or val == "":
            continue
        if name in ("is_hs", "is_ggt"):
            val = _normalize_hs_equity_flag(str(val))
        query = query.filter(getattr(StockListEntities, name) == val)
    return query


class StockListModel:
    def __init__(self) -> None:
        self.db = Database()

    def search_stock_list(self, **filters: str | None) -> List[StockListEntities]:
        """
        可选筛选：
        - period：报告期/ref；不传、空串或 \"0\" 不限制；“1” 表示截止今天在市的参考日；
          其它值解析为 YYYYMMDD，筛「在该日已上市且未退市」。
        - symbol：股票代码（模糊），映射列 ts_code。
        - exchange：交易所代码等值（如 BSE、SSE、SZSE）。
        - 其余见 _ILIKE_FIELDS / _EQ_FIELDS；文本类 ILIKE；is_ggt/is_hs 等值，兼容 Y/N。
        """
        session: Session = self.db.get_session()
        try:
            fw = dict(filters)
            period_raw = fw.pop("period", None)
            ref = (
                None
                if period_raw is None
                else _reference_date_from_period(str(period_raw).strip())
            )

            query = session.query(StockListEntities)
            if ref is not None:
                query = _apply_listing_period_filter(query, ref)
            query = _apply_search_filters(query, **fw)
            query = query.order_by(StockListEntities.ts_code)
            return query.all()
        finally:
            session.close()


if __name__ == "__main__":
    m = StockListModel()
    print(len(m.search_stock_list()))
