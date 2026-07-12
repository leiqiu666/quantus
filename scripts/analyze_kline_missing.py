"""分析 log_missing 中 kline_daily 缺失分布：市场 / 年份 / 重点股票。"""
from collections import Counter, defaultdict

from sqlalchemy import func, select

from src.common.database import Database
from src.entities.data_entities.log_missing import LogMissing
from src.entities.data_entities.stock_list_entities import StockListEntities as StockList


MISSING_ENTITY = "kline_daily"


def market_of(ts_code: str) -> str:
    """按 ts_code 前缀判断市场板块。"""
    if not ts_code or "." not in ts_code:
        return "未知"
    code, exch = ts_code.split(".", 1)
    if exch == "BJ":
        return "北交所(BJ)"
    if exch == "SH":
        if code.startswith("688"):
            return "科创板(688)"
        if code.startswith("605") or code.startswith("603") or code.startswith("601") or code.startswith("600"):
            return "沪主板(60x)"
        if code.startswith("900"):
            return "沪B股(900)"
        return f"沪其他({code[:3]})"
    if exch == "SZ":
        if code.startswith("300") or code.startswith("301"):
            return "创业板(300/301)"
        if code.startswith("000") or code.startswith("001"):
            return "深主板(000/001)"
        if code.startswith("002") or code.startswith("003"):
            return "中小板(002/003)"
        if code.startswith("200"):
            return "深B股(200)"
        return f"深其他({code[:3]})"
    return f"{exch}其他"


def main() -> None:
    db = Database()
    session = db.get_session()
    try:
        total = session.scalar(
            select(func.count()).select_from(LogMissing).where(LogMissing.missing_entity == MISSING_ENTITY)
        )
        if not total:
            print(f"log_missing 中无 missing_entity={MISSING_ENTITY} 记录。")
            return

        distinct_codes = session.scalar(
            select(func.count(func.distinct(LogMissing.ts_code)))
            .select_from(LogMissing)
            .where(LogMissing.missing_entity == MISSING_ENTITY)
        )
        date_min, date_max = session.execute(
            select(func.min(LogMissing.missing_date), func.max(LogMissing.missing_date))
            .where(LogMissing.missing_entity == MISSING_ENTITY)
        ).one()

        # 拉全量明细（kline_daily 记录数即便几十万也能扛）
        rows = session.execute(
            select(LogMissing.ts_code, LogMissing.missing_date, LogMissing.try_count)
            .where(LogMissing.missing_entity == MISSING_ENTITY)
        ).all()

        market_counter: Counter[str] = Counter()
        year_counter: Counter[str] = Counter()
        market_year: dict[str, Counter[str]] = defaultdict(Counter)
        per_code: Counter[str] = Counter()
        try_buckets: Counter[str] = Counter()
        per_code_try_max: dict[str, int] = {}

        for ts_code, missing_date, try_count in rows:
            mk = market_of(ts_code)
            yr = (missing_date or "")[:4] or "未知"
            market_counter[mk] += 1
            year_counter[yr] += 1
            market_year[mk][yr] += 1
            per_code[ts_code] += 1
            tc = try_count or 0
            if tc <= 1:
                try_buckets["1 次"] += 1
            elif tc <= 3:
                try_buckets["2-3 次"] += 1
            elif tc <= 10:
                try_buckets["4-10 次"] += 1
            else:
                try_buckets[">10 次"] += 1
            per_code_try_max[ts_code] = max(per_code_try_max.get(ts_code, 0), tc)

        # 关联 stock_list 拉名称 / 上市退市日
        top_codes = [c for c, _ in per_code.most_common(30)]
        stock_meta: dict[str, tuple[str, str, str, str]] = {}
        if top_codes:
            meta_rows = session.execute(
                select(StockList.ts_code, StockList.name, StockList.list_date, StockList.delist_date, StockList.list_status)
                .where(StockList.ts_code.in_(top_codes))
            ).all()
            for ts_code, name, list_date, delist_date, list_status in meta_rows:
                stock_meta[ts_code] = (name or "", list_date or "", delist_date or "", list_status or "")

        # --- 报告输出 ---
        print("=" * 72)
        print(f"kline_daily 缺失分布报告 (missing_entity = {MISSING_ENTITY})")
        print("=" * 72)
        print(f"总缺失记录数:     {total:,}")
        print(f"涉及股票数:       {distinct_codes:,}")
        print(f"缺失日期范围:     {date_min}  ~  {date_max}")
        print()

        print("【一】市场分布")
        print("-" * 72)
        print(f"{'市场板块':<22}{'缺失条数':>12}{'占比':>10}")
        for mk, cnt in sorted(market_counter.items(), key=lambda x: -x[1]):
            pct = cnt / total * 100
            print(f"{mk:<22}{cnt:>12,}{pct:>9.2f}%")
        print()

        print("【二】年份分布")
        print("-" * 72)
        print(f"{'年份':<10}{'缺失条数':>12}{'占比':>10}")
        for yr, cnt in sorted(year_counter.items()):
            pct = cnt / total * 100
            print(f"{yr:<10}{cnt:>12,}{pct:>9.2f}%")
        print()

        print("【三】市场 × 年份 交叉（仅 TOP 市场 × 全部年份）")
        print("-" * 72)
        years_sorted = sorted(year_counter.keys())
        top_markets = [m for m, _ in market_counter.most_common(6)]
        header = f"{'年份':<8}" + "".join(f"{m[:12]:>14}" for m in top_markets)
        print(header)
        for yr in years_sorted:
            line = f"{yr:<8}" + "".join(f"{market_year[m].get(yr, 0):>14,}" for m in top_markets)
            print(line)
        print()

        print("【四】缺失最严重的 TOP 30 股票")
        print("-" * 72)
        print(f"{'排名':<5}{'代码':<13}{'名称':<10}{'缺失':>8}{'最大重试':>10}  {'上市日':<10} {'退市日':<10} 状态")
        for i, (ts_code, cnt) in enumerate(per_code.most_common(30), 1):
            name, list_d, delist_d, status = stock_meta.get(ts_code, ("", "", "", ""))
            max_try = per_code_try_max.get(ts_code, 0)
            name_show = (name[:8] + "…") if len(name) > 9 else name
            print(
                f"{i:<5}{ts_code:<13}{name_show:<10}{cnt:>8,}{max_try:>10}  "
                f"{list_d:<10} {delist_d:<10} {status}"
            )
        print()

        print("【五】重试次数分布")
        print("-" * 72)
        for bucket in ["1 次", "2-3 次", "4-10 次", ">10 次"]:
            cnt = try_buckets.get(bucket, 0)
            pct = cnt / total * 100 if total else 0
            print(f"{bucket:<10}{cnt:>12,}{pct:>9.2f}%")
        print()

        # 退市股 / 在市股 缺失对比（只看 TOP 出现过的股票之外，需要全量元数据）
        all_codes = list(per_code.keys())
        status_meta: dict[str, str] = {}
        delist_meta: dict[str, str] = {}
        # 分批 IN 避免一次过大
        BATCH = 1000
        for i in range(0, len(all_codes), BATCH):
            chunk = all_codes[i : i + BATCH]
            rows2 = session.execute(
                select(StockList.ts_code, StockList.list_status, StockList.delist_date)
                .where(StockList.ts_code.in_(chunk))
            ).all()
            for ts_code, list_status, delist_date in rows2:
                status_meta[ts_code] = list_status or "未知"
                delist_meta[ts_code] = delist_date or ""

        status_counter: Counter[str] = Counter()
        status_codes: Counter[str] = Counter()
        unknown_codes = 0
        for ts_code, cnt in per_code.items():
            st = status_meta.get(ts_code)
            if st is None:
                unknown_codes += 1
                status_counter["未在 stock_list"] += cnt
                status_codes["未在 stock_list"] += 1
            else:
                label = {"L": "在市(L)", "D": "退市(D)", "P": "暂停上市(P)"}.get(st, f"其他({st})")
                status_counter[label] += cnt
                status_codes[label] += 1

        print("【六】按上市状态聚合（缺失条数 / 涉及股票数）")
        print("-" * 72)
        print(f"{'状态':<18}{'缺失条数':>12}{'占比':>10}{'股票数':>10}")
        for label, cnt in sorted(status_counter.items(), key=lambda x: -x[1]):
            pct = cnt / total * 100
            print(f"{label:<18}{cnt:>12,}{pct:>9.2f}%{status_codes[label]:>10}")
        print()

        print("【建议】")
        print("-" * 72)
        print("1. 缺失记录条数 / 涉及股票数 = " f"{total/max(distinct_codes,1):.1f} 条/股，判断是 ‘少量集中’ 还是 ‘大面积稀疏’。")
        print("2. 重点关注 try_count > 10 与 退市股：通常 tdx_quant 拉不到，需要走 tushare 兜底或确认是否真无数据。")
        print("3. 北交所 / B 股若占比异常高，确认数据源是否对该板块全覆盖。")
        print("4. 某年份突增通常对应数据源切换 / 接口限流：对照 kline_daily_by_date_sources 的历史变更。")
    finally:
        session.close()


if __name__ == "__main__":
    main()
