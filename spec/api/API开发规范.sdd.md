# SDD · API 开发规范

> **适用：** 新增 HTTP 端点的通用规范。**只**覆盖两种主流模式 —— ① **Service 读**（同步 JSON）与 ② **ETL Strategy + SSE 写**（长任务）。
> **不在本规范内：** API 本地代理类（如 `tdx_quant`，把请求反射到外部进程），属特例，单独写 endpoint spec 即可。
> **入口：** [`src/api/main.py`](../../src/api/main.py)；公共索引：[`spec/api/README.md`](./README.md)。

---

## 1. 两种模式速判

| 维度 | ① Service 读 | ② ETL Strategy + SSE 写 |
|------|--------------|-------------------------|
| 用途 | 只读查询，秒级返回 | 拉外部数据 + 写库，分钟/小时级 |
| 路由签名 | `def`（同步，跑在线程池） | `async def`，返回 `StreamingResponse` |
| 调用层 | `src/service/<域>/*_service.py` | `src/etl/strategy/<域>/*_strategy.py`（直接复用 CLI 用的 Strategy 方法） |
| 返回类型 | `BaseModel` 或 `list[BaseModel]` + `response_model=` | `StreamingResponse(media_type="text/event-stream")` |
| 进度反馈 | 无 | 通过 `progress_queue` 推 JSON 帧 |
| 鉴权 | `verify_api_token`（router 级 dependency） | 同左 |
| 失败处理 | `raise HTTPException` | 异常自动被 SSE 包装层转成 `{"error": ...}` 帧 |
| 现有示例 | `report/period-list`、`kline/daily/trade-date-list`、`stock/list` | `report/{income\|balance\|cashflow}-history-init` |

**决策规则：**

1. 如果请求是「读 PG / 算几个聚合数」秒级能返回 → ①
2. 如果会调 Tushare / tdx_quant / 写 PG / 耗时 ≥10 秒 → ②，**不要**用 ① 同步等
3. 如果是反射代理外部进程 → 不在本规范，参考 [`通达信-tq代理.sdd.md`](./admin/通达信-tq代理.sdd.md)

> 同步路由内**不要**调 ETL Strategy 的写库方法。这会占住 FastAPI 的线程池，并且 SSE 才是给前端进度条用的正确通道。

---

## 2. 公共约定（两种模式都遵守）

### 2.1 文件位置

| 内容 | 位置 | 命名 |
|------|------|------|
| Router | `src/api/routers/<客户端>/<域>.py` | `<客户端>` 按受众分：`admin`（管理后台）/ `client`（toC，未来）；`<域>.py` 如 `financial.py`、`kline.py` |
| 请求/响应 schema | `src/api/schemas/<具体>.py` | 按业务名而非按 router 名（如 `financial_report.py`、`kline_daily.py`） |
| 业务 Service（**跨模块共享**） | `src/service/<域>/<域>_<对象>_service.py` | 与 ETL 共享 |
| API 专属辅助层 | `src/api/services/*.py` | 仅 router 自己用（如 `tdx_quant_service`） |

> **`src/service/*` vs `src/api/services/*` 别混：** 前者是领域 Service，ETL / CLI / API 都能调；后者是 router 私有胶水层。新增普通业务读 → 写 `src/service/`，不要塞 `src/api/services/`。

### 2.2 路由挂载

- 业务 router 按客户端分组，统一在 [`main.py`](../../src/api/main.py) 用 `app.include_router(<router>, prefix="/api/<客户端>")` 挂载；当前仅 `admin` 一组，prefix 为 `/api/admin`，未来 toC 用 `/api/v1`
- Router 自身再加 `prefix="/<域>"`、`tags=["<域>"]`、`dependencies=[Depends(verify_api_token)]`
- `/health` 是唯一不走客户端前缀、不鉴权的例外
- 新增 router → 在 `main.py` 加 `app.include_router(...)`

### 2.3 鉴权

```python
router = APIRouter(
    prefix="/<域>",
    tags=["<域>"],
    dependencies=[Depends(verify_api_token)],
)
```

[`verify_api_token`](../../src/api/deps.py) 当前是**占位实现**（不真校验）。新增接口默认挂上，未来补真鉴权时**不需要**改业务代码。

### 2.4 OpenAPI 文档字段

| 字段 | 必填？ | 说明 |
|------|--------|------|
| `summary` | 是 | 短句，≤20 字，能从 Swagger 列表一眼看出做什么 |
| `description` | 是 | 写清「参数默认值、分页语义、与 ETL 的关系、易错点」；中文 |
| `response_model` | ①必填 / ②不填 | ② 走 SSE 流，FastAPI 的 `response_model` 不适用 |
| `Body(..., default_factory=...)` | 当请求体可省略时 | 允许调用方传 `{}` 或不传 body |

### 2.5 错误处理

- 业务校验错误：`raise HTTPException(status_code=400, detail="...")`
- 鉴权不通过：`raise HTTPException(status_code=401, ...)`（占位实现暂时不做）
- 外部依赖缺失（如 `TDX_QUANT_ENABLED=false`）：`503`
- **不要**自定义全局异常拦截器、不要写中间件吞错；让异常正常往上抛
- SSE 模式下错误由 `sse_event_stream` 兜底转 `{"error": str(e)}` 帧，不要在 router 里手动 try

---

## 3. 模式 ① · Service 读（同步 JSON）

### 3.1 分层

```
Router (def)
  └─ src/service/<域>/<对象>_service.py        ← 领域 Service（跨模块共享）
       └─ src/model/<域>/<对象>_model.py        ← SQLAlchemy 查询
            └─ PostgreSQL
```

**约束：**

- Router 函数用 **`def`**（非 `async def`）—— FastAPI 自动跑在线程池，能调同步 SQLAlchemy
- Router 不直接读 Model、不直接读 DB；中间必须经 Service
- Service 是**无状态的薄封装**：参数 → Model 调用 → 转 dict/Pydantic；不要把分页/区间默认值塞 Service，那是 router 的活
- Service 方法**返回 `list[dict]` 或领域对象**，由 router 用 schema 序列化

### 3.2 请求 schema

- 字段命名跟 DB 列名对齐（`start_period_date`、`trade_date`），避免在 router 里再 alias
- 日期一律 `YYYYMMDD` 字符串，加 `pattern=r"^\d{8}$"`
- 范围参数加 `@model_validator(mode="after")` 校验 `start <= end`
- 分页：`page: int = Field(default=1, ge=1)` + `count: int = Field(default=50, ge=1, le=500)`

### 3.3 响应 schema

- `class XxxItem(BaseModel)` 描述单行；每个字段都写 `Field(description=...)`
- 列表响应直接 `response_model=list[XxxItem]`；带 total 的分页响应单独建 `XxxListResponse { items, total }`
- ORM 对象 → schema：`XxxItem.model_validate(row)` 或 Service 直接返回 dict

### 3.4 分页公共工具

| 工具 | 用途 |
|------|------|
| [`trade_date_page_bounds`](../../src/common/function.py) | 按 SSE 开市日序列分页（第 1 页 = 最新一页） |
| [`report_period_page_bounds`](../../src/common/function.py) | 按季度末序列分页 |

**典型调用：**

```python
start_bound = body.start_date or _default_start_date()
end_bound = body.end_date or datetime.now().strftime("%Y%m%d")

bounds = trade_date_page_bounds(start_bound, end_bound, body.page, body.count)
if bounds is None:
    return XxxListResponse(items=[], total=0)
window_lo, window_hi = bounds

items = XxxService().get_xxx(start_date=window_lo, end_date=window_hi)
```

**total 语义：** 区间内**总开市日数 / 总报告期数**（不是 items 长度），供前端分页器。

### 3.5 完整示例

```python
# src/api/schemas/widget.py
class WidgetItem(BaseModel):
    trade_date: str = Field(description="开市日 YYYYMMDD")
    foo_count: int = Field(description="...")

class WidgetListRequest(BaseModel):
    start_date: str | None = Field(default=None, pattern=r"^\d{8}$", description="...")
    end_date: str | None = Field(default=None, pattern=r"^\d{8}$", description="...")
    page: int = Field(default=1, ge=1)
    count: int = Field(default=50, ge=1, le=500)

class WidgetListResponse(BaseModel):
    items: list[WidgetItem]
    total: int

# src/api/routers/widget.py
@router.post(
    "/list",
    summary="...",
    description="...",
    response_model=WidgetListResponse,
)
def list_widgets(
    body: Annotated[
        WidgetListRequest,
        Body(default_factory=WidgetListRequest, description="..."),
    ],
) -> WidgetListResponse:
    """同步路由：FastAPI 在线程池中执行。"""
    start_bound = body.start_date or "19900101"
    end_bound = body.end_date or datetime.now().strftime("%Y%m%d")
    bounds = trade_date_page_bounds(start_bound, end_bound, body.page, body.count)
    if bounds is None:
        return WidgetListResponse(items=[], total=0)
    items = WidgetService().list_widgets(*bounds)
    return WidgetListResponse(items=items, total=...)
```

---

## 4. 模式 ② · ETL Strategy + SSE 写（长任务）

### 4.1 分层

```
Router (async def)
  └─ sse_streaming_response(Strategy.method, *args, thread_name=...)
       └─ 后台 daemon 线程 → ETL Strategy.method(progress_queue=q)
            └─ Workflow → Extract / Transform / Load → PG
       └─ 主协程从 queue 异步轮询 → yield "data: <json>\n\n"
```

**关键约束：**

- Router 用 **`async def`**（必须）—— 内部不要 `await` 任何重活，只是把请求交给 `sse_streaming_response`
- **直接复用 ETL Strategy 的现有方法**，不要为 API 重写一份；Strategy 方法需要遵守「`progress_queue` 协议」（见 4.3）
- `sse_streaming_response` 来自 [`src/common/sse.py`](../../src/common/sse.py)，**不要**自己写线程/队列/yield 模板
- 起 `thread_name=` 便于排查
- **不要**用 `await asyncio.to_thread(q.get)`：阻塞读不可取消，断连后占线程池，几个请求就把所有 `to_thread` 饿死（注释见 `sse.py` 顶部）

### 4.2 路由示例

```python
@router.post(
    "/foo/init",
    summary="Foo 全量入库（SSE）",
    description=_SSE_DESC_COMMON + " 后台线程执行 strategy.foo_init；契约见 src.api.schemas.foo 中 FooInitStream*。",
    # 注意：SSE 不写 response_model
)
async def foo_init(
    body: Annotated[
        FooInitRequest,
        Body(default_factory=FooInitRequest, description="..."),
    ],
) -> StreamingResponse:
    return sse_streaming_response(
        FooStrategy().foo_init,
        body.start_date,
        thread_name="foo_init",
    )
```

### 4.3 Strategy 端 `progress_queue` 协议

ETL Strategy 方法签名固定形如：

```python
def foo_init(
    self,
    start_date: str | None = None,
    *,
    progress_queue: Queue | None = None,
) -> SomeReturn:
    ...
    if progress_queue is not None:
        progress_queue.put({"status": "running", "total": total})

    for i, item in enumerate(items, start=1):
        saved = do_one(item)
        if progress_queue is not None:
            progress_queue.put({"index": i, "total": total, "item": ..., "saved": saved})

    if progress_queue is not None:
        progress_queue.put({"done": True, ...})
    return ...
```

**协议要点：**

| 帧类型 | 形状 | 必须？ |
|--------|------|--------|
| running | `{"status": "running", "total": N}` | 有总数后立刻推（让前端进度条出现） |
| 进度 | `{"index": int, "total": int, ...}` | 每个最小工作单元完成后推 |
| 结束 | `{"done": True, ...}` | **必须**（消费方靠它知道流结束） |
| 错误 | `{"error": "..."}` | **不要**自己推；让异常往上抛，SSE 包装层会兜底 |

`{"status": "started"}` 首帧由 `sse_event_stream` 自动推，**不要** Strategy 自己推。

**CLI 路径不传 `progress_queue`，所有 put 都跳过；同一份 Strategy 给 CLI + API 复用。**

### 4.4 SSE 帧 schema

为前端 / OpenAPI 文档保留契约，建议在 `src/api/schemas/<具体>.py` 里建：

```python
class FooInitStreamStarted(BaseModel):
    status: Literal["started"] = "started"

class FooInitStreamRunning(BaseModel):
    status: Literal["running"] = "running"
    total: int

class FooInitStreamProgress(BaseModel):
    index: int
    total: int
    item: str
    saved: int

class FooInitStreamFinal(BaseModel):
    done: Literal[True] = True
    items: list[...]

class FooInitStreamError(BaseModel):
    error: str
```

这些 schema **不**绑到 `response_model`（SSE 不走 pydantic 序列化），仅作文档与前端 TS 类型来源。

### 4.5 客户端 / 代理注意

- 浏览器 `fetch` + `ReadableStream` 解析；Admin 已统一封装 `@/components/SseTask` + `sseTask` slice，新接入复用
- 调试用 `curl -N <url>`（`-N` 关闭缓冲）
- 部署在 Nginx 后必须 `proxy_buffering off`、放宽 `proxy_read_timeout`；`X-Accel-Buffering: no` 已由 `sse.py` 自动加
- 任务可能极长（财报全量 30min+），前端要做"会话断了重连"的引导（**目前无服务端续传**，断了就重头来）

---

## 5. 新增 API 的 SOP

1. **先写 spec**：在 `spec/api/<客户端>/<功能>.sdd.md`（`<客户端>` 为 `admin` 或 `client`）里描述路径、参数、返回、与 ETL/Service 的关系；对齐后再动代码
2. **建 schema**：`src/api/schemas/<具体>.py`
   - ① 模式：Request + Item + （可选）ListResponse
   - ② 模式：Request + 一套 `*StreamStarted/Running/Progress/Final/Error`
3. **建 / 复用 Service 或 Strategy**
   - ① 模式：新建 `src/service/<域>/<对象>_service.py`，方法返回 `list[dict]` / 领域对象
   - ② 模式：复用 ETL Strategy 方法，确认它支持 `progress_queue` 参数；不支持就在 Strategy 里加（CLI 不传时无副作用）
4. **建 router**：`src/api/routers/<客户端>/<域>.py`，按模式 ①/② 模板写
5. **挂载**：若是新 router，在 `src/api/main.py` `app.include_router(...)` 时使用 `/api/<客户端>` 前缀
6. **更新文档**
   - 对应客户端子目录的 `spec/api/<客户端>/README.md` 索引表加一行
   - [`docs/开发进度.md`](../../docs/开发进度.md) HTTP API 表加一行
7. **自验**：本地起 `quantus-api`，`/docs` 看 OpenAPI；②模式用 `curl -N` 至少看到 `started → running → done` 流

---

## 6. 反模式（不要做）

| 反模式 | 为什么 |
|--------|--------|
| 同步 router 里直接调 ETL 写库方法 | 占线程池、前端没进度、可能超时；用 SSE |
| `async def` router 里同步调 SQLAlchemy | 阻塞事件循环；要么用 `def`，要么真异步 |
| 自己 `await asyncio.to_thread(q.get)` | 断连后占线程池，详见 [`sse.py`](../../src/common/sse.py) 顶部注释 |
| Service 里塞默认日期 / 分页 / 鉴权 | Service 给 ETL 也用；这些是 router 的职责 |
| 业务 service 放进 `src/api/services/` | 那是 router 私有胶水层；领域 service 放 `src/service/` |
| 跳过 `verify_api_token` | 占位归占位，留好接入点 |
| SSE worker 内自己 `try/except` 转 `{"error":...}` 入队 | 包装层已经做了，重复做反而吞了堆栈 |
| 不写 `description` / `summary` | `/docs` 就成了一坨没法读 |

---

## 7. 公共材料速查

| 项 | 文件 / 工具 |
|----|------------|
| FastAPI 入口 | [`src/api/main.py`](../../src/api/main.py) |
| 鉴权 | [`src/api/deps.py`](../../src/api/deps.py) `verify_api_token` |
| SSE 包装 | [`src/common/sse.py`](../../src/common/sse.py) `sse_streaming_response` |
| 分页（开市日） | [`src/common/function.py`](../../src/common/function.py) `trade_date_page_bounds` |
| 分页（报告期） | [`src/common/function.py`](../../src/common/function.py) `report_period_page_bounds` |
| 模式 ① 参考实现 | [`财报-报告期列表.sdd.md`](./财报-报告期列表.sdd.md)、[`K线-日列表.sdd.md`](./K线-日列表.sdd.md) |
| 模式 ② 参考实现 | [`财报-三表历史入库-SSE.sdd.md`](./财报-三表历史入库-SSE.sdd.md) |
| 特例（代理类） | [`通达信-tq代理.sdd.md`](./通达信-tq代理.sdd.md) |
