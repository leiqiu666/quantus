"""通用工具函数"""

import time
import threading
from collections import deque
from typing import List, Dict, Any, Callable, Iterable, TypeVar

import pandas as pd

T = TypeVar("T")


def create_rate_limiter(max_per_minute: int) -> Callable[[], None]:
    """
    创建一个「每分钟最多 N 次」的限流器，用于 Tushare、新浪财经等 API 的请求频率控制。

    参数:
        max_per_minute: 服务端允许的每分钟最大请求次数。

    返回:
        一个无参可调用对象，每次发起请求前调用一次。
        实际执行上限为 (max_per_minute - 10)，达到即阻塞，避免与服务器统计误差导致超限；达到该安全上限时会打印告警。

    示例:
        >>> acquire = create_rate_limiter(400)
        >>> acquire()   # 请求前调用
        >>> response = requests.get(...)
    """
    window_sec = 60
    # 保留 5% 余量（至少 1 次），避免与服务器统计误差导致超限
    effective_max = max(1, int(max_per_minute * 0.95))
    times: deque = deque(maxlen=max_per_minute + 100)
    lock = threading.Lock()

    def acquire() -> None:
        now = time.monotonic()
        with lock:
            cutoff = now - window_sec
            while times and times[0] < cutoff:
                times.popleft()
            if len(times) >= effective_max:
                wait_secs = times[0] + window_sec - now
                if wait_secs > 0:
                    print(f"[限流告警] 已达安全上限 {effective_max} 次/分钟（服务端限制 {max_per_minute}），等待 {int(wait_secs)} 秒后继续")
                    time.sleep(wait_secs)
                now = time.monotonic()
                while times and times[0] < now - window_sec:
                    times.popleft()
            times.append(time.monotonic())

    return acquire


def dataframe_to_list(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """将 DataFrame 转为 dict 列表，NaN / pd.NA → None。"""
    if df.empty:
        return []

    out = df.where(pd.notna(df), None).to_dict(orient="records")
    for row in out:
        for k, v in row.items():
            if v is not None and v != v:
                row[k] = None
    return out

# 财报报告期：每季度最后一天，格式 YYYYMMDD
QUARTER_END_DATES = ("0331", "0630", "0930", "1231")


def report_period_generate(start_date: str, end_date: str) -> List[str]:
    """
    生成财报报告期列表

    参数说明
        start_date: 开始日期，格式 YYYYMMDD，如 "20240101"
        end_date: 结束日期，格式 YYYYMMDD，如 "20251231"

    返回说明
        report_period: 财报报告期列表，格式如 ["20240331", "20240630", "20240930", "20241231"]

    函数逻辑
        根据 start_date 和 end_date，生成该区间内所有季度末报告期；
        2005 年之前（不含）只生成半年报（0630）和年报（1231）；
        2005 年及之后生成完整四季报（0331/0630/0930/1231）。
    """
    if not start_date or not end_date or start_date > end_date:
        return []

    start_year = int(start_date[:4])
    end_year = int(end_date[:4])
    report_period = []

    for year in range(start_year, end_year + 1):
        qends = ("0630", "1231") if year < 2005 else QUARTER_END_DATES
        for qend in qends:
            period = f"{year}{qend}"
            if start_date <= period <= end_date:
                report_period.append(period)

    return report_period


def report_period_page_bounds(
    start_date: str,
    end_date: str,
    page: int,
    count: int,
) -> tuple[str, str] | None:
    """
    在 [start_date, end_date] 内按季度末生成全部报告期，再按「新→旧」分页，返回当前页的日历下界与上界（含），供按日期区间查库。

    参数:
        start_date / end_date: YYYYMMDD，与 report_period_generate 一致。
        page: 页码，从 1 起；第 1 页为最新报告期。
        count: 每页条数（季度个数）。

    返回:
        (window_lo, window_hi)：当前页所含季度在日历上的最小与最大 report_period（字符串比较即 YYYYMMDD 序）。
        区间内无季度、或 page 超出时返回 None。
    """
    if page < 1 or count < 1:
        return None
    periods_asc = report_period_generate(start_date, end_date)
    if not periods_asc:
        return None
    periods_new_first = list(reversed(periods_asc))
    offset = (page - 1) * count
    page_slice = periods_new_first[offset : offset + count]
    if not page_slice:
        return None
    return (min(page_slice), max(page_slice))


def _month_sequence(start_yyyymm: str, end_yyyymm: str) -> list[str]:
    """生成 YYYYMM 升序列表（含两端）。"""
    sy, sm = int(start_yyyymm[:4]), int(start_yyyymm[4:6])
    ey, em = int(end_yyyymm[:4]), int(end_yyyymm[4:6])
    result: list[str] = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        result.append(f"{y:04d}{m:02d}")
        m += 1
        if m > 12:
            y += 1
            m = 1
    return result


def month_page_bounds(
    start_yyyymm: str,
    end_yyyymm: str,
    page: int,
    count: int,
) -> tuple[str, str] | None:
    """在 [start_yyyymm, end_yyyymm] 内按「新→旧」分页，返回当前页的月份下界与上界。"""
    if page < 1 or count < 1:
        return None
    months_asc = _month_sequence(start_yyyymm, end_yyyymm)
    if not months_asc:
        return None
    months_new_first = list(reversed(months_asc))
    offset = (page - 1) * count
    page_slice = months_new_first[offset : offset + count]
    if not page_slice:
        return None
    return (min(page_slice), max(page_slice))


def trade_date_page_bounds(
    start_date: str,
    end_date: str,
    page: int,
    count: int,
    exchange: str = "SSE",
) -> tuple[str, str] | None:
    """
    在 [start_date, end_date] 内取 SSE 等交易所开市日序列，再按「新→旧」分页，
    返回当前页的日历下界与上界（含），供按日期区间查库。

    参数:
        start_date / end_date: YYYYMMDD。
        page: 页码，从 1 起；第 1 页为最新开市日。
        count: 每页条数（开市日个数）。
        exchange: 交易所，默认 SSE。

    返回:
        (window_lo, window_hi)：当前页所含开市日在日历上的最小与最大 trade_date。
        区间内无开市日、或 page 超出时返回 None。
    """
    if page < 1 or count < 1:
        return None
    from src.service.stock.stock_trade_cal_service import TradeCalService

    dates_asc = TradeCalService().get_open_trade_dates(
        start_date=start_date,
        end_date=end_date,
        exchange=exchange,
    )
    if not dates_asc:
        return None
    dates_new_first = list(reversed(dates_asc))
    offset = (page - 1) * count
    page_slice = dates_new_first[offset : offset + count]
    if not page_slice:
        return None
    return (min(page_slice), max(page_slice))


def calendar_day_sequence(start_date: str, end_date: str) -> List[str]:
    """生成 [start_date, end_date] 内全部自然日（YYYYMMDD，含两端）。"""
    if not start_date or not end_date or start_date > end_date:
        return []
    from datetime import datetime, timedelta

    cur = datetime.strptime(start_date[:8], "%Y%m%d").date()
    end = datetime.strptime(end_date[:8], "%Y%m%d").date()
    out: List[str] = []
    while cur <= end:
        out.append(cur.strftime("%Y%m%d"))
        cur += timedelta(days=1)
    return out


def calendar_day_page_bounds(
    start_date: str,
    end_date: str,
    page: int,
    count: int,
) -> tuple[str, str] | None:
    """
    在 [start_date, end_date] 内按自然日「新→旧」分页，返回当前页下界与上界（含）。
    第 1 页为最新自然日。
    """
    if page < 1 or count < 1:
        return None
    days_asc = calendar_day_sequence(start_date, end_date)
    if not days_asc:
        return None
    days_new_first = list(reversed(days_asc))
    offset = (page - 1) * count
    page_slice = days_new_first[offset : offset + count]
    if not page_slice:
        return None
    return (min(page_slice), max(page_slice))


def missing_quarter_report_periods(
    observed_end_dates: Iterable[str],
    start_end_date: str,
    end_end_date: str,
) -> List[str]:
    """
    在区间 [start_end_date, end_end_date] 内，按季度末序列（report_period_generate）对比已有报告期，
    返回缺失的报告期 end_date 列表（YYYYMMDD 字符串）。

    「应有」季度的起点：优先取已观测报告期在区间内的最小值（晚于上市后再查漏），
    若该最小值早于 start_end_date，则仍从 start_end_date 起算；若无任何观测，则整段从 start_end_date 起算。

    适用于利润表、现金流、资产负债表等任意「报告期列为季度末」的表：调用方只传入已存在的 end_date 集合即可。

    Args:
        observed_end_dates: 已观测报告期，均为 YYYYMMDD 字符串（无空值、无首尾空格）。
        start_end_date: 区间起点 YYYYMMDD（与报告期字符串比较）。
        end_end_date: 区间终点 YYYYMMDD（含边界）。

    Returns:
        应有而未出现的季度末 end_date 列表，顺序与 report_period_generate 一致。
    """
    missing_periods: List[str]

    if not start_end_date or not end_end_date or start_end_date > end_end_date:
        missing_periods = []
        return missing_periods

    observed: set[str] = {
        x for x in observed_end_dates if start_end_date <= x <= end_end_date
    }

    if observed:
        min_observed = min(observed)
        effective_start = max(min_observed, start_end_date)
    else:
        effective_start = start_end_date

    expected = report_period_generate(effective_start, end_end_date)
    if not expected:
        missing_periods = []
        return missing_periods

    missing_periods = [ed for ed in expected if ed not in observed]
    return missing_periods


def tqdm_iter(
    iterable: Iterable[T],
    *,
    desc: str = "",
    unit: str = "item",
    leave: bool = True,
):
    """
    对任意可迭代对象生成 tqdm 进度条（延迟导入以避免不必要的依赖开销）。
    leave=True 时迭代结束后仍保留最后一行进度（便于 CLI 跑完后看到 100% 结果）。
    """
    from tqdm.auto import tqdm

    return tqdm(
        iterable,
        desc=desc,
        unit=unit,
        mininterval=0.1,
        leave=leave,
        dynamic_ncols=True,
    )


MACRO_COMPLETE_THRESHOLD = 0.95


def scan_macro_snapshot_rows(
    rows: list[dict],
    *,
    count_field: str,
    stock_field: str = "period_stock_count",
    desc: str,
    unit: str,
) -> dict[str, int]:
    """
    宏观快照维度扫描：按日/按期 tqdm，统计 95% 达标与缺口。

    Returns:
        pass_days, fail_days, missing_records, active_stock（末行应在市/活跃股数）
    """
    pass_days = 0
    fail_days = 0
    missing_records = 0
    active_stock = 0
    pbar = tqdm_iter(rows, desc=desc, unit=unit)
    for row in pbar:
        stock_n = int(row.get(stock_field) or 0)
        cnt = int(row.get(count_field) or 0)
        active_stock = stock_n
        if stock_n <= 0:
            pbar.set_postfix(
                活跃=f"{active_stock}股",
                通过=f"{pass_days}{unit}",
                缺失=f"{fail_days}{unit}",
                缺条=missing_records,
            )
            continue
        floor = int(MACRO_COMPLETE_THRESHOLD * stock_n)
        if cnt >= floor:
            pass_days += 1
        else:
            fail_days += 1
            missing_records += max(0, floor - cnt)
        pbar.set_postfix(
            活跃=f"{active_stock}股",
            通过=f"{pass_days}{unit}",
            缺失=f"{fail_days}{unit}",
            缺条=missing_records,
        )
    return {
        "pass_days": pass_days,
        "fail_days": fail_days,
        "missing_records": missing_records,
        "active_stock": active_stock,
    }


def format_micro_stock_postfix(
    *,
    active_stocks: int,
    passed_stocks: int,
    failed_stocks: int,
    missing_items: int,
    missing_key: str = "缺日",
) -> dict[str, str | int]:
    """微观逐股检查 tqdm postfix。"""
    return {
        "活跃": f"{active_stocks}股",
        "通过": f"{passed_stocks}股",
        "缺失": f"{failed_stocks}股",
        missing_key: missing_items,
    }
