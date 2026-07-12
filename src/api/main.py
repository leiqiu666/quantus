"""
ASGI 入口：开发启动示例
  uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
或安装项目后：quantus-api
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers.admin import data_source, etl_sse, financial, kline, quant, scheduler, stock, tdx_quant
from src.api.services import scheduler_service, tdx_quant_service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    tdx_quant_service.startup()
    scheduler_service.startup()
    yield
    scheduler_service.shutdown()
    tdx_quant_service.shutdown()


app = FastAPI(title="Quantus API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(financial.router, prefix="/api/admin")
app.include_router(kline.router, prefix="/api/admin")
app.include_router(data_source.router, prefix="/api/admin")
app.include_router(etl_sse.router, prefix="/api/admin")
app.include_router(stock.router, prefix="/api/admin")
app.include_router(tdx_quant.router, prefix="/api/admin")
app.include_router(quant.router, prefix="/api/admin")
app.include_router(scheduler.router, prefix="/api/admin")


@app.get("/health")
def health() -> dict[str, str]:
    if not scheduler_service.is_enabled():
        scheduler = "disabled"
    elif scheduler_service.is_running():
        scheduler = "running"
    else:
        scheduler = "stopped"
    return {
        "status": "ok",
        "tdx_quant": "ready" if tdx_quant_service.is_ready() else ("disabled" if not tdx_quant_service.is_enabled() else "unavailable"),
        "scheduler": scheduler,
    }


def run() -> None:
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=False)
