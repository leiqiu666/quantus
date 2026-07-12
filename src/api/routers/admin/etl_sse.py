from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse

from src.api.deps import verify_api_token
from src.api.schemas.etl_sse import EtlSseRunRequest
from src.common.sse import sse_event_stream, SSE_HEADERS
from src.service.etl.etl_sse_registry import get_sse_task_runner, validate_sse_task_key

router = APIRouter(
    prefix="/etl",
    tags=["etl-sse"],
    dependencies=[Depends(verify_api_token)],
)

_SSE_DESC = (
    "通用 ETL 补位 SSE：task_key 映射 Strategy.check_complete / pull / report_history_init。"
    " report history init 类仅使用 start_date 作为报告期锚点。"
)


@router.post(
    "/sse/run",
    summary="ETL 补位任务（SSE）",
    description=_SSE_DESC,
)
async def run_etl_sse(
    body: Annotated[EtlSseRunRequest, Body()],
) -> StreamingResponse:
    try:
        validate_sse_task_key(body.task_key)
        runner = get_sse_task_runner(body.task_key)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    end = body.end_date or datetime.now().strftime("%Y%m%d")
    start = body.start_date

    def _worker(q):
        runner(start, end, q)

    return StreamingResponse(
        sse_event_stream(_worker, thread_name=f"etl_sse_{body.task_key}"),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
