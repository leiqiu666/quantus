"""国泰 191 公式目录：解析 docs/国泰191.md。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_DOC = Path(__file__).resolve().parents[4] / "docs" / "国泰191.md"

# 需 Fama-French，本期不算值
NEEDS_FF: frozenset[int] = frozenset({30})

# 需基准指数日线
NEEDS_BENCHMARK: frozenset[int] = frozenset({75, 149, 181, 182})

# 递推 SELF
NEEDS_SELF: frozenset[int] = frozenset({143})

_TYPO_FIXES: list[tuple[str, str]] = [
    ("HGIH", "HIGH"),
    ("DELAT", "DELTA"),
    ("SMEAN", "SMA"),
    # Alpha23 首段三元误写为逗号
    ("?STD(CLOSE:20),0)", "?STD(CLOSE,20):0)"),
    ("，", ","),
    ("（", "("),
    ("）", ")"),
    ("./.", "/"),
    ("./", "/"),
    (".*", "*"),
    ("||", " or "),
    ("&&", " and "),
    ("&", " and "),
]


@dataclass(frozen=True)
class GtjaAlphaSpec:
    n: int
    name: str
    formula_raw: str
    formula_eval: str
    needs_ff: bool
    needs_benchmark: bool
    needs_self: bool
    skip_compute: bool
    skip_reason: str = ""


def _normalize_formula(raw: str) -> str:
    s = raw.strip()
    for a, b in _TYPO_FIXES:
        s = s.replace(a, b)
    # 三元 ?: → Python 条件表达式较难通用转换，保留给引擎二次处理
    # 幂运算 ^ → **（避免与异或混淆：国泰公式中 ^ 均为幂）
    s = re.sub(r"\^", "**", s)
    return s


def _parse_doc(text: str) -> dict[int, str]:
    out: dict[int, str] = {}
    for m in re.finditer(
        r"Alpha(\d+)\s*:\s*(.+?)(?=\n\s*Alpha\d+\s*:|\Z)",
        text,
        flags=re.S,
    ):
        n = int(m.group(1))
        formula = " ".join(m.group(2).split())
        out[n] = formula
    return out


@lru_cache(maxsize=1)
def load_catalog() -> dict[int, GtjaAlphaSpec]:
    if not _DOC.exists():
        raise FileNotFoundError(f"缺少国泰191公式文件: {_DOC}")
    raw_map = _parse_doc(_DOC.read_text(encoding="utf-8"))
    catalog: dict[int, GtjaAlphaSpec] = {}
    for n in range(1, 192):
        raw = raw_map.get(n, "")
        needs_ff = n in NEEDS_FF
        needs_bm = n in NEEDS_BENCHMARK
        needs_self = n in NEEDS_SELF
        skip = needs_ff or not raw
        reason = ""
        if needs_ff:
            reason = "依赖 MKT/SMB/HML，本期跳过计算"
        elif not raw:
            reason = "公式缺失"
        catalog[n] = GtjaAlphaSpec(
            n=n,
            name=f"gtja_alpha{n}",
            formula_raw=raw,
            formula_eval=_normalize_formula(raw) if raw else "",
            needs_ff=needs_ff,
            needs_benchmark=needs_bm,
            needs_self=needs_self,
            skip_compute=skip,
            skip_reason=reason,
        )
    return catalog


def list_computable_alphas(alpha: int | None = None) -> list[GtjaAlphaSpec]:
    cat = load_catalog()
    if alpha is not None:
        spec = cat[alpha]
        return [] if spec.skip_compute else [spec]
    return [s for s in cat.values() if not s.skip_compute]


def factor_name(n: int) -> str:
    return f"gtja_alpha{n}"


def _strip_meta_skip_suffix(formula: str) -> str:
    s = (formula or "").strip()
    if "｜[" in s:
        return s.split("｜[", 1)[0].strip()
    return s


def overlay_db_formulas(specs: list[GtjaAlphaSpec]) -> list[GtjaAlphaSpec]:
    """用 factor_meta.formula 覆盖文档公式（Admin 编辑生效）。"""
    try:
        from src.model.kline.factor_meta_model import FactorMetaModel

        fmap = FactorMetaModel().list_formula_map()
    except Exception:
        return specs
    if not fmap:
        return specs
    out: list[GtjaAlphaSpec] = []
    for s in specs:
        raw = _strip_meta_skip_suffix(fmap.get(s.name, ""))
        if not raw or raw == s.formula_raw:
            out.append(s)
            continue
        out.append(
            GtjaAlphaSpec(
                n=s.n,
                name=s.name,
                formula_raw=raw,
                formula_eval=_normalize_formula(raw),
                needs_ff=s.needs_ff,
                needs_benchmark=s.needs_benchmark,
                needs_self=s.needs_self,
                skip_compute=s.skip_compute,
                skip_reason=s.skip_reason,
            )
        )
    return out
