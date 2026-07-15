# Quantus API · Admin 端点规格

> Admin 后台（`src/web/admin`）专用 API，前缀统一为 `/api/admin`。

## 端点清单

| 文档 | 方法 | 路径 | 响应类型 |
|------|------|------|----------|
| [健康检查](./健康检查.sdd.md) | GET | `/health` | JSON |
| [财报-三表历史入库-SSE](./财报-三表历史入库-SSE.sdd.md) | POST ×3 | `/api/admin/financial/report/{income\|balance\|cashflow}-history-init` | **SSE** |
| [财报-报告期列表](./财报-报告期列表.sdd.md) | POST | `/api/admin/financial/report/period-list` | JSON |
| [K线-日列表](./K线-日列表.sdd.md) | POST | `/api/admin/kline/daily/trade-date-list` | JSON |
| [股票-列表查询](./股票-列表查询.sdd.md) | GET | `/api/admin/stock/list` | JSON |
| [通达信-tq代理](./通达信-tq代理.sdd.md) | GET / POST | `/api/admin/tdx/{functions\|{function_name}}` | JSON |
| [因子-因子列表](./因子-因子列表.sdd.md) | GET | `/api/admin/quant/factor/list` | JSON（分页） |
| [因子-编辑与源码](./因子-编辑与源码.sdd.md) | GET/PUT | `/api/admin/quant/factor/{name}`、`.../source` | JSON |
| [因子-生成-SSE](./因子-生成-SSE.sdd.md) | POST | `/api/admin/etl/sse/run`（`factor_compute`） | **SSE** |
| [特征-特征列表](./特征-特征列表.sdd.md) | GET/POST/PUT | `/api/admin/quant/feature/*` | JSON |
| [回测-运行与结果](./回测-运行与结果.sdd.md) | POST SSE / GET | `/api/admin/etl/sse/run`（`backtest_run`）；`/api/admin/quant/backtest/runs` | SSE / JSON |
| [回测-因子组合](./回测-因子组合.sdd.md) | GET/POST/PUT/DELETE | `/api/admin/quant/factor-combo` | JSON |
| [回测-明细表](./回测-明细表.sdd.md) | GET | `/api/admin/quant/backtest/runs/{run_id}/tables` | JSON |
| [投研-因子截面与个股K线](./投研-因子截面与个股K线.sdd.md) | GET | `/api/admin/research/*` | JSON |
| [数据质量-看板](./数据质量-看板.sdd.md) | GET / POST | `/api/admin/data-source/{groups\|dashboard}` | JSON |
| [数据质量-总览](./数据质量-总览.sdd.md) | GET | `/api/admin/data-source/overview` | JSON |
| [ETL-补位-SSE](./ETL-补位-SSE.sdd.md) | POST | `/api/admin/etl/sse/run` | **SSE** |
| [调度-任务管理](./调度-任务管理.sdd.md) | GET/POST/PATCH/DELETE | `/api/admin/scheduler/*` | JSON |

## 对应 Router

| Router 文件 | 前缀 |
|-------------|------|
| [`src/api/routers/admin/financial.py`](../../../src/api/routers/admin/financial.py) | `/api/admin/financial` |
| [`src/api/routers/admin/kline.py`](../../../src/api/routers/admin/kline.py) | `/api/admin/kline` |
| [`src/api/routers/admin/stock.py`](../../../src/api/routers/admin/stock.py) | `/api/admin/stock` |
| [`src/api/routers/admin/tdx_quant.py`](../../../src/api/routers/admin/tdx_quant.py) | `/api/admin/tdx` |
| [`src/api/routers/admin/quant.py`](../../../src/api/routers/admin/quant.py) | `/api/admin/quant` |
| [`src/api/routers/admin/data_source.py`](../../../src/api/routers/admin/data_source.py) | `/api/admin/data-source` |
| [`src/api/routers/admin/etl_sse.py`](../../../src/api/routers/admin/etl_sse.py) | `/api/admin/etl` |
| [`src/api/routers/admin/scheduler.py`](../../../src/api/routers/admin/scheduler.py) | `/api/admin/scheduler` |

## 上游索引

通用规范 / 公共架构 / 鉴权 / SSE 机制见 [`../README.md`](../README.md)。
