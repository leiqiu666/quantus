# 财报 report_income 入库 load_report 性能分析

> 场景：`report_income_by_period(period="20260331")` 在服务器上总耗时 15–20s，本地约 2s。  
> 分段计时显示 `load_report` 占 ~11s，是主要瓶颈。  
> 分析日期：2026-05-26 · 环境：Quantus ETL 服务器（Docker PostgreSQL 18.3）

---

## 一、问题现象

终端分段输出（服务器）：

```text
[report_income_by_period] pull_report_income:        ~2.0s
[report_income_by_period] report_transform_merge_now: ~0.05s
[report_income_by_period] report_more_detail_to_json: ~1.7s
[report_income_by_period] load_report:               ~11.8s   ← 瓶颈
[report_income_by_period] total:                     ~15.8s
```

本地同一代码路径总耗时约 **2s**，`load_report` 明显更快。

---

## 二、调用链

```text
report_income_by_period
  └─ ReportLoad.load_report
       └─ dataframe_to_list(df)
       └─ Database.bulk_upsert_postgresql(ReportIncomeEntities, records)
            └─ INSERT ... ON CONFLICT DO UPDATE（按唯一键 upsert）
```

相关代码：

- 工作流：`src/etl/workflow/financial/report_workflow.py`
- 入库层：`src/etl/load/financial/report_load.py`
- 数据库层：`src/common/database.py` → `bulk_upsert_postgresql`

---

## 三、服务器实测数据

### 3.1 环境与表规模

| 项 | 值 |
|----|-----|
| PostgreSQL | 18.3（Docker `postgres:18.3-alpine`） |
| 连接 | `POSTGRESQL_HOST=localhost`（非远程连库） |
| 连接延迟 | ~2ms |
| `report_income` 行数 | ~255,000 |
| 表 + 索引总大小 | ~235 MB（堆表 ~152 MB） |
| 当期（20260331）行数 | ~5,500 |
| 索引数量 | **13 个**（含 11 个单列索引 + upsert 唯一键 + 主键） |

### 3.2 分段计时（5645 行，period=20260331）

| 阶段 | 耗时 | 占比 |
|------|------|------|
| `_check_field_lengths` | ~0.17s | 可忽略 |
| `_has_unique_constraint` | ~0.12s | 可忽略 |
| **`bulk_upsert_postgresql`（execute + commit）** | **~11–12s** | **>95%** |

### 3.3 排除项

| 假设 | 结论 |
|------|------|
| 远程数据库网络延迟 | ❌ 连 localhost，ping ~2ms |
| fallback 到逐条 `bulk_upsert` | ❌ 唯一索引 `idx_report_income_upsert_key` 存在，走批量 upsert |
| `income_table` JSONB 过大 | ❌ 抽样平均 ~286 字节，非主因 |
| 重复跑导致 UPDATE 比 INSERT 慢 | ❌ 见下文对照实验 |

---

## 四、根因：索引写放大

### 4.1 单行成本

| 批量规模 | 耗时 | 单行约 |
|----------|------|--------|
| 100 行 upsert | ~0.20s | ~2.0ms |
| 500 行 upsert | ~1.13s | ~2.3ms |
| 5645 行 upsert | ~11.4s | ~2.0ms |

**5500 行 × ~2ms/行 ≈ 11s**，与观测一致。

### 4.2 空表 vs 已有数据（关键对照）

在同结构空表 `report_income_bench`（`LIKE report_income INCLUDING ALL`）上测试：

| 场景 | 耗时 |
|------|------|
| 5645 行 **首次 INSERT**（空表） | ~10.9s |
| 5645 行 **再次 upsert**（全冲突 UPDATE） | ~11.6s |

**空表首次插入也要 ~11 秒**，说明瓶颈不是「表已有 25 万行所以 UPDATE 慢」，而是 **每行 upsert 都要维护 13 个 B-tree 索引**。

### 4.3 索引列表（按大小降序）

| 索引名 | 唯一 | 大小（约） |
|--------|------|------------|
| `idx_report_income_upsert_key` | ✓ | 20 MB |
| `idx_report_income_total_revenue` | | 8.5 MB |
| `idx_report_income_total_cogs` | | 8.5 MB |
| `idx_report_income_total_profit` | | 8.0 MB |
| `idx_report_income_operate_profit` | | 8.0 MB |
| `idx_report_income_n_income` | | 7.8 MB |
| `idx_report_income_rd_exp` | | 7.2 MB |
| `report_income_pkey` | ✓ | 6.1 MB |
| … 其余 5 个单列索引 | | 各 2–3 MB |

实体定义见 `src/entities/data_entities/report_income_entities.py` 的 `__table_args__`。

### 4.4 ON CONFLICT DO UPDATE 的写放大

`bulk_upsert_postgresql` 在冲突时对**除 conflict_keys 外的所有列**执行 `SET col = excluded.col`，包括 `income_table`（JSONB）。  
即使业务数据未变，PostgreSQL 仍可能触发索引页更新（取决于 HOT 等条件），在 **13 个索引** 下写入成本显著。

---

## 五、为何本地更快？

代码路径相同，本地总耗时 ~2s 通常来自以下差异（可叠加）：

1. **索引数量不一致（最常见）**  
   本地若只建了 PK + upsert 唯一键，写入会快一个数量级。对比命令：

   ```sql
   SELECT indexname, indexdef
   FROM pg_indexes
   WHERE tablename = 'report_income'
   ORDER BY indexname;
   ```

2. **磁盘与部署**  
   服务器 PG 跑在 Docker 内，数据卷在 VPS ext4 盘上；本地 NVMe + 原生 PG 安装，随机写通常快数倍。

3. **不是「重复跑所以更慢」**  
   服务器上 INSERT 与 RE-upsert 耗时接近，重复执行同一期不是根因。

---

## 六、优化建议（按收益排序）

### P0 · 精简写入热路径上的索引

- 评估 `report_income` 上 11 个单列索引是否都必须在 ETL 写入表上存在。
- 若仅服务分析查询，可考虑：写入表保留 PK + upsert 键；查询走物化视图或单独分析表。
- **预期**：减少 N 个索引 → 单行写入成本近似按比例下降。

### P1 · ETL 可信数据跳过长度检查

在 `ReportLoad.load_report` 传入 `skip_length_check=True`，可省 ~0.2s（边际收益，已实现参数支持）。

### P2 · 历史全量入库换路径

按期次批量历史初始化时，可考虑：

- `COPY` 批量导入 + 导入完成后一次性 `CREATE INDEX`
- 或临时 drop 非必要索引 → bulk load → rebuild index

详见 [bulk_upsert_postgresql性能深度分析.md](./bulk_upsert_postgresql性能深度分析.md) 第四节。

### P3 · PostgreSQL / Docker 调优

- 数据卷使用 SSD
- 适当增大 `shared_buffers`、`maintenance_work_mem`
- 批量入库期间可临时调大 `maintenance_work_mem` 以利于索引构建

### P4 · 驱动与批量执行

对 **远程连库** 场景，`executemany` round-trip 可能是主因；本案例为 **localhost + 索引写放大**，P4 收益有限。  
`skip_length_check` / `chunk_size` 在本案例实测几乎无改善（5645 行规模下 chunk 仍 ~11s）。

---

## 七、本地复现分段计时

在 workflow 中已有 print，或直接跑：

```bash
uv run src/etl/workflow/financial/report_workflow.py
```

对比本地与服务器各阶段秒数，并执行：

```sql
SELECT count(*) FROM pg_indexes WHERE tablename = 'report_income';
SELECT pg_size_pretty(pg_total_relation_size('report_income'));
```

---

## 八、结论

| 问题 | 答案 |
|------|------|
| 为什么服务器 `load_report` ~11s？ | ~5500 行 upsert，每行维护 **13 个索引**，约 **2ms/行** |
| 是网络吗？ | 否，localhost |
| 是走了慢的逐条 fallback 吗？ | 否，唯一索引存在，走 `ON CONFLICT DO UPDATE` |
| 是表太大 UPDATE 慢吗？ | 否，空表同结构 INSERT 也要 ~11s |
| 本地为什么快？ | 多为 **索引更少** 或 **磁盘更快** |

**一句话**：瓶颈在 PostgreSQL 索引写放大，而非 ETL 逻辑或网络。

---

## 相关文档

- [bulk_upsert_postgresql性能深度分析.md](./bulk_upsert_postgresql性能深度分析.md) — `bulk_upsert_postgresql` 通用瓶颈与参数说明
- `src/entities/data_entities/report_income_entities.py` — 索引定义
- `spec/etl/财报-三表全量历史入库.sdd.md` — 财报 ETL 流程规格
