"""Quantus 量化研究 CLI — 因子 / 回测 / 策略。"""

import typer
from typing import Callable

from src.etl.strategy.kline.kline_factor_compute_strategy import FactorComputeStrategy
from src.etl.strategy.kline.kline_factor_tushare_strategy import TushareFactorStrategy
from src.research.factor.sync import FactorSyncService

app = typer.Typer()

factor_cmd = typer.Typer()
app.add_typer(factor_cmd, name="factor", help="因子计算与管理")
tushare_factor_cmd = typer.Typer()
app.add_typer(tushare_factor_cmd, name="tushare-factor", help="Tushare 技术因子入库")
backtest_cmd = typer.Typer()
app.add_typer(backtest_cmd, name="backtest", help="截面回测")
gtja191_cmd = typer.Typer()
app.add_typer(gtja191_cmd, name="gtja191", help="国泰191因子")

_MENU_ROWS: list[tuple[str, str]] = [
    ("【因子】更新全量因子 Parquet计算+PG同步 (factor update-all)", "factor-update-all"),
    ("【因子】计算指定因子到Parquet (factor compute)", "factor-compute"),
    ("【因子】同步因子到PG热层 (factor sync-pg)", "factor-sync-pg"),
    ("【因子】列出已注册因子 (factor list)", "factor-list"),
    ("【因子】Tushare技术因子 by date 区间增量 (tushare-factor pull-by-date-range)", "tushare-factor-pull"),
    ("【因子】刷新因子元数据 (factor update-meta)", "factor-update-meta"),
    ("【因子】国泰191计算 (gtja191 compute)", "gtja191-compute"),
    ("【回测】单因子截面 (backtest run)", "backtest-run"),
]


def _run_interactive_menu() -> None:
    typer.echo("选择要执行的任务：")
    for idx, (label, _) in enumerate(_MENU_ROWS, start=1):
        typer.echo(f"  {idx:>2}. {label}")
    quit_idx = len(_MENU_ROWS) + 1
    typer.echo(f"  {quit_idx:>2}. 退出")

    try:
        raw = input("请输入序号（回车=退出）: ").strip()
    except EOFError:
        return

    if raw == "" or raw == str(quit_idx):
        return
    if not raw.isdigit():
        typer.echo(f"[错误] 无效输入: {raw!r}", err=True)
        raise typer.Exit(1)

    choice = int(raw)
    if not (1 <= choice <= len(_MENU_ROWS)):
        typer.echo(f"[错误] 序号超出范围: {choice}", err=True)
        raise typer.Exit(1)

    _, key = _MENU_ROWS[choice - 1]
    handler = _MENU_HANDLERS.get(key)
    if handler is None:
        typer.echo(f"[错误] 未注册菜单项: {key}", err=True)
        raise typer.Exit(1)
    handler()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is not None:
        return
    _run_interactive_menu()
    raise typer.Exit(0)


# ─── factor 命令 ───


def _run_factor_update_all(force: bool = False) -> None:
    FactorComputeStrategy().compute_all_factors(force=force)
    FactorSyncService().sync_to_pg(days=60)


@factor_cmd.command("update-all")
def factor_update_all(
    force: bool = typer.Option(False, "--force", help="强制重算已有 Parquet 分区"),
) -> None:
    """计算全部因子 Parquet + 同步到 PG 热层（推荐日常使用）。"""
    _run_factor_update_all(force)


def _run_factor_compute(
    name: str | None = None,
    start_month: str | None = None,
    end_month: str | None = None,
    force: bool = False,
) -> None:
    if name is None:
        try:
            name = input("请输入因子名称: ").strip()
        except EOFError:
            return
        if not name:
            return
    FactorComputeStrategy().compute_factor(name, start_month, end_month, force)


@factor_cmd.command("compute")
def factor_compute(
    name: str = typer.Option(..., "--name", help="因子名称，如 momentum_20d"),
    start_month: str | None = typer.Option(None, "--start-month", help="起始月 YYYYMM"),
    end_month: str | None = typer.Option(None, "--end-month", help="结束月 YYYYMM"),
    force: bool = typer.Option(False, "--force", help="强制重算已有分区"),
) -> None:
    """计算指定因子到 Parquet（增量，跳过已有分区；--force 强制重算）。"""
    _run_factor_compute(name, start_month, end_month, force)


def _run_factor_sync_pg(days: int = 60, source: str = "all") -> None:
    FactorSyncService().sync_to_pg(days=days, source=source)


@factor_cmd.command("sync-pg")
def factor_sync_pg(
    days: int = typer.Option(60, "--days", help="保留最近 N 个交易日，默认 60"),
    source: str = typer.Option(
        "all",
        "--source",
        help="同步范围：self（自研）/ tushare / all",
    ),
) -> None:
    """同步因子值从 Parquet 到 PG 热层（不重新计算）。"""
    _run_factor_sync_pg(days, source)


def _run_factor_list() -> None:
    from src.research.factor.registry import FactorRegistry

    FactorRegistry.auto_discover()
    metas = FactorRegistry.list_all()
    if not metas:
        typer.echo("暂无已注册因子")
        return
    typer.echo(f"已注册因子 ({len(metas)} 个)：")
    typer.echo(f"  {'名称':<25s} {'类别':<15s} {'频率':<10s} {'窗口':<6s} {'版本'}")
    for m in metas:
        typer.echo(
            f"  {m.name:<25s} {m.category:<15s} {m.frequency:<10s} "
            f"{m.window_size:<6d} {m.version}"
        )


@factor_cmd.command("list")
def factor_list() -> None:
    """列出所有已注册因子。"""
    _run_factor_list()


# ─── tushare-factor 命令 ───


def _run_tushare_factor_pull(
    start_date: str | None = None, end_date: str | None = None,
) -> None:
    TushareFactorStrategy().pull_by_date_range(start_date, end_date)


@tushare_factor_cmd.command("pull-by-date-range")
def tushare_factor_pull(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """按交易日区间增量拉取 Tushare 技术面因子到 Parquet（30/min 限流）。"""
    _run_tushare_factor_pull(start_date, end_date)


def _run_factor_update_meta() -> None:
    from src.research.factor.meta_service import FactorMetaService
    FactorMetaService().update_meta()


@factor_cmd.command("update-meta")
def factor_update_meta() -> None:
    """扫描 Parquet + 注册表，刷新 PG factor_meta 元数据（因子列表、覆盖区间、来源）。"""
    _run_factor_update_meta()


# ─── backtest 命令 ───


def _run_backtest(
    strategy: str = "single_factor",
    factor: str | None = None,
    start: str | None = None,
    end: str | None = None,
    rebalance: str = "monthly",
    groups: int = 10,
) -> None:
    if factor is None:
        try:
            factor = input("因子名称 (默认 momentum_20d): ").strip() or "momentum_20d"
        except EOFError:
            return
    if start is None:
        try:
            start = input("起始日 YYYYMMDD: ").strip()
        except EOFError:
            return
    if end is None:
        try:
            end = input("结束日 YYYYMMDD: ").strip()
        except EOFError:
            return
    if not start or not end:
        typer.echo("[错误] 需要 --start / --end", err=True)
        raise typer.Exit(1)

    if strategy != "single_factor":
        typer.echo(f"[错误] 暂仅支持 strategy=single_factor，收到: {strategy}", err=True)
        raise typer.Exit(1)

    from src.research.backtest.crosssection.engine import CrossSectionEngine
    from src.research.strategy.single_factor import SingleFactorStrategy

    eng = CrossSectionEngine(
        strategy=SingleFactorStrategy(factor, n_groups=groups),
        rebalance_freq=rebalance,
        n_groups=groups,
    )
    eng.run(start, end)


@backtest_cmd.command("run")
def backtest_run(
    strategy: str = typer.Option("single_factor", "--strategy", help="策略类型"),
    factor: str = typer.Option(..., "--factor", help="因子名，如 momentum_20d"),
    start: str = typer.Option(..., "--start", help="起始日 YYYYMMDD"),
    end: str = typer.Option(..., "--end", help="结束日 YYYYMMDD"),
    rebalance: str = typer.Option("monthly", "--rebalance", help="monthly | weekly"),
    groups: int = typer.Option(10, "--groups", help="分组数"),
    force: bool = typer.Option(False, "--force", help="预留：强制覆盖同 run（当前每次新 run_id）"),
) -> None:
    """单因子截面回测：分组净值 + IC，结果写入 warehouse/backtest/。"""
    _ = force
    _run_backtest(strategy, factor, start, end, rebalance, groups)


# ─── gtja191 命令 ───


def _run_gtja191_compute(
    start_month: str | None = None,
    end_month: str | None = None,
    alpha: int | None = None,
    force: bool = False,
) -> None:
    from src.research.factor.gtja.strategy import Gtja191Strategy
    from src.research.factor.meta_service import FactorMetaService

    if start_month is None:
        try:
            start_month = input("起始月 YYYYMM（回车=全部）: ").strip() or None
        except EOFError:
            return
    if end_month is None and start_month is not None:
        try:
            end_month = input("结束月 YYYYMM（回车=同起始/最新）: ").strip() or None
        except EOFError:
            return

    Gtja191Strategy().compute(
        start_month=start_month,
        end_month=end_month,
        alpha=alpha,
        force=force,
    )
    FactorMetaService().update_meta()


@gtja191_cmd.command("compute")
def gtja191_compute(
    start_month: str | None = typer.Option(None, "--start-month", help="起始月 YYYYMM"),
    end_month: str | None = typer.Option(None, "--end-month", help="结束月 YYYYMM"),
    alpha: int | None = typer.Option(None, "--alpha", help="只算指定 Alpha 编号"),
    force: bool = typer.Option(False, "--force", help="强制重算已有分区"),
) -> None:
    """计算国泰191因子到 Parquet（Alpha30 跳过），并刷新 factor_meta。"""
    _run_gtja191_compute(start_month, end_month, alpha, force)


_MENU_HANDLERS: dict[str, Callable[[], None]] = {
    "factor-update-all": _run_factor_update_all,
    "factor-compute": lambda: _run_factor_compute(),
    "factor-sync-pg": lambda: _run_factor_sync_pg(),
    "factor-list": _run_factor_list,
    "tushare-factor-pull": lambda: _run_tushare_factor_pull(),
    "factor-update-meta": _run_factor_update_meta,
    "backtest-run": lambda: _run_backtest(),
    "gtja191-compute": lambda: _run_gtja191_compute(),
}

if __name__ == "__main__":
    app()
