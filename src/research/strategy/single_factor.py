"""单因子截面排序策略。"""

from __future__ import annotations

import polars as pl


class SingleFactorStrategy:
    """按因子值降序分 n_groups；组内等权。G0=最高分位。"""

    def __init__(self, factor_name: str, n_groups: int = 10) -> None:
        self.factor_name = factor_name
        self.n_groups = max(int(n_groups), 2)

    def target_weights(
        self,
        trade_date: str,
        factor_cs: pl.DataFrame,
        universe: list[str],
    ) -> dict[str, dict[str, float]]:
        """
        返回 group_id -> {ts_code: weight}，各组权重和为 1。
        group_id: G0 .. G{n-1}（G0 因子值最高）。
        """
        _ = trade_date
        uni = set(universe)
        if factor_cs.is_empty() or "ts_code" not in factor_cs.columns:
            return {f"G{i}": {} for i in range(self.n_groups)}

        value_col = "value" if "value" in factor_cs.columns else self.factor_name
        if value_col not in factor_cs.columns:
            return {f"G{i}": {} for i in range(self.n_groups)}

        df = (
            factor_cs
            .filter(pl.col("ts_code").is_in(list(uni)))
            .filter(pl.col(value_col).is_not_null())
            .select("ts_code", pl.col(value_col).alias("value"))
            .sort("value", descending=True)
        )
        n = df.height
        if n == 0:
            return {f"G{i}": {} for i in range(self.n_groups)}

        codes = df["ts_code"].to_list()
        # 尽量均分；前 remainder 组多 1 只
        base = n // self.n_groups
        rem = n % self.n_groups
        out: dict[str, dict[str, float]] = {}
        idx = 0
        for g in range(self.n_groups):
            size = base + (1 if g < rem else 0)
            chunk = codes[idx : idx + size]
            idx += size
            if not chunk:
                out[f"G{g}"] = {}
            else:
                w = 1.0 / len(chunk)
                out[f"G{g}"] = {c: w for c in chunk}
        return out
