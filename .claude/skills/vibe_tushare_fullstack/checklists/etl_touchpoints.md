# ETL 必改触点清单

> 骨架生成后逐项勾选；`generate_skeleton.py --emit-checklist` 会输出带占位符的片段。

## 实体与配置

- [ ] `src/entities/data_entities/{domain_dir}/{table_name}_entities.py` — 建表
  ```bash
  uv run python -c "from src.common.database import sync_table; from src.entities... import X; sync_table(X, interactive=False)"
  ```
- [ ] `src/entities/client_entities/tushare_entities.py` — 追加 `{table_name}` 字段列表
- [ ] `src/common/setting.py` — `{table_name}_START_DATE` 或复用 `settings.etl_start_date("{table_name}")`
- [ ] `src/common/etl_start.py` — 表名映射（若 env 名与表名不一致）

## 8 层骨架（generate_skeleton 产出）

- [ ] `src/etl/client/{domain_dir}/{domain}_*.py`
- [ ] `src/etl/extract/{domain_dir}/{domain}_extract.py`
- [ ] `src/etl/extract/local/{domain_dir}/{domain}_extract.py`
- [ ] `src/etl/load/{domain_dir}/{domain}_load.py`
- [ ] `src/etl/workflow/{domain_dir}/{domain}_workflow.py`
- [ ] `src/etl/strategy/{domain_dir}/{domain}_strategy.py`
- [ ] `src/model/{domain_dir}/{domain}_model.py`（可选）
- [ ] `src/service/{domain_dir}/{domain}_service.py`（可选）
- [ ] `src/etl/transform/...`（若 has_transform）

## CLI

- [ ] `src/etl/cli.py` — `add_typer` + `pull-*` 子命令
- [ ] `src/etl/cli.py` — `check-complete` 子命令（若 has_completeness）
- [ ] `src/scheduler/command_registry.py` — 交互菜单 25 条之一（若需调度）

## 完整性（has_completeness=true）

- [ ] Strategy — `CompletenessConfig` + `CompletenessEngine`
- [ ] `source_name` 与看板列 `key` 或 `source_name` 一致
- [ ] `pull_by_date` / `pull_by_stock` 等 lambda 指向 Workflow
- [ ] `refresh_completeness_snapshot` 在 pull 区间结束后调用

## 自验

```bash
uv run ./src/etl/cli.py {cli_group} {cli_command} --start-date YYYYMMDD --end-date YYYYMMDD
uv run ./src/etl/cli.py {cli_group} check-complete --start-date YYYYMMDD --end-date YYYYMMDD
```
