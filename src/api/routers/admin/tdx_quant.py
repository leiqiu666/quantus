"""通达信 tq HTTP 代理路由。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from src.api.deps import verify_api_token
from src.api.schemas.tdx_quant import TdxFunctionsResponse, TdxInvokeResponse
from src.api.services import tdx_quant_service

router = APIRouter(
    prefix="/tdx",
    tags=["tdx"],
    dependencies=[Depends(verify_api_token)],
)


@router.get(
    "/functions",
    summary="列出可代理的 tq 函数",
    response_model=TdxFunctionsResponse,
)
def list_tdx_functions() -> TdxFunctionsResponse:
    try:
        return TdxFunctionsResponse(functions=tdx_quant_service.list_functions())
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/{function_name}",
    summary="调用 tq 函数",
    description="POST body 为函数 kwargs，如 stock_list 传 JSON array。",
    response_model=TdxInvokeResponse,
)
def invoke_tdx_function(
    function_name: str,
    params: dict[str, Any] = Body(default_factory=dict),
) -> TdxInvokeResponse:
    try:
        data = tdx_quant_service.invoke(function_name, params)
        return TdxInvokeResponse(data=data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TypeError as exc:
        raise HTTPException(status_code=400, detail=f"参数错误: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
