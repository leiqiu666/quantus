"""回测 Runner：SSE / CLI 共用，写 warehouse + PG 索引。"""

from __future__ import annotations

import queue
import uuid
from datetime import datetime
from typing import Any

from src.model.kline.backtest_run_model import BacktestRunModel
from src.model.kline.factor_combo_model import FactorComboModel
from src.research.backtest.common.cost import CostModel
from src.research.backtest.crosssection.engine import CrossSectionEngine
from src.research.dataset.factor import FactorDataset
from src.research.strategy.multi_factor import MultiFactorStrategy
from src.research.strategy.single_factor import SingleFactorStrategy


def _months_overlap(factor_name: str, start: str, end: str, ds: FactorDataset) -> bool:
    months = ds.list_available_months(factor_name)
    if not months:
        return False
    s, e = start[:6], end[:6]
    return any(s <= m <= e for m in months)


class BacktestRunner:
    def __init__(self) -> None:
        self._runs = BacktestRunModel()
        self._combos = FactorComboModel()
        self._factors = FactorDataset()

    def run(
        self,
        *,
        start_date: str,
        end_date: str,
        backtest_mode: str = "single",
        factor_name: str | None = None,
        combo_id: int | None = None,
        groups: int = 10,
        rebalance: str = "monthly",
        commission_rate: float | None = None,
        stamp_duty_rate: float | None = None,
        slippage_rate: float | None = None,
        progress_queue: queue.Queue | None = None,
    ) -> dict[str, Any]:
        start = (start_date or "").strip()
        end = (end_date or "").strip()
        mode = (backtest_mode or "single").strip().lower()
        rebalance = (rebalance or "monthly").strip().lower()
        groups = max(int(groups or 10), 2)
        _cost_defaults = CostModel()
        cost_model = CostModel(
            commission_rate=(
                float(commission_rate)
                if commission_rate is not None
                else _cost_defaults.commission_rate
            ),
            stamp_duty_rate=(
                float(stamp_duty_rate)
                if stamp_duty_rate is not None
                else _cost_defaults.stamp_duty_rate
            ),
            slippage_rate=(
                float(slippage_rate)
                if slippage_rate is not None
                else _cost_defaults.slippage_rate
            ),
        )

        def _log(msg: str) -> None:
            print(msg)
            if progress_queue is not None:
                progress_queue.put({"log": msg})

        if not start or not end or start > end:
            raise ValueError(f"无效回测区间: {start}~{end}")
        if rebalance not in ("monthly", "weekly"):
            raise ValueError("rebalance 仅支持 monthly | weekly")

        combo_name: str | None = None
        strategy: Any
        label_factor: str | None = None

        if mode == "combo":
            if combo_id is None:
                raise ValueError("combo 模式需要 combo_id")
            combo = self._combos.get(int(combo_id))
            if combo is None:
                raise ValueError(f"组合不存在: {combo_id}")
            combo_name = combo.name
            items_raw = combo.items or []
            pairs: list[tuple[str, float]] = []
            missing: list[str] = []
            for it in items_raw:
                fn = str((it or {}).get("factor_name") or "").strip()
                w = float((it or {}).get("weight") or 1.0)
                if not fn:
                    continue
                if not _months_overlap(fn, start, end, self._factors):
                    missing.append(fn)
                pairs.append((fn, w))
            if len(pairs) < 2:
                raise ValueError("组合有效因子不足 2 个")
            if missing:
                raise ValueError(
                    "以下因子在区间内无 Parquet 覆盖: " + ", ".join(missing)
                )
            strategy = MultiFactorStrategy(pairs, n_groups=groups, name=combo_name)
            _log(f"多因子组合「{combo_name}」· {len(pairs)} 因子 · {start}~{end}")
        elif mode == "single":
            fn = (factor_name or "").strip()
            if not fn:
                raise ValueError("single 模式需要 factor_name")
            if not _months_overlap(fn, start, end, self._factors):
                raise ValueError(f"因子 {fn} 在区间 {start}~{end} 无 Parquet 覆盖")
            strategy = SingleFactorStrategy(fn, n_groups=groups)
            label_factor = fn
            _log(f"单因子 {fn} · {start}~{end}")
        else:
            raise ValueError("backtest_mode 仅支持 single | combo")

        meta = {
            "backtest_mode": mode,
            "factor_name": label_factor,
            "combo_id": int(combo_id) if combo_id is not None else None,
            "combo_name": combo_name,
            "start_date": start,
            "end_date": end,
            "rebalance": rebalance,
            "groups": groups,
            "cost": {
                "commission_rate": cost_model.commission_rate,
                "stamp_duty_rate": cost_model.stamp_duty_rate,
                "slippage_rate": cost_model.slippage_rate,
            },
        }

        if progress_queue is not None:
            progress_queue.put({"status": "running", "total": 1})

        try:
            result = CrossSectionEngine(
                strategy=strategy,
                cost_model=cost_model,
                rebalance_freq=rebalance,
                n_groups=groups,
            ).run(start, end)
            real_id = str(result.summary.get("run_id") or "")
            self._runs.save_success(
                {
                    **meta,
                    "run_id": real_id,
                    "summary": result.summary,
                    "output_dir": result.output_dir,
                }
            )
            msg = f"回测完成 run_id={real_id}"
            _log(msg)
            if progress_queue is not None:
                progress_queue.put(
                    {"index": 1, "total": 1, "period": real_id, "saved": 1}
                )
                progress_queue.put({"done": True, "saved": 1, "message": msg})
            return result.summary
        except Exception as e:
            fail_id = (
                datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
            )
            try:
                self._runs.save_failed({**meta, "run_id": fail_id}, str(e))
            except Exception:
                pass
            if progress_queue is not None:
                progress_queue.put({"error": str(e)})
            raise
