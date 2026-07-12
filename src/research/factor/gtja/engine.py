"""国泰 191 计算引擎：共享面板 + 受控公式求值。"""

from __future__ import annotations

import math
import os
import re
from pathlib import Path

import polars as pl

from src.common.setting import settings
from src.research.dataset.kline import KlineDataset
from src.research.factor.gtja.catalog import GtjaAlphaSpec, list_computable_alphas
from src.research.factor.gtja.ops import OpsContext
from src.research.factor.gtja.parallel import (
    panel_temp_path,
    resolve_parallelism,
    run_alpha_shards,
)
from src.research.factor.load import FactorParquetLoad

BENCHMARK_CODE = "000300.SH"
LOOKBACK_DAYS = 260


def _convert_ternary(expr: str) -> str:
    """把 a?b:c 转为 WHERE(a,b,c)，从右向左处理嵌套（Series 安全）。"""
    s = expr
    for _ in range(64):
        q = s.rfind("?")
        if q < 0:
            break
        depth = 0
        colon = -1
        for i in range(q + 1, len(s)):
            ch = s[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == ":" and depth == 0:
                colon = i
                break
        if colon < 0:
            break
        depth = 0
        start = 0
        for i in range(q - 1, -1, -1):
            ch = s[i]
            if ch == ")":
                depth += 1
            elif ch == "(":
                depth -= 1
                if depth < 0:
                    start = i + 1
                    break
            elif ch == "," and depth == 0:
                start = i + 1
                break
        else:
            start = 0
        depth = 0
        end = len(s)
        for i in range(colon + 1, len(s)):
            ch = s[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    end = i
                    break
                depth -= 1
            elif ch == "," and depth == 0:
                end = i
                break
        cond = s[start:q].strip()
        true_v = s[q + 1 : colon].strip()
        false_v = s[colon + 1 : end].strip()
        repl = f"WHERE({cond},{true_v},{false_v})"
        s = s[:start] + repl + s[end:]
    return s


def _infix_logic_to_func(expr: str) -> str:
    """把 and/or 中缀转为 AND()/OR()，避免 Series 位运算优先级问题。"""
    s = expr
    for op_word, func in ((" or ", "OR"), (" and ", "AND")):
        for _ in range(256):
            low = s.lower()
            idx = low.find(op_word)
            if idx < 0:
                break
            depth = 0
            left_start = 0
            for i in range(idx - 1, -1, -1):
                ch = s[i]
                if ch == ")":
                    depth += 1
                elif ch == "(":
                    depth -= 1
                    if depth < 0:
                        left_start = i + 1
                        break
                elif ch == "," and depth == 0:
                    left_start = i + 1
                    break
            else:
                left_start = 0
            depth = 0
            right_end = len(s)
            start_r = idx + len(op_word)
            for i in range(start_r, len(s)):
                ch = s[i]
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    if depth == 0:
                        right_end = i
                        break
                    depth -= 1
                elif ch == "," and depth == 0:
                    right_end = i
                    break
            left = s[left_start:idx].strip()
            right = s[start_r:right_end].strip()
            repl = f"{func}({left},{right})"
            s = s[:left_start] + repl + s[right_end:]
    return s


def _prep_formula(formula: str) -> str:
    s = formula
    s = re.sub(r"STD\(([A-Za-z_]+):(\d+)\)", r"STD(\1,\2)", s)
    s = re.sub(r"DELAY\(([A-Za-z_]+)\)", r"DELAY(\1,1)", s)
    s = _convert_ternary(s)
    # 比较等号（排除 == <= >= !=）
    s = re.sub(r"(?<![<>=!])=(?!=)", "==", s)
    s = _infix_logic_to_func(s)
    return s


def _where(cond, true_v, false_v):
    if isinstance(cond, pl.Series):
        c = cond if cond.dtype == pl.Boolean else (cond != 0)
    else:
        c = bool(cond)
        if not isinstance(true_v, pl.Series) and not isinstance(false_v, pl.Series):
            return true_v if c else false_v
        ref = true_v if isinstance(true_v, pl.Series) else false_v
        c = pl.Series([c] * ref.len())
    n = c.len() if isinstance(c, pl.Series) else 1
    if isinstance(true_v, pl.Series):
        tv = true_v.cast(pl.Float64)
        n = tv.len()
    else:
        tv = pl.Series([float(true_v)] * n)
    if isinstance(false_v, pl.Series):
        fv = false_v.cast(pl.Float64)
        n = fv.len()
    else:
        fv = pl.Series([float(false_v)] * n)
    if not isinstance(c, pl.Series):
        c = pl.Series([bool(c)] * n)
    if c.dtype != pl.Boolean:
        c = c != 0
    return (
        pl.DataFrame({"c": c, "t": tv, "f": fv})
        .select(pl.when(pl.col("c")).then(pl.col("t")).otherwise(pl.col("f")))
        .to_series()
    )


def _series_and(a, b):
    def _b(x, n):
        if isinstance(x, pl.Series):
            return x if x.dtype == pl.Boolean else (x != 0)
        return pl.Series([bool(x)] * n)

    n = a.len() if isinstance(a, pl.Series) else (b.len() if isinstance(b, pl.Series) else 1)
    return (_b(a, n) & _b(b, n)).cast(pl.Float64)


def _series_or(a, b):
    def _b(x, n):
        if isinstance(x, pl.Series):
            return x if x.dtype == pl.Boolean else (x != 0)
        return pl.Series([bool(x)] * n)

    n = a.len() if isinstance(a, pl.Series) else (b.len() if isinstance(b, pl.Series) else 1)
    return (_b(a, n) | _b(b, n)).cast(pl.Float64)

class Gtja191Engine:
    def __init__(
        self,
        warehouse_root: str | None = None,
        benchmark_code: str = BENCHMARK_CODE,
    ) -> None:
        self._root = Path(warehouse_root or settings.warehouse_root)
        self._kline = KlineDataset(str(self._root))
        self._load = FactorParquetLoad(str(self._root))
        self._benchmark_code = benchmark_code

    def _load_panel(self, year_month: str) -> pl.DataFrame:
        lf = self._kline.read_month_with_window(year_month, LOOKBACK_DAYS)
        df = (
            lf.select(
                "ts_code",
                "trade_date",
                "open_adj",
                "high_adj",
                "low_adj",
                "close_adj",
                "vol",
                "amount",
            )
            .sort("ts_code", "trade_date")
            .collect()
        )
        # VWAP
        df = df.with_columns(
            pl.when(pl.col("vol") > 0)
            .then(pl.col("amount") * 10.0 / pl.col("vol"))
            .otherwise(None)
            .alias("VWAP"),
            (
                pl.col("close_adj") / pl.col("close_adj").shift(1).over("ts_code") - 1.0
            ).alias("RET"),
        )
        # DTM / DBM / HD / LD / TR（简化国泰定义）
        df = df.with_columns(
            pl.col("open_adj").shift(1).over("ts_code").alias("_o1"),
            pl.col("high_adj").shift(1).over("ts_code").alias("_h1"),
            pl.col("low_adj").shift(1).over("ts_code").alias("_l1"),
            pl.col("close_adj").shift(1).over("ts_code").alias("_c1"),
        )
        df = df.with_columns(
            pl.when(pl.col("open_adj") <= pl.col("_o1"))
            .then(0.0)
            .otherwise(
                pl.max_horizontal(
                    pl.col("high_adj") - pl.col("open_adj"),
                    pl.col("open_adj") - pl.col("_o1"),
                )
            )
            .alias("DTM"),
            pl.when(pl.col("open_adj") >= pl.col("_o1"))
            .then(0.0)
            .otherwise(
                pl.max_horizontal(
                    pl.col("open_adj") - pl.col("low_adj"),
                    pl.col("open_adj") - pl.col("_o1"),
                )
            )
            .alias("DBM"),
            (pl.col("_h1") - pl.col("high_adj")).alias("_hd_raw"),
            (pl.col("_l1") - pl.col("low_adj")).alias("_ld_raw"),
        )
        df = df.with_columns(
            pl.when(pl.col("_hd_raw") > 0)
            .then(pl.col("_hd_raw"))
            .otherwise(0.0)
            .alias("HD"),
            pl.when(pl.col("_ld_raw") > 0)
            .then(pl.col("_ld_raw"))
            .otherwise(0.0)
            .alias("LD"),
            pl.max_horizontal(
                pl.col("high_adj") - pl.col("low_adj"),
                (pl.col("high_adj") - pl.col("_c1")).abs(),
                (pl.col("low_adj") - pl.col("_c1")).abs(),
            ).alias("TR"),
        )
        # 基准：优先 Parquet，否则 PG index_daily
        bm_open = "BANCHMARKINDEXOPEN"
        bm_close = "BANCHMARKINDEXCLOSE"
        idx = self._load_benchmark()
        if idx is not None and not idx.is_empty():
            df = df.join(idx, on="trade_date", how="left")
        else:
            df = df.with_columns(
                pl.lit(None).cast(pl.Float64).alias(bm_open),
                pl.lit(None).cast(pl.Float64).alias(bm_close),
            )
        return df

    def _load_benchmark(self) -> pl.DataFrame | None:
        idx_path = self._root / "index_daily"
        if idx_path.exists():
            try:
                return (
                    pl.scan_parquet(str(idx_path / "**" / "*.parquet"))
                    .filter(pl.col("ts_code") == self._benchmark_code)
                    .select(
                        pl.col("trade_date"),
                        pl.col("open").alias("BANCHMARKINDEXOPEN"),
                        pl.col("close").alias("BANCHMARKINDEXCLOSE"),
                    )
                    .collect()
                )
            except Exception:
                pass
        try:
            from src.common.database import Database
            from src.entities.data_entities.index.index_daily_entities import (
                IndexDailyEntities,
            )

            session = Database().get_session()
            try:
                rows = (
                    session.query(
                        IndexDailyEntities.trade_date,
                        IndexDailyEntities.open,
                        IndexDailyEntities.close,
                    )
                    .filter(IndexDailyEntities.ts_code == self._benchmark_code)
                    .all()
                )
            finally:
                session.close()
            if not rows:
                return None
            return pl.DataFrame(
                {
                    "trade_date": [str(r[0]) for r in rows],
                    "BANCHMARKINDEXOPEN": [r[1] for r in rows],
                    "BANCHMARKINDEXCLOSE": [r[2] for r in rows],
                }
            )
        except Exception:
            return None

    def _eval_alpha(self, panel: pl.DataFrame, spec: GtjaAlphaSpec) -> pl.Series | None:
        ops = OpsContext(panel)
        env: dict = {
            "OPEN": panel["open_adj"],
            "HIGH": panel["high_adj"],
            "LOW": panel["low_adj"],
            "CLOSE": panel["close_adj"],
            "VOLUME": panel["vol"],
            "VOL": panel["vol"],
            "AMOUNT": panel["amount"],
            "VWAP": panel["VWAP"],
            "RET": panel["RET"],
            "DTM": panel["DTM"],
            "DBM": panel["DBM"],
            "HD": panel["HD"],
            "LD": panel["LD"],
            "TR": panel["TR"],
            "BANCHMARKINDEXOPEN": panel["BANCHMARKINDEXOPEN"],
            "BANCHMARKINDEXCLOSE": panel["BANCHMARKINDEXCLOSE"],
            "SELF": panel.get_column("SELF") if "SELF" in panel.columns else ops.const(0.0),
            # ops
            "DELAY": ops.DELAY,
            "DELTA": ops.DELTA,
            "SUM": ops.SUM,
            "MEAN": ops.MEAN,
            "STD": ops.STD,
            "SMA": ops.SMA,
            "SMEAN": ops.SMA,
            "WMA": ops.WMA,
            "TSMAX": ops.TSMAX,
            "TSMIN": ops.TSMIN,
            "MAX": ops.MAX,
            "MIN": ops.MIN,
            "ABS": ops.ABS,
            "SIGN": ops.SIGN,
            "LOG": ops.LOG,
            "RANK": ops.RANK,
            "TSRANK": ops.TSRANK,
            "CORR": ops.CORR,
            "COVIANCE": ops.COVIANCE,
            "COVARIANCE": ops.COVARIANCE,
            "COUNT": ops.COUNT,
            "SUMIF": ops.SUMIF,
            "HIGHDAY": ops.HIGHDAY,
            "LOWDAY": ops.LOWDAY,
            "DECAYLINEAR": ops.DECAYLINEAR,
            "SEQUENCE": ops.SEQUENCE,
            "REGBETA": ops.REGBETA,
            "PROD": ops.PROD,
            "SUMAC": ops.SUMAC,
            "FILTER": ops.FILTER,
            "WHERE": _where,
            "AND": _series_and,
            "OR": _series_or,
            "True": True,
            "False": False,
        }
        formula = _prep_formula(spec.formula_eval)
        # 替换比较运算符为 Series 安全形式较难；依赖 Polars Series 的 > 等
        try:
            val = eval(formula, {"__builtins__": {}}, env)  # noqa: S307
        except Exception:
            return None
        if isinstance(val, pl.Series):
            return val.cast(pl.Float64)
        if isinstance(val, (int, float)) and not (isinstance(val, float) and math.isnan(val)):
            return ops.const(float(val))
        if isinstance(val, bool):
            return ops.const(1.0 if val else 0.0)
        return None

    def _eval_and_write_specs(
        self,
        panel: pl.DataFrame,
        year_month: str,
        specs: list[GtjaAlphaSpec],
    ) -> tuple[dict[str, int], list[str]]:
        """对给定面板求值并写分区；供串行与 worker 复用。"""
        ym_start, ym_end = year_month + "01", year_month + "31"
        results: dict[str, int] = {}
        failed: list[str] = []
        for spec in specs:
            series = self._eval_alpha(panel, spec)
            if series is None or series.len() != panel.height:
                failed.append(spec.name)
                continue
            out = panel.select("ts_code", "trade_date").with_columns(
                series.alias("value")
            )
            out = out.filter(
                (pl.col("trade_date") >= ym_start) & (pl.col("trade_date") <= ym_end)
            ).drop_nulls("value")
            if out.is_empty():
                failed.append(spec.name)
                continue
            n = self._load.write_month_partition(out.to_arrow(), spec.name, year_month)
            results[spec.name] = n
            if spec.n == 143:
                panel = panel.with_columns(series.alias("SELF"))
        return results, failed

    def compute_month(
        self,
        year_month: str,
        alphas: list[GtjaAlphaSpec] | None = None,
        *,
        force: bool = False,
        workers: int | None = None,
    ) -> dict[str, int]:
        specs = alphas if alphas is not None else list_computable_alphas()
        if not specs:
            return {}

        to_run: list[GtjaAlphaSpec] = []
        for s in specs:
            if s.skip_compute:
                continue
            if not force and year_month in self._load.list_existing_months(s.name):
                continue
            to_run.append(s)
        if not to_run:
            return {}

        panel = self._load_panel(year_month)
        self_specs = [s for s in to_run if s.n == 143]
        parallel_specs = [s for s in to_run if s.n != 143]

        results: dict[str, int] = {}
        failed: list[str] = []

        n_par = len(parallel_specs)
        w, polars_threads = resolve_parallelism(n_par, workers)
        print(
            f"  [{year_month}] to_run={len(to_run)} parallel={n_par} "
            f"workers={w} polars_threads={polars_threads}"
        )

        if n_par == 0:
            pass
        elif w <= 1 or n_par <= 1:
            prev = os.environ.get("POLARS_MAX_THREADS")
            os.environ["POLARS_MAX_THREADS"] = str(polars_threads)
            try:
                r, f = self._eval_and_write_specs(panel, year_month, parallel_specs)
            finally:
                if prev is None:
                    os.environ.pop("POLARS_MAX_THREADS", None)
                else:
                    os.environ["POLARS_MAX_THREADS"] = prev
            results.update(r)
            failed.extend(f)
        else:
            tmp = panel_temp_path(self._root, year_month)
            try:
                panel.write_parquet(tmp)
                r, f = run_alpha_shards(
                    panel_path=str(tmp),
                    year_month=year_month,
                    alpha_ids=[s.n for s in parallel_specs],
                    warehouse_root=str(self._root),
                    workers=w,
                    polars_threads=polars_threads,
                )
                results.update(r)
                failed.extend(f)
            finally:
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass

        if self_specs:
            if "SELF" not in panel.columns:
                panel = panel.with_columns(pl.lit(0.0).alias("SELF"))
            r, f = self._eval_and_write_specs(panel, year_month, self_specs)
            results.update(r)
            failed.extend(f)

        if failed:
            print(
                f"  [{year_month}] 跳过/失败 {len(failed)} 个: {', '.join(failed[:12])}"
                + ("..." if len(failed) > 12 else "")
            )
        return results
