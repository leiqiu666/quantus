"""选股域：按历史时点筛选可投资股票。"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import or_

from src.common.database import Database
from src.entities.data_entities.stock.stock_list_entities import StockListEntities
from src.entities.data_entities.stock.stock_suspend_entities import SuspendEntities
from src.service.stock.stock_list_service import StockListService


def _norm_ymd(value: object) -> str:
    if value is None:
        return ""
    digits = "".join(c for c in str(value).strip() if c.isdigit())
    return digits[:8] if len(digits) >= 8 else ""


def _ymd_add_days(ymd: str, days: int) -> str:
    d = datetime.strptime(ymd, "%Y%m%d").date()
    return (d + timedelta(days=days)).strftime("%Y%m%d")


class UniverseDataset:
    def __init__(self) -> None:
        self._stock_list = StockListService()
        self._db = Database()

    def all_a(
        self,
        trade_date: str,
        *,
        exclude_st: bool = True,
        min_list_days: int = 60,
        exclude_suspended: bool = True,
    ) -> list[str]:
        """
        该日可投资 A 股：
        - list_date <= trade_date < delist_date（或 delist 空）
        - 可选排除名称含 ST
        - 上市不足 min_list_days 排除
        - 可选排除全天停牌（suspend_type=S 且 suspend_timing 空）
        """
        td = (trade_date or "").strip()
        if not td or len(td) != 8:
            return []

        stocks = self._stock_list.get_stock_list(period=td)
        min_list_date = _ymd_add_days(td, -max(min_list_days, 0)) if min_list_days > 0 else ""

        codes: list[str] = []
        for s in stocks:
            code = (getattr(s, "ts_code", None) or "").strip()
            if not code:
                continue
            name = (getattr(s, "name", None) or "") or ""
            if exclude_st and "ST" in name.upper():
                continue
            list_date = _norm_ymd(getattr(s, "list_date", None))
            if min_list_days > 0 and list_date and list_date > min_list_date:
                continue
            codes.append(code)

        if exclude_suspended and codes:
            suspended = self._full_day_suspended_codes(td, codes)
            codes = [c for c in codes if c not in suspended]

        return codes

    def _full_day_suspended_codes(self, trade_date: str, codes: list[str]) -> set[str]:
        if not codes:
            return set()
        session = self._db.get_session()
        try:
            # 分批避免 IN 过长
            out: set[str] = set()
            chunk = 2000
            for i in range(0, len(codes), chunk):
                part = codes[i : i + chunk]
                rows = (
                    session.query(SuspendEntities.ts_code)
                    .filter(SuspendEntities.trade_date == trade_date)
                    .filter(SuspendEntities.ts_code.in_(part))
                    .filter(SuspendEntities.suspend_type == "S")
                    .filter(
                        or_(
                            SuspendEntities.suspend_timing.is_(None),
                            SuspendEntities.suspend_timing == "",
                        )
                    )
                    .all()
                )
                out.update(str(r[0]).strip() for r in rows if r[0])
            return out
        finally:
            session.close()

    def index_members(self, index_code: str, trade_date: str) -> list[str]:
        raise NotImplementedError("index_members 待接 index_weight，Phase 2 后置")
