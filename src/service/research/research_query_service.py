"""投研分析查询：因子截面 / 个股K线 / 行情快照。"""

from __future__ import annotations

from typing import Any

from src.common.setting import settings
from src.model.kline.factor_combo_model import FactorComboModel
from src.research.dataset.factor import FactorDataset
from src.research.dataset.kline import KlineDataset
from src.research.strategy.multi_factor import MultiFactorStrategy


def _quantiles(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"p10": None, "p50": None, "p90": None, "count": 0}
    s = sorted(values)
    n = len(s)

    def _q(p: float) -> float:
        idx = min(max(int(round((n - 1) * p)), 0), n - 1)
        return s[idx]

    return {"p10": _q(0.10), "p50": _q(0.50), "p90": _q(0.90), "count": n}


class ResearchQueryService:
    def __init__(self) -> None:
        self._factors = FactorDataset()
        self._kline = KlineDataset()
        self._combos = FactorComboModel()

    def factor_cs(
        self,
        *,
        trade_date: str,
        factor_name: str | None = None,
        combo_id: int | None = None,
    ) -> dict[str, Any]:
        td = (trade_date or "").strip()
        if not td:
            raise ValueError("trade_date 必填")

        label: str
        values_by_code: dict[str, float]

        if combo_id is not None:
            combo = self._combos.get(int(combo_id))
            if combo is None:
                raise ValueError(f"组合不存在: {combo_id}")
            items_raw = combo.items or []
            pairs: list[tuple[str, float]] = []
            for it in items_raw:
                fn = str((it or {}).get("factor_name") or "").strip()
                w = float((it or {}).get("weight") or 1.0)
                if fn:
                    pairs.append((fn, w))
            if len(pairs) < 2:
                raise ValueError("组合有效因子不足 2 个")
            strategy = MultiFactorStrategy(pairs, name=combo.name)
            factor_cs = self._factors.read_multi(strategy.factor_names, td)
            scored = strategy.compose_scores(factor_cs)
            values_by_code = {
                r["ts_code"]: float(r["value"])
                for r in scored.iter_rows(named=True)
                if r.get("value") is not None
            }
            label = combo.name
        else:
            fn = (factor_name or "").strip()
            if not fn:
                raise ValueError("需要 factor_name 或 combo_id")
            df = self._factors.read(fn, td, td).collect()
            values_by_code = {
                r["ts_code"]: float(r["value"])
                for r in df.iter_rows(named=True)
                if r.get("value") is not None
            }
            label = fn

        ranked = sorted(values_by_code.items(), key=lambda x: x[1], reverse=True)
        rows = [
            {"ts_code": code, "value": val, "rank": i + 1}
            for i, (code, val) in enumerate(ranked)
        ]
        return {
            "trade_date": td,
            "factor_name": label,
            "rows": rows,
            "quantiles": _quantiles([v for _, v in ranked]),
        }

    def stock_kline(
        self,
        *,
        ts_code: str,
        start: str,
        end: str,
        factor_name: str | None = None,
    ) -> dict[str, Any]:
        code = (ts_code or "").strip()
        start = (start or "").strip()
        end = (end or "").strip()
        if not code or not start or not end or start > end:
            raise ValueError("ts_code / start / end 无效")

        bars = self._load_bars(code, start, end)
        factor_series: list[dict[str, Any]] = []
        fn = (factor_name or "").strip()
        if fn:
            fdf = (
                self._factors.read(fn, start, end, ts_codes=[code])
                .collect()
                .sort("trade_date")
            )
            factor_series = [
                {"trade_date": r["trade_date"], "value": r["value"]}
                for r in fdf.iter_rows(named=True)
                if r.get("value") is not None
            ]
        return {
            "ts_code": code,
            "start": start,
            "end": end,
            "bars": bars,
            "factor": factor_series,
            "factor_name": fn or None,
        }

    def quote(self, ts_code: str) -> dict[str, Any]:
        code = (ts_code or "").strip()
        if not code:
            raise ValueError("ts_code 必填")

        if settings.tdx_quant_enabled:
            try:
                from src.api.services import tdx_quant_service

                if tdx_quant_service.is_ready():
                    data = tdx_quant_service.invoke(
                        "get_market_snapshot", {"stock_code": code}
                    )
                    parsed = self._parse_tdx_snapshot(code, data)
                    if parsed is not None:
                        return parsed
            except Exception as e:
                daily = self._daily_quote(code)
                daily["message"] = f"TDX 失败已降级日线：{e}"
                return daily

        return self._daily_quote(code)

    def _load_bars(self, ts_code: str, start: str, end: str) -> list[dict[str, Any]]:
        try:
            df = (
                self._kline.read_range(start, end, ts_codes=[ts_code])
                .select(
                    "trade_date",
                    "open",
                    "high",
                    "low",
                    "close",
                    "vol",
                    "amount",
                    "close_adj",
                )
                .collect()
                .sort("trade_date")
            )
            if not df.is_empty():
                return df.to_dicts()
        except Exception:
            pass
        return self._load_bars_pg(ts_code, start, end)

    def _load_bars_pg(self, ts_code: str, start: str, end: str) -> list[dict[str, Any]]:
        from src.common.database import Database
        from src.entities.data_entities.kline.kline_daily_entities import (
            KlineDailyEntities,
        )

        session = Database().get_session()
        try:
            rows = (
                session.query(KlineDailyEntities)
                .filter(
                    KlineDailyEntities.ts_code == ts_code,
                    KlineDailyEntities.trade_date >= start,
                    KlineDailyEntities.trade_date <= end,
                )
                .order_by(KlineDailyEntities.trade_date.asc())
                .all()
            )
        finally:
            session.close()
        out: list[dict[str, Any]] = []
        for r in rows:
            adj = getattr(r, "adj_factor", None) or 1.0
            close = r.close
            out.append(
                {
                    "trade_date": r.trade_date,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": close,
                    "vol": r.vol,
                    "amount": r.amount,
                    "close_adj": (close * adj) if close is not None else None,
                }
            )
        return out

    def _daily_quote(self, ts_code: str) -> dict[str, Any]:
        # 最近约一年日 K，取最后一根
        from datetime import datetime, timedelta

        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=400)).strftime("%Y%m%d")
        bars = self._load_bars(ts_code, start, end)
        if not bars:
            raise ValueError(f"无日 K: {ts_code}")
        last = bars[-1]
        prev = bars[-2] if len(bars) >= 2 else None
        close = last.get("close")
        pre_close = prev.get("close") if prev else None
        change_pct = None
        if close is not None and pre_close:
            change_pct = float(close) / float(pre_close) - 1.0
        return {
            "mode": "daily",
            "ts_code": ts_code,
            "trade_date": last.get("trade_date"),
            "price": close,
            "pre_close": pre_close,
            "change_pct": change_pct,
            "open": last.get("open"),
            "high": last.get("high"),
            "low": last.get("low"),
            "close": close,
            "vol": last.get("vol"),
            "message": "日线快照，非盘中实时",
        }

    @staticmethod
    def _parse_tdx_snapshot(ts_code: str, data: Any) -> dict[str, Any] | None:
        """尽量从 get_market_snapshot 返回结构抽出报价。"""
        row: dict[str, Any] | None = None
        if isinstance(data, dict):
            if ts_code in data and isinstance(data[ts_code], dict):
                row = data[ts_code]
            elif "data" in data and isinstance(data["data"], list) and data["data"]:
                first = data["data"][0]
                if isinstance(first, dict):
                    row = first
            else:
                # 单票可能直接是字段 dict
                if any(k in data for k in ("price", "now", "close", "last")):
                    row = data
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            row = data[0]
        if not row:
            return None

        def _num(*keys: str) -> float | None:
            for k in keys:
                v = row.get(k)
                if v is None:
                    continue
                try:
                    return float(v)
                except (TypeError, ValueError):
                    continue
            return None

        price = _num("price", "now", "last", "close")
        pre_close = _num("pre_close", "preClose", "yclose")
        change_pct = _num("change_pct", "pct_chg", "涨跌幅")
        if change_pct is None and price is not None and pre_close:
            change_pct = price / pre_close - 1.0
        return {
            "mode": "tdx",
            "ts_code": ts_code,
            "trade_date": str(row.get("trade_date") or row.get("date") or ""),
            "price": price,
            "pre_close": pre_close,
            "change_pct": change_pct,
            "open": _num("open"),
            "high": _num("high"),
            "low": _num("low"),
            "close": price,
            "vol": _num("vol", "volume"),
            "message": None,
        }
