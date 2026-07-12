---
name: admin_web_dev
deprecated: "量化数据源看板部分已迁入 vibe_tushare_fullstack；本 Skill 仅用于模式 B 与非看板 Admin 页"
description: |
  Admin 后台全栈开发（React + FastAPI），**不含**量化数据源宽表看板（那部分见 vibe_tushare_fullstack）。

  适用场景：
  - 模式 B：独立 ProTable 明细列表页（与看板列并列）
  - 调度系统 / 因子列表 / 其他非看板 CRUD 页
  - 在已有页面追加功能

  用法示例：
  - "给 dragon_tiger_inst 做逐条明细 Admin 列表页"（模式 B）
  - "调度任务编辑页加字段"
  - "/admin_web_dev 因子列表改筛选"

  量化数据源默认接入：请用 [`vibe_tushare_fullstack`](../vibe_tushare_fullstack/skill.md)
---

# Admin 全栈开发 Skill

> **量化数据源（6 张宽表 + SSE 补位）**：不要按本 Skill 新建列表页，请用 [`vibe_tushare_fullstack`](../vibe_tushare_fullstack/skill.md) Step 6 模式 A（只改 `completeness_dashboard_config` + `etl_sse_registry`）。

## 工具路径

- Skill 目录：`.claude/skills/admin_web_dev/`
- 前端规范：[`src/web/admin/CLAUDE.md`](../../src/web/admin/CLAUDE.md)
- API 规范：[`spec/api/API开发规范.sdd.md`](../../spec/api/API开发规范.sdd.md)
- 看板组件（模式 A 只读参考）：[`DataSourceDashboardTable`](../../src/web/admin/src/components/DataSourceDashboard/DataSourceDashboardTable.tsx)

## 模式 A vs 模式 B

| 模式 | 何时用 | 做法 |
|------|--------|------|
| **A · 看板列**（默认） | 新 Tushare 数据源完整性监控 | → **`vibe_tushare_fullstack` Step 6**，不改 routes |
| **B · 独立列表页** | 需逐条明细 ProTable、字段级搜索 | 本 Skill 下文流程 |

---

## 工作流程（模式 B · 独立 ProTable 页）

### Step 1: 确认需求

与用户确认：
- **数据源**：目标表名
- **页面类型**：表格搜索列表 / 表单 / 详情
- **搜索条件**：日期范围、股票代码等
- **是否需要 SSE 操作列**：长任务走 `useSseTask`
- **分页**：服务端分页 vs 客户端过滤

### Step 2: 后端 API（模式 ① 读）

- Schema：`src/api/schemas/<业务名>.py`
- Service：`src/service/<域>/*_service.py`（**不是** `src/api/services/`）
- Model：`src/model/<域>/*_model.py`
- Router：`src/api/routers/admin/<域>.py`，同步 `def`
- 挂载：`src/api/main.py` → `app.include_router(..., prefix="/api/admin")`

读操作参考：[`stock.py`](../../src/api/routers/admin/stock.py)、[`quant.py`](../../src/api/routers/admin/quant.py)

写库 / 长任务（模式 ②）：`async def` + `sse_streaming_response(Strategy.method, ...)`，复用 ETL Strategy；**禁止** sync router 直接写库。

### Step 3: 前端

- Types：`src/web/admin/src/types/<业务名>.ts`
- Service：`src/web/admin/src/services/<业务名>.ts`
- 页面：`src/web/admin/src/pages/<域>/<Name>/index.tsx` — ProTable
- 路由：[`routes.config.tsx`](../../src/web/admin/src/routes/routes.config.tsx) 注册（绝对 path、kebab-case）

规范见 [`src/web/admin/CLAUDE.md`](../../src/web/admin/CLAUDE.md) §6 新增页面 SOP。

### Step 4: SSE 操作列（可选）

- `useSseTask().startEtlTask({ taskKey, label, startDate, endDate })`
- `useEffect` 监听 SSE success → `actionRef.current?.reload()`
- task_key 须在 `etl_sse_registry` 已注册

参考：[`SseTaskManager`](../../src/web/admin/src/components/SseTask/SseTaskManager.tsx)

### Step 5: 验证与文档

```bash
quantus-api   # 或 uvicorn src.api.main:app --reload
cd src/web/admin && pnpm dev
```

- 更新 [`docs/开发进度.md`](../../docs/开发进度.md)
- 补 `spec/api/admin/*.sdd.md`（若无）
- 更新 [`spec/api/admin/README.md`](../../spec/api/admin/README.md) 索引

---

## 页面类型模板

### 1. ProTable + 服务端分页

- 搜索：日期 `valueType: 'date'`，`hideInTable: true`
- 分页：`trade_date_page_bounds` / `report_period_page_bounds`
- `request` → `{ data, success, total }`

### 2. ProTable + 客户端过滤

参考：[`FactorList`](../../src/web/admin/src/pages/quant/FactorList/index.tsx)

- 一次拉全量；`valueEnum` 筛选

### 3. 调度 / 配置类页

参考：[`scheduler/JobList`](../../src/web/admin/src/pages/scheduler/JobList/index.tsx)

---

## 回复规范

1. Step 1 后：汇总表名、模式 B 确认、搜索与分页方式
2. Step 2 后：后端文件清单 + API 路径
3. Step 3 后：前端文件清单 + 路由 path
4. 若用户其实要「看板监控」：立即转指 `vibe_tushare_fullstack`
