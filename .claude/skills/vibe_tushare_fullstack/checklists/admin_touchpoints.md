# Admin 看板集成触点清单

> **默认路径**：不新建 ProTable 页，只改配置；列自动出现在「量化数据源 → 大类/维度」页与「数据总览」。

## 必改（模式 A · 看板列）

- [ ] [`src/service/etl/completeness_dashboard_config.py`](../../../src/service/etl/completeness_dashboard_config.py)
  - 在 Step 1 确定的 `group_id` 下追加 `DashboardColumn`
  - 字段：`key` / `label` / `threshold` / `sse_task_key` / `source_name` 或 `count_field`
- [ ] [`src/service/etl/etl_sse_registry.py`](../../../src/service/etl/etl_sse_registry.py)
  - 注册 `{sse_task_key}`：优先 `_run_check`；K 线维度用 `_run_kline_dim`；停复牌用 `_run_suspend_pull`
  - **禁止**长循环只发 `total: 1`；Strategy 须转发 `progress_queue`（见 skill Step 6 ⚠️）
- [ ] [`spec/api/admin/ETL-补位-SSE.sdd.md`](../../../spec/api/admin/ETL-补位-SSE.sdd.md) — task_key 表增一行

## 通常不改

- [ ] `src/web/admin/src/routes/routes.config.tsx` — 已有 6 张宽表页 + 数据总览
- [ ] 新建 `pages/dataSource/*Page.tsx` — **除非**用户明确要求模式 B

## 自验

1. `pnpm dev` → 量化数据源 → 对应大类页 → 新列可见
2. 列头 / 单元格「补位」→ SSE 日志成功
3. **表头整列补位**：进度条随 `第 i/N 步` 推进，勿卡在「共 1 步」；与终端 tqdm 步数一致
4. `/data-source/overview` → 分组卡片含新源缺口统计
5. 明细页 `?focus=date_key` 高亮（从总览跳转）
6. 同一区间重复点击 → 「有一个同样的任务已经正在进行中」

## 并发提醒

连续多点补位会并行 SSE，易触发 PG `too many clients`；自验时**单任务完成后再点下一个**。

## 可选（模式 B · 独立明细 ProTable）

见 [`admin_web_dev`](../admin_web_dev/skill.md)「模式 B」章节；与看板列并列，不替代看板列。

- [ ] `src/api/schemas/` + `src/api/routers/admin/`
- [ ] `src/web/admin/src/pages/` + `routes.config.tsx`
- [ ] `spec/api/admin/*.sdd.md`

## 文档

- [ ] [`docs/开发进度.md`](../../../docs/开发进度.md) — ETL CLI + Admin + API 表
- [ ] [`spec/etl/README.md`](../../../spec/etl/README.md) 索引（如有）
