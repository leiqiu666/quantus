# 看板列注册片段

> 添加到 [`src/service/etl/completeness_dashboard_config.py`](../../../src/service/etl/completeness_dashboard_config.py) 中对应 `group_id` 的 `columns` 元组末尾。

## 使用 completeness_snapshot（source_name）

适用于 by-date / by-period 宏观快照完整性：

```python
DashboardColumn(
    "{{column_key}}",
    "{{column_label}}",
    source_name="{{source_name}}",
    threshold=0.95,
    sse_task_key="{{sse_task_key}}",
),
```

## 使用 report_period_count 等 count_field

适用于已有 period 聚合表、条数在 snapshot 的 count 字段：

```python
DashboardColumn(
    "{{column_key}}",
    "{{column_label}}",
    count_field="{{column_key}}_count",
    threshold=0.95,
    sse_task_key="{{sse_task_key}}",
),
```

## 仅条数、不做比率（如停复牌）

```python
DashboardColumn(
    "{{column_key}}",
    "{{column_label}}",
    count_field="{{column_key}}_count",
    threshold=0.0,
    sse_task_key="{{sse_task_key}}",
),
```

## 占位符说明

| 占位符 | 示例 |
|--------|------|
| `group_id` | `market_trade_date` |
| `column_key` | `market_foo`（通常 = 域前缀表名或短 key） |
| `column_label` | Admin 列头中文 |
| `source_name` | `completeness_snapshot.source_name` |
| `sse_task_key` | `market_foo_check` |

`GROUP_DETAIL_PATHS` 已有 6 组映射，**新数据源一般无需改**。
