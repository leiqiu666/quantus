"""Tushare ETL 全链路代码骨架生成器（vibe_tushare_fullstack）。

在 vibe_tushare_etl 骨架基础上，额外输出 Admin 看板列 / SSE 注册片段与 checklist。

用法：
    uv run python .claude/skills/vibe_tushare_fullstack/generate_skeleton.py \\
      --api-name top_inst \\
      --domain market_dragon_tiger \\
      --domain-dir market \\
      --table-name dragon_tiger_inst \\
      --pull-mode by-date \\
      --conflict-keys "ts_code,trade_date" \\
      --output-fields "ts_code:str,trade_date:str" \\
      --rate-limit 200 \\
      --has-transform false \\
      --has-completeness true \\
      --cli-group dragon-tiger \\
      --cli-command pull-by-date-range \\
      --dashboard-group market_trade_date \\
      --column-key dragon_tiger_inst \\
      --column-label 龙虎榜机构 \\
      --sse-task-key dragon_tiger_inst_check \\
      --source-name dragon_tiger_inst \\
      --emit-checklist
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from textwrap import dedent
from typing import Literal

PullMode = Literal["by-date", "by-period", "snapshot", "by-code"]


def parse_field_list(s: str) -> list[tuple[str, str]]:
    """解析 field:type 逗号分隔列表。"""
    if not s or not s.strip():
        return []
    pairs = []
    for token in s.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" in token:
            name, ftype = token.split(":", 1)
            pairs.append((name.strip(), ftype.strip()))
        else:
            pairs.append((token, "str"))
    return pairs


def tushare_type_to_sqlalchemy(ftype: str) -> str:
    """Tushare 字段类型字符串 → SQLAlchemy Column 类型字符串。"""
    t = ftype.lower().strip()
    if t in ("str", "string", "object"):
        return "String(128)"
    if t in ("int", "int64", "integer"):
        return "BigInteger"
    if t in ("float", "float64", "double", "decimal"):
        return "Float"
    if t in ("datetime", "date"):
        return "String(32)"
    return "String(128)"


def _collect_sqlalchemy_types(output_fields: list[tuple[str, str]]) -> list[str]:
    """收集需要的 SQLAlchemy 类型导入。"""
    types = set()
    for _, ftype in output_fields:
        sa_type = tushare_type_to_sqlalchemy(ftype)
        if sa_type.startswith("String"):
            types.add("String")
        elif sa_type == "BigInteger":
            types.add("BigInteger")
        elif sa_type == "Float":
            types.add("Float")
    return sorted(types)


def tushare_type_to_python(ftype: str) -> str:
    """Tushare 字段类型 → Python 类型注解字符串。"""
    t = ftype.lower().strip()
    if t in ("int", "int64", "integer"):
        return "int"
    if t in ("float", "float64", "double", "decimal"):
        return "float"
    return "str"


def to_class_name(snake: str) -> str:
    """snake_case → PascalCase。"""
    return "".join(word.capitalize() for word in snake.split("_"))


def to_method_suffix(api_name: str) -> str:
    """接口名 → 方法名后缀（去掉常见前缀）。"""
    return api_name


# ─── 生成器主类 ────────────────────────────────────────────────────────────────


class SkeletonGenerator:
    def __init__(
        self,
        api_name: str,
        domain: str,
        domain_dir: str,
        table_name: str,
        pull_mode: PullMode,
        conflict_keys: list[str],
        input_fields: list[tuple[str, str]],
        output_fields: list[tuple[str, str]],
        rate_limit: int,
        has_transform: bool,
        has_completeness: bool,
        cli_group: str,
        cli_command: str,
        spec_path: str,
        dashboard_group: str = "",
        column_key: str = "",
        column_label: str = "",
        sse_task_key: str = "",
        source_name: str = "",
    ) -> None:
        self.api_name = api_name
        self.domain = domain          # 域前缀，如 market_northbound
        self.domain_dir = domain_dir  # 域目录，如 market
        self.table_name = table_name  # DB 表名，如 market_northbound_top10
        self.pull_mode = pull_mode
        self.conflict_keys = conflict_keys
        self.input_fields = input_fields
        self.output_fields = output_fields
        self.rate_limit = rate_limit
        self.has_transform = has_transform
        self.has_completeness = has_completeness
        self.cli_group = cli_group
        self.cli_command = cli_command
        self.spec_path = spec_path
        self.dashboard_group = dashboard_group or ""
        self.column_key = column_key or table_name
        self.column_label = column_label or table_name
        self.sse_task_key = sse_task_key or f"{table_name}_check"
        self.source_name = source_name or table_name

        self.cls_name = to_class_name(table_name)
        self.domain_cls = to_class_name(domain)
        self.output_field_names = [f[0] for f in output_fields]

        self.project_root = Path(__file__).resolve().parents[3]
        self.generated_files: list[Path] = []
        self.snippets: dict[str, str] = {}

    # ── 公共入口 ─────────────────────────────────────────────────────────────

    def generate_all(self) -> None:
        """生成所有骨架文件并输出 snippets。"""
        self._gen_entities()
        self._gen_client_common()
        self._gen_client_tushare()
        self._gen_extract()
        if self.has_transform:
            self._gen_transform()
        self._gen_load()
        self._gen_workflow()
        self._gen_strategy()
        self._gen_model()
        self._gen_service()
        self._gen_local_extract()
        self._build_snippets()
        self._print_summary()

    # ── 文件写入工具 ─────────────────────────────────────────────────────────

    def _write(self, rel_path: str, content: str) -> Path:
        p = self.project_root / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(dedent(content).lstrip(), encoding="utf-8")
        self.generated_files.append(p)
        return p

    # ── Entities ─────────────────────────────────────────────────────────────

    def _gen_entities(self) -> None:
        cols_lines = []
        for name, ftype in self.output_fields:
            sa_type = tushare_type_to_sqlalchemy(ftype)
            cols_lines.append(f'    {name} = Column({sa_type}, comment="")')

        conflict_key_cols = ",\n".join(f'        "{k}"' for k in self.conflict_keys)
        idx_unique_name = f"idx_{self.table_name}_unique"

        # 收集需要的 SQLAlchemy 类型导入
        extra_types = _collect_sqlalchemy_types(self.output_fields)
        import_list = ["Column", "Integer"] + extra_types + ["Index"]
        import_str = ", ".join(import_list)

        content = f'''"""{self.table_name} 实体（Tushare {self.api_name}）。"""

from sqlalchemy import {import_str}
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class {self.cls_name}Entities(Base):
    __tablename__ = "{self.table_name}"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
{chr(10).join(cols_lines)}

    __table_args__ = (
        Index(
            "{idx_unique_name}",
{conflict_key_cols},
            unique=True,
        ),
        # TODO: 按需补充其他索引
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table({self.cls_name}Entities)
'''
        self._write(
            f"src/entities/data_entities/{self.domain_dir}/{self.table_name}_entities.py",
            content,
        )

    # ── Client Common ────────────────────────────────────────────────────────

    def _gen_client_common(self) -> None:
        col_tuple_items = ",\n".join(f'    "{n}"' for n in self.output_field_names)

        normalize_funcs = dedent('''
def _normalize_ymd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else ""


def _normalize_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    s = str(value).strip()
    if s.lower() in ("none", "nan", "null"):
        return ""
    return s
''').rstrip()

        # 识别哪些字段是日期字段（trade_date / end_date / ann_date 等）
        date_fields = [
            n for n in self.output_field_names
            if "date" in n.lower() or n in ("period", "report_date", "ann_date", "f_ann_date", "end_date")
        ]
        str_fields = [n for n in self.output_field_names if n not in date_fields]

        finalize_lines = []
        for f in date_fields:
            finalize_lines.append(f'    out["{f}"] = out["{f}"].map(_normalize_ymd)')
        for f in str_fields:
            finalize_lines.append(f'    out["{f}"] = out["{f}"].map(_normalize_str)')

        finalize_body = "\n".join(finalize_lines) if finalize_lines else "    pass  # TODO: 按需添加字段归一化"

        content = f'''"""{self.domain} Client 共用工具。"""

from __future__ import annotations

import pandas as pd

# Tushare {self.api_name} 输出列
{self.domain.upper()}_COLUMNS: tuple[str, ...] = (
{col_tuple_items},
)

{normalize_funcs}


def is_usable_{self.domain}(df: pd.DataFrame | None) -> bool:
    """DataFrame 是否可用于后续流程。"""
    if df is None or df.empty:
        return False
    # TODO: 按需补充必要列校验
    return True


def finalize_{self.domain}(df: pd.DataFrame | None) -> pd.DataFrame:
    """对齐 {self.api_name} 实体列，归一化字段，去重。"""
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
{finalize_body}

    # 补齐缺失列
    for col in {self.domain.upper()}_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    out = out[list({self.domain.upper()}_COLUMNS)].drop_duplicates(
        subset=list({self.domain.upper()}_COLUMNS), keep="last"
    )
    return out.reset_index(drop=True)
'''
        self._write(
            f"src/etl/client/{self.domain_dir}/{self.domain}_common.py",
            content,
        )

    # ── Client Tushare ───────────────────────────────────────────────────────

    def _gen_client_tushare(self) -> None:
        # 根据 pull_mode 生成不同的 pull 方法签名
        if self.pull_mode == "by-date":
            method_sig = "def pull_{self.api_name}_by_date(self, trade_date: str) -> pd.DataFrame:"
            api_call_kwargs = "trade_date=td"
            pre_call = '''td = (trade_date or "").strip()
        if not td:
            return pd.DataFrame()'''
            method_name = f"pull_{self.api_name}_by_date"
            doc_desc = "拉取指定交易日数据"
        elif self.pull_mode == "by-period":
            method_sig = "def pull_{self.api_name}_by_period(self, period: str) -> pd.DataFrame:"
            api_call_kwargs = "period=period"
            pre_call = '''period = (period or "").strip()
        if not period:
            return pd.DataFrame()'''
            method_name = f"pull_{self.api_name}_by_period"
            doc_desc = "拉取指定报告期数据"
        elif self.pull_mode == "snapshot":
            method_sig = "def pull_{self.api_name}(self) -> pd.DataFrame:"
            api_call_kwargs = ""
            pre_call = ""
            method_name = f"pull_{self.api_name}"
            doc_desc = "拉取全量快照"
        else:  # by-code
            method_sig = "def pull_{self.api_name}_by_code(self, ts_code: str) -> pd.DataFrame:"
            api_call_kwargs = "ts_code=code"
            pre_call = '''code = (ts_code or "").strip()
        if not code:
            return pd.DataFrame()'''
            method_name = f"pull_{self.api_name}_by_code"
            doc_desc = "拉取指定股票数据"

        content = f'''"""Tushare {self.api_name} Client。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.entities.client_entities.tushare_entities import tushare_entities
from src.etl.client.{self.domain_dir}.{self.domain}_common import finalize_{self.domain}
from src.etl.client.base import call_with_network_retry

_acquire_{self.domain}_rate_limit = create_rate_limiter({self.rate_limit})


class Tushare{self.domain_cls}Client:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts
        self.{self.domain}_fields = tushare_entities.{self.table_name}

    def {method_name}(self{", trade_date: str" if self.pull_mode == "by-date" else ", period: str" if self.pull_mode == "by-period" else ", ts_code: str" if self.pull_mode == "by-code" else ""}) -> pd.DataFrame:
        """
        {doc_desc}。

        参考：https://tushare.pro/document/2?doc_id=TODO
        """
        {pre_call}

        _acquire_{self.domain}_rate_limit()
        df = call_with_network_retry(
            self.ts.{self.api_name},
            {api_call_kwargs},
            fields=self.{self.domain}_fields,
        )
        return finalize_{self.domain}(df)
'''
        self._write(
            f"src/etl/client/{self.domain_dir}/{self.domain}_tushare_client.py",
            content,
        )

    # ── Extract ──────────────────────────────────────────────────────────────

    def _gen_extract(self) -> None:
        if self.pull_mode == "by-date":
            method_name = f"pull_{self.api_name}_by_date"
            sig_param = "trade_date: str"
            call_arg = "trade_date"
        elif self.pull_mode == "by-period":
            method_name = f"pull_{self.api_name}_by_period"
            sig_param = "period: str"
            call_arg = "period"
        elif self.pull_mode == "snapshot":
            method_name = f"pull_{self.api_name}"
            sig_param = ""
            call_arg = ""
        else:
            method_name = f"pull_{self.api_name}_by_code"
            sig_param = "ts_code: str"
            call_arg = "ts_code"

        call_args_str = call_arg if call_arg else ""

        content = f'''"""{self.domain} Extract：编排 Tushare Client。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.{self.domain_dir}.{self.domain}_common import is_usable_{self.domain}
from src.etl.client.{self.domain_dir}.{self.domain}_tushare_client import Tushare{self.domain_cls}Client


class {self.domain_cls}Extract:
    def __init__(self) -> None:
        self._client = Tushare{self.domain_cls}Client()

    def {method_name}(self{", " + sig_param if sig_param else ""}) -> pd.DataFrame:
        df = self._client.{method_name}({call_args_str})
        if not is_usable_{self.domain}(df):
            return pd.DataFrame()
        return df
'''
        self._write(
            f"src/etl/extract/{self.domain_dir}/{self.domain}_extract.py",
            content,
        )

    # ── Transform（可选）──────────────────────────────────────────────────────

    def _gen_transform(self) -> None:
        content = f'''"""{self.domain} Transform（可选）。"""

from __future__ import annotations

import pandas as pd


class {self.domain_cls}Transform:
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        在此执行数据清洗、去重、JSONB 转换等逻辑。

        TODO: 根据 SDD spec 中的业务规则实现。
        """
        if df is None or df.empty:
            return pd.DataFrame()
        # TODO: 实现 transform 逻辑
        return df
'''
        self._write(
            f"src/etl/transform/{self.domain_dir}/{self.domain}_transform.py",
            content,
        )

    # ── Load ─────────────────────────────────────────────────────────────────

    def _gen_load(self) -> None:
        conflict_keys_str = ", ".join(f'"{k}"' for k in self.conflict_keys)

        content = f'''"""{self.domain} 入库。"""

from __future__ import annotations

import pandas as pd

from src.common.database import Database, DEFAULT_BULK_UPSERT_CHUNK_SIZE
from src.common.function import dataframe_to_list
from src.entities.data_entities.{self.domain_dir}.{self.table_name}_entities import {self.cls_name}Entities


class {self.domain_cls}Load:
    def __init__(self) -> None:
        self.db = Database()

    def load_{self.domain}(
        self,
        df: pd.DataFrame,
        *,
        chunk_size: int | None = DEFAULT_BULK_UPSERT_CHUNK_SIZE,
    ) -> int:
        if df is None or df.empty:
            return 0
        self.db.ensure_table({self.cls_name}Entities)
        records = dataframe_to_list(df)
        return self.db.bulk_upsert_postgresql(
            model_class={self.cls_name}Entities,
            records=records,
            conflict_keys=[{conflict_keys_str}],
            fallback_on_error=True,
            skip_length_check=True,
            chunk_size=chunk_size,
        )
'''
        self._write(
            f"src/etl/load/{self.domain_dir}/{self.domain}_load.py",
            content,
        )

    # ── Workflow ─────────────────────────────────────────────────────────────

    def _gen_workflow(self) -> None:
        if self.pull_mode == "by-date":
            wf_method = f"pull_{self.api_name}_by_date"
            sig_param = "trade_date: str"
            call_arg = "trade_date"
        elif self.pull_mode == "by-period":
            wf_method = f"pull_{self.api_name}_by_period"
            sig_param = "period: str"
            call_arg = "period"
        elif self.pull_mode == "snapshot":
            wf_method = f"pull_{self.api_name}"
            sig_param = ""
            call_arg = ""
        else:
            wf_method = f"pull_{self.api_name}_by_code"
            sig_param = "ts_code: str"
            call_arg = "ts_code"

        transform_line = ""
        extract_call = f"df = self.{self.domain}_extract.{wf_method}({call_arg})"
        if self.has_transform:
            transform_line = f"        df = self.{self.domain}_transform.transform(df)"

        content = f'''"""{self.domain} 单日/单次工作流。"""

from __future__ import annotations

from src.etl.extract.{self.domain_dir}.{self.domain}_extract import {self.domain_cls}Extract
from src.etl.load.{self.domain_dir}.{self.domain}_load import {self.domain_cls}Load
{"from src.etl.transform." + self.domain_dir + "." + self.domain + "_transform import " + self.domain_cls + "Transform" if self.has_transform else ""}


class {self.domain_cls}Workflow:
    def __init__(self) -> None:
        self.{self.domain}_extract = {self.domain_cls}Extract()
        self.{self.domain}_load = {self.domain_cls}Load()
{"        self." + self.domain + "_transform = " + self.domain_cls + "Transform()" if self.has_transform else ""}

    def {wf_method}(self{", " + sig_param if sig_param else ""}) -> int:
        {extract_call}
{transform_line}
        return self.{self.domain}_load.load_{self.domain}(df)
'''
        self._write(
            f"src/etl/workflow/{self.domain_dir}/{self.domain}_workflow.py",
            content,
        )

    # ── Strategy ─────────────────────────────────────────────────────────────

    def _gen_strategy(self) -> None:
        if self.pull_mode == "by-date":
            strategy_body = self._strategy_by_date()
        elif self.pull_mode == "by-period":
            strategy_body = self._strategy_by_period()
        elif self.pull_mode == "snapshot":
            strategy_body = self._strategy_snapshot()
        else:
            strategy_body = self._strategy_by_code()

        content = f'''"""{self.domain} 区间编排 Strategy。"""

from __future__ import annotations

from datetime import datetime

from src.common.function import tqdm_iter
from src.common.setting import settings
from src.etl.extract.local.{self.domain_dir}.{self.domain}_extract import {self.domain_cls}LocalExtract
from src.etl.extract.local.stock.stock_trade_calendar_extract import TradeCalLocalExtract
from src.etl.strategy.stock.stock_trade_calendar_strategy import TradeCalStrategy
from src.etl.workflow.{self.domain_dir}.{self.domain}_workflow import {self.domain_cls}Workflow
{"from src.common.completeness import CompletenessConfig, CompletenessEngine" + chr(10) + "from src.entities.data_entities." + self.domain_dir + "." + self.table_name + "_entities import " + self.cls_name + "Entities" if self.has_completeness else ""}


class {self.domain_cls}Strategy:
    def __init__(self) -> None:
        self.{self.domain}_workflow = {self.domain_cls}Workflow()
        self.{self.domain}_local = {self.domain_cls}LocalExtract()
        self.trade_cal_local = TradeCalLocalExtract()
        self.trade_cal_strategy = TradeCalStrategy()
        self.{self.domain}_start_date = settings.etl_start_date("{self.table_name}")

{strategy_body}
{self._completeness_methods() if self.has_completeness else ""}
'''
        self._write(
            f"src/etl/strategy/{self.domain_dir}/{self.domain}_strategy.py",
            content,
        )

    def _strategy_by_date(self) -> str:
        return dedent(f'''
    def pull_{self.api_name}_by_date(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> int:
        """按 SSE 开市日逐日拉取并 upsert。"""
        if start_date is None:
            start_date = self.{self.domain}_start_date
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        floor = (start_date or "").strip()
        end = (end_date or "").strip()
        if not floor or not end or floor > end:
            return 0

        self.trade_cal_strategy.ensure_trade_cal(
            start_date=floor,
            end_date=end,
            exchange="SSE",
        )

        eff_start = self.{self.domain}_local.resolve_incremental_start(
            configured_start=floor,
        )
        if not eff_start or eff_start > end:
            print(f"[信息] {self.domain} 已同步至最新，跳过")
            return 0

        trade_dates = self.trade_cal_local.get_open_trade_dates(
            start_date=eff_start,
            end_date=end,
            exchange="SSE",
        )
        if not trade_dates:
            print(f"[信息] {self.domain} 区间 {{eff_start}}~{{end}} 无 SSE 开市日，跳过")
            return 0

        print(
            f"[信息] {self.domain} 区间 {{eff_start}}~{{end}}，"
            f"待补开市日 {{len(trade_dates)}} 天"
        )

        total_saved = 0
        pbar = tqdm_iter(trade_dates, desc="{self.domain}入库", unit="日")
        for td in pbar:
            n = self.{self.domain}_workflow.pull_{self.api_name}_by_date(td)
            total_saved += n
            pbar.set_postfix(saved=n, total=total_saved, date=td)

        return total_saved
''').rstrip()

    def _completeness_methods(self) -> str:
        if self.pull_mode == "by-date":
            pull_lambda = (
                f"lambda td: self.{self.domain}_workflow.pull_{self.api_name}_by_date(td)"
            )
            date_col = "trade_date"
            is_period = "False"
        elif self.pull_mode == "by-period":
            pull_lambda = (
                f"lambda period: self.{self.domain}_workflow.pull_{self.api_name}_by_period(period)"
            )
            date_col = "end_date"
            is_period = "True"
        else:
            pull_lambda = "None  # TODO: 绑定 pull 方法"
            date_col = "trade_date"
            is_period = "False"

        pull_kw = "pull_by_date" if self.pull_mode == "by-date" else "pull_by_date"
        if self.pull_mode == "by-period":
            pull_kw = "pull_by_date"  # CompletenessEngine 仍用 pull_by_date 名，传 period

        return dedent(f'''

    @property
    def _completeness(self) -> CompletenessEngine:
        return CompletenessEngine(CompletenessConfig(
            source_name="{self.source_name}",
            entity_class={self.cls_name}Entities,
            date_column="{date_col}",
            start_date=self.{self.domain}_start_date,
            is_period={is_period},
            pull_by_date={pull_lambda},
        ))

    def refresh_completeness_snapshot(self, start_date=None, end_date=None) -> int:
        return self._completeness.refresh_snapshot(start_date, end_date)

    def check_complete(self, start_date=None, end_date=None) -> int:
        return self._completeness.check_complete(start_date, end_date)
''').rstrip()

    def _strategy_by_period(self) -> str:
        return dedent(f'''
    def pull_{self.api_name}_by_period(
        self,
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> int:
        """按期次（如 20231231）遍历拉取并 upsert。"""
        # TODO: 实现期次生成逻辑（参考 report 域）
        # 通常：生成 [start_period, end_period] 内的所有报告期
        # 对每个期次调用 self.{self.domain}_workflow.pull_{self.api_name}_by_period(period)
        raise NotImplementedError("TODO: 实现按报告期遍历逻辑")
''').rstrip()

    def _strategy_snapshot(self) -> str:
        return dedent(f'''
    def pull_{self.api_name}(self) -> int:
        """全量快照拉取并 upsert。"""
        print(f"[信息] 开始拉取 {self.domain} 全量快照")
        n = self.{self.domain}_workflow.pull_{self.api_name}()
        print(f"[信息] {self.domain} 全量快照入库 {{n}} 条")
        return n
''').rstrip()

    def _strategy_by_code(self) -> str:
        return dedent(f'''
    def pull_{self.api_name}_by_code(
        self,
        ts_codes: list[str] | None = None,
    ) -> int:
        """逐股拉取并 upsert。"""
        # TODO: 从 stock_basic 获取全市场 ts_code 列表
        if not ts_codes:
            print(f"[信息] 未提供 ts_codes，跳过")
            return 0

        total_saved = 0
        pbar = tqdm_iter(ts_codes, desc="{self.domain}入库", unit="股")
        for code in pbar:
            n = self.{self.domain}_workflow.pull_{self.api_name}_by_code(code)
            total_saved += n
            pbar.set_postfix(saved=n, total=total_saved, code=code)

        return total_saved
''').rstrip()

    # ── Model ────────────────────────────────────────────────────────────────

    def _gen_model(self) -> None:
        content = f'''"""{self.table_name} 表查询。"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.common.database import Database
from src.entities.data_entities.{self.domain_dir}.{self.table_name}_entities import {self.cls_name}Entities


class {self.domain_cls}Model:
    def __init__(self) -> None:
        self.db = Database()
        self.db.ensure_table({self.cls_name}Entities)

    def get_max_trade_date(self) -> str | None:
        """库内最大 trade_date（适用于按日期拉取的场景）。"""
        session: Session = self.db.get_session()
        try:
            row = session.query(func.max({self.cls_name}Entities.trade_date)).scalar()
            if row is None:
                return None
            s = str(row).strip()
            return s[:8] if len(s) >= 8 else None
        finally:
            session.close()

    # TODO: 根据业务需要补充其他查询方法
'''
        self._write(
            f"src/model/{self.domain_dir}/{self.domain}_model.py",
            content,
        )

    # ── Service ──────────────────────────────────────────────────────────────

    def _gen_service(self) -> None:
        content = f'''"""{self.domain} 查询服务（仅读库，不依赖 ETL）。"""

from __future__ import annotations

from datetime import datetime, timedelta

from src.model.{self.domain_dir}.{self.domain}_model import {self.domain_cls}Model


def _ymd_add_days(ymd: str, days: int) -> str:
    d = datetime.strptime(ymd.strip(), "%Y%m%d").date()
    return (d + timedelta(days=days)).strftime("%Y%m%d")


class {self.domain_cls}Service:
    def __init__(self) -> None:
        self._model = {self.domain_cls}Model()

    def get_max_trade_date(self) -> str | None:
        return self._model.get_max_trade_date()

    def resolve_incremental_start(self, *, configured_start: str) -> str:
        """增量同步起点：max(配置起始日, 库内最大 trade_date 的下一自然日)。"""
        floor = (configured_start or "").strip()
        if not floor:
            return ""

        last = self.get_max_trade_date()
        if not last:
            return floor
        nxt = _ymd_add_days(last, 1)
        return max(floor, nxt)

    # TODO: 根据业务需要补充其他查询方法
'''
        self._write(
            f"src/service/{self.domain_dir}/{self.domain}_service.py",
            content,
        )

    # ── Local Extract ────────────────────────────────────────────────────────

    def _gen_local_extract(self) -> None:
        content = f'''"""{self.domain} 本地 Extract：经 Service 读库。"""

from __future__ import annotations

from src.service.{self.domain_dir}.{self.domain}_service import {self.domain_cls}Service


class {self.domain_cls}LocalExtract:
    def __init__(self) -> None:
        self._service = {self.domain_cls}Service()

    def get_max_trade_date(self) -> str | None:
        return self._service.get_max_trade_date()

    def resolve_incremental_start(self, *, configured_start: str) -> str:
        return self._service.resolve_incremental_start(
            configured_start=configured_start,
        )

    # TODO: 根据业务需要补充其他读库方法
'''
        self._write(
            f"src/etl/extract/local/{self.domain_dir}/{self.domain}_extract.py",
            content,
        )

    # ── Snippets ─────────────────────────────────────────────────────────────

    def _build_snippets(self) -> None:
        # CLI 子命令注册片段
        if self.pull_mode == "by-date":
            cli_params = "start_date: str | None = None, end_date: str | None = None"
            cli_call_args = "start_date=start_date, end_date=end_date"
        elif self.pull_mode == "by-period":
            cli_params = "start_period: str | None = None, end_period: str | None = None"
            cli_call_args = "start_period=start_period, end_period=end_period"
        elif self.pull_mode == "snapshot":
            cli_params = ""
            cli_call_args = ""
        else:
            cli_params = "ts_codes: list[str] | None = None"
            cli_call_args = "ts_codes=ts_codes"

        self.snippets["cli.py — 子命令注册"] = dedent(f'''
# ── 添加到 {self.cli_group} 子命令组 ──────────────────────────────────────
@{self.cli_group}_app.command("{self.cli_command}")
def cmd_{self.domain}_{self.cli_command.replace("-", "_")}({cli_params}) -> None:
    """拉取 {self.api_name} 数据。"""
    from src.etl.strategy.{self.domain_dir}.{self.domain}_strategy import {self.domain_cls}Strategy

    strategy = {self.domain_cls}Strategy()
    strategy.pull_{self.api_name}_{"by_date" if self.pull_mode == "by-date" else "by_period" if self.pull_mode == "by-period" else "by_code" if self.pull_mode == "by-code" else self.api_name}({cli_call_args})
''').rstrip()

        # 交互菜单条目
        self.snippets["cli.py — 交互菜单 _MENU_ROWS"] = dedent(f'''
# ── 添加到 _MENU_ROWS 列表 ──────────────────────────────────────────────
{{
    "key": "{self.domain}_{self.cli_command.replace("-", "_")}",
    "category": "TODO: 分类标签",
    "label": "{self.api_name} {self.cli_command}",
    "action": cmd_{self.domain}_{self.cli_command.replace("-", "_")},
}},
''').rstrip()

        # setting.py 片段
        self.snippets["setting.py — 新增配置项"] = dedent(f'''
# ── 添加到 Settings 类 ────────────────────────────────────────────────────
{self.domain}_start_date: str = "TODO: 设定起始日期，如 20000101"
''').rstrip()

        # tushare_entities.py 片段
        field_names = ", ".join(self.output_field_names)
        self.snippets["tushare_entities.py — 新增字段列表"] = dedent(f'''
# ── 添加到 TushareEntities 类 ─────────────────────────────────────────────
{self.table_name}: str = "{field_names}"
''').rstrip()

        if self.dashboard_group:
            self.snippets["completeness_dashboard_config.py — 看板列"] = dedent(f'''
# ── 在 DASHBOARD_GROUPS["{self.dashboard_group}"].columns 末尾追加 ────────
DashboardColumn(
    "{self.column_key}",
    "{self.column_label}",
    source_name="{self.source_name}",
    threshold=0.95,
    sse_task_key="{self.sse_task_key}",
),
''').rstrip()

            self.snippets["etl_sse_registry.py — SSE 注册"] = dedent(f'''
# ── 添加到 SSE_TASK_REGISTRY ─────────────────────────────────────────────
from src.etl.strategy.{self.domain_dir}.{self.domain}_strategy import {self.domain_cls}Strategy

"{self.sse_task_key}": lambda start, end, q: _run_check(
    {self.domain_cls}Strategy().check_complete, start, end, q,
),
''').rstrip()

        if self.has_completeness:
            self.snippets["cli.py — check-complete 子命令"] = dedent(f'''
@{self.cli_group}_app.command("check-complete")
def cmd_{self.domain}_check_complete(
    start_date: str | None = None,
    end_date: str | None = None,
) -> None:
    from src.etl.strategy.{self.domain_dir}.{self.domain}_strategy import {self.domain_cls}Strategy

    saved = {self.domain_cls}Strategy().check_complete(
        start_date=start_date, end_date=end_date,
    )
    typer.echo(f"补拉 {{saved}} 条")
''').rstrip()

    def _emit_checklist(self) -> None:
        skill_dir = Path(__file__).resolve().parent
        for name in ("etl_touchpoints.md", "admin_touchpoints.md"):
            p = skill_dir / "checklists" / name
            if p.exists():
                print(f"\n── checklist: {name} ─────────────────────────────────────")
                print(p.read_text(encoding="utf-8"))

    # ── 汇总输出 ─────────────────────────────────────────────────────────────

    def _print_summary(self) -> None:
        print("=" * 72)
        print(f"骨架生成完成")
        print(f"  接口：{self.api_name}")
        print(f"  Domain：{self.domain}")
        print(f"  拉取模式：{self.pull_mode}")
        print(f"  冲突键：{', '.join(self.conflict_keys)}")
        print("=" * 72)
        print()

        print("【生成的文件】")
        for f in self.generated_files:
            rel = f.relative_to(self.project_root)
            print(f"  ✓ {rel}")
        print()

        print("【需要手动添加到现有文件的代码片段】")
        for title, snippet in self.snippets.items():
            print(f"\n── {title} ──────────────────────────────────────────────")
            print(snippet)
            print()


# ─── CLI 入口 ──────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tushare ETL 代码骨架生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--api-name", required=True, help="Tushare 接口名，如 suspend_d")
    parser.add_argument("--domain", required=True, help="域前缀，如 market_northbound")
    parser.add_argument("--domain-dir", required=True, help="域目录名：financial / market / kline / stock / index / warehouse")
    parser.add_argument("--table-name", required=True, help="DB 表名（带域前缀），如 market_northbound_top10")
    parser.add_argument(
        "--pull-mode",
        required=True,
        choices=["by-date", "by-period", "snapshot", "by-code"],
        help="拉取模式",
    )
    parser.add_argument(
        "--conflict-keys",
        required=True,
        help="冲突键，逗号分隔，如 ts_code,trade_date",
    )
    parser.add_argument(
        "--input-fields",
        default="",
        help="Tushare 输入参数，field:type 逗号分隔",
    )
    parser.add_argument(
        "--output-fields",
        required=True,
        help="Tushare 输出字段，field:type 逗号分隔",
    )
    parser.add_argument("--rate-limit", type=int, default=200, help="Tushare 限流（次/分钟）")
    parser.add_argument(
        "--has-transform",
        default="false",
        help="是否需要 Transform 层（true/false）",
    )
    parser.add_argument(
        "--has-completeness",
        default="false",
        help="是否需要完整性校验（true/false）",
    )
    parser.add_argument("--cli-group", required=True, help="CLI 子命令组名")
    parser.add_argument("--cli-command", required=True, help="CLI 命令名")
    parser.add_argument("--spec-path", default="", help="SDD spec 文件路径")
    parser.add_argument(
        "--dashboard-group",
        default="",
        help="Admin 看板 group_id，如 market_trade_date",
    )
    parser.add_argument("--column-key", default="", help="看板列 key，默认 table_name")
    parser.add_argument("--column-label", default="", help="看板列中文 label")
    parser.add_argument(
        "--sse-task-key",
        default="",
        help="SSE task_key，默认 {table_name}_check",
    )
    parser.add_argument(
        "--source-name",
        default="",
        help="completeness_snapshot.source_name，默认 table_name",
    )
    parser.add_argument(
        "--emit-checklist",
        action="store_true",
        help="额外打印 checklists/*.md 内容",
    )

    args = parser.parse_args()

    conflict_keys = [k.strip() for k in args.conflict_keys.split(",") if k.strip()]
    input_fields = parse_field_list(args.input_fields)
    output_fields = parse_field_list(args.output_fields)
    has_transform = args.has_transform.lower() in ("true", "1", "yes")
    has_completeness = args.has_completeness.lower() in ("true", "1", "yes")

    gen = SkeletonGenerator(
        api_name=args.api_name,
        domain=args.domain,
        domain_dir=args.domain_dir,
        table_name=args.table_name,
        pull_mode=args.pull_mode,
        conflict_keys=conflict_keys,
        input_fields=input_fields,
        output_fields=output_fields,
        rate_limit=args.rate_limit,
        has_transform=has_transform,
        has_completeness=has_completeness,
        cli_group=args.cli_group,
        cli_command=args.cli_command,
        spec_path=args.spec_path,
        dashboard_group=args.dashboard_group,
        column_key=args.column_key,
        column_label=args.column_label,
        sse_task_key=args.sse_task_key,
        source_name=args.source_name,
    )
    gen.generate_all()
    if args.emit_checklist:
        gen._emit_checklist()


if __name__ == "__main__":
    main()
