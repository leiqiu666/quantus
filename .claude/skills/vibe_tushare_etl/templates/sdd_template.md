# SDD · {{title}}

> **CLI 命令：** `{{cli_group}} {{cli_command}}`
> **交互菜单：** 【{{category_label}}】{{menu_label}}
> **源码入口：** `src/etl/cli.py`
> **Tushare 接口：** [{{api_name}}]({{tushare_doc_url}})

---

## 1. 概述

{{overview_text}}

> {{api_note}}

### 触发方式

```bash
# 默认区间
uv run ./src/etl/cli.py {{cli_group}} {{cli_command}}

{{#if has_date_params}}
# 自定义区间
uv run ./src/etl/cli.py {{cli_group}} {{cli_command}} --start-date {{default_start_date}} --end-date {{default_end_date}}
{{/if}}

# 交互菜单
uv run ./src/etl/cli.py
```

### 前置依赖

| 依赖 | 说明 |
|------|------|
| `TUSHARE_API_KEY` | Tushare Pro 鉴权 |
{{#each dependencies}}
| `{{this.name}}` | {{this.description}} |
{{/each}}

### CLI 参数

{{#if has_cli_params}}
| 选项 | 默认 | 说明 |
|------|------|------|
{{#each cli_params}}
| `{{this.option}}` | `{{this.default}}` | {{this.description}} |
{{/each}}
{{else}}
无。
{{/if}}

---

## 2. CLI 入口

| 项 | 值 |
|----|-----|
| Typer 子命令组 | `{{cli_group}}` |
| 命令名 | `{{cli_command}}` |
| 处理函数 | `{{handler_function}}()` |
| 菜单 key | `{{menu_key}}` |

```python
# src/etl/cli.py（示意）
{{cli_code_snippet}}
```

---

## 3. 分层架构

```
{{architecture_diagram}}
```

**新增源码骨架：**

| 路径 | 角色 |
|------|------|
{{#each source_files}}
| `{{this.path}}` | {{this.role}} |
{{/each}}

---

## 4. 完整调用流程图

### 4.1 模块调用链

```mermaid
{{flowchart}}
```

### 4.2 时序图

```mermaid
{{sequence_diagram}}
```

---

## 5. 逐步说明

| 步骤 | 位置 | 输入 | 处理 | 输出 / 副作用 |
|------|------|------|------|----------------|
{{#each steps}}
| {{this.step}} | {{this.location}} | {{this.input}} | {{this.processing}} | {{this.output}} |
{{/each}}

---

## 6. 数据与外部依赖

### 6.1 Tushare API

| 项 | 值 |
|----|-----|
| 接口 | `{{api_name}}` |
| Client | `src/etl/client/{{domain_dir}}/{{domain}}_tushare_client.py` |
| Token | `settings.tushare_api_key` ← `TUSHARE_API_KEY` |
| 限流 | {{rate_limit}}/min |

**接口输入参数：**

| 名称 | 类型 | 必选 | 说明 |
|------|------|------|------|
{{#each input_params}}
| {{this.name}} | {{this.type}} | {{this.required}} | {{this.description}} |
{{/each}}

**接口输出字段：**

| 名称 | 类型 | 说明 |
|------|------|------|
{{#each output_params}}
| {{this.name}} | {{this.type}} | {{this.description}} |
{{/each}}

**示例（doc）：**

```python
{{usage_example}}
```

### 6.2 数据库

| 项 | 值 |
|----|-----|
| 表名 | `{{table_name}}` |
| ORM | `{{entity_class_name}}`（`src/entities/data_entities/{{domain_dir}}/{{table_name}}_entities.py`） |
| 冲突键 | `({{conflict_keys_str}})` |
| Upsert | `bulk_upsert_postgresql(..., conflict_keys=[{{conflict_keys_list}}], fallback_on_error=True)` |

**ORM 字段：**

| 列 | 类型 | 说明 |
|----|------|------|
| `id` | Integer PK autoincrement | — |
{{#each entity_fields}}
| `{{this.name}}` | {{this.type}} | {{this.description}} |
{{/each}}

**索引：**

| 索引名 | 列 | 唯一 |
|--------|----|------|
| `idx_{{table_name}}_unique` | `({{conflict_keys_str}})` | UNIQUE |
{{#each additional_indexes}}
| `{{this.name}}` | `({{this.columns}})` | {{#if this.unique}}UNIQUE{{else}}—{{/if}} |
{{/each}}

{{#if has_null_normalization}}
**关于 NULL 与 ON CONFLICT：** {{null_normalization_note}}
{{/if}}

### 6.3 finalize 规则

| 列 | 规则 |
|----|------|
{{#each finalize_rules}}
| `{{this.column}}` | {{this.rule}} |
{{/each}}

---

## 7. 业务规则

{{#each business_rules}}
{{@index_1}}. **{{this.title}}：** {{this.description}}
{{/each}}

---

## 8. 日志与可观测性

| 机制 | 说明 |
|------|------|
| typer.echo | {{echo_description}} |
| print | {{print_description}} |
| tqdm | `{{tqdm_desc}}`，单位「{{tqdm_unit}}」，postfix `{{tqdm_postfix}}` |

---

## 9. 已知限制与实现备注

| 项 | 说明 |
|----|------|
{{#each known_limitations}}
| {{this.item}} | {{this.description}} |
{{/each}}

---

## 10. 相关命令

| 命令 | 关系 |
|------|------|
{{#each related_commands}}
| `{{this.command}}` | {{this.relationship}} |
{{/each}}

---

## 附录 · Call Stack

```
{{call_stack}}
```

{{#if has_env_vars}}
## 附录 · 环境变量新增项

| 变量 | 默认 | 用途 | 推荐 .env |
|------|------|------|-----------|
{{#each env_vars}}
| `{{this.name}}` | `{{this.default}}` | {{this.purpose}} | {{this.recommended}} |
{{/each}}

> 应同步更新 `src/common/setting.py` 与 `spec/etl/README.md` 环境依赖表。
{{/if}}
