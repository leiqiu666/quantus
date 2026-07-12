"""通达信 tq HTTP 代理 Schema。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TdxInvokeResponse(BaseModel):
    data: Any = Field(description="序列化后的 tq 函数返回值")


class TdxFunctionsResponse(BaseModel):
    functions: list[str] = Field(description="可通过 HTTP 调用的 tq 函数名列表")
