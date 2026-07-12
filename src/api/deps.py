from typing import Annotated

from fastapi import Header


async def verify_api_token(
    authorization: Annotated[str | None, Header()] = None,
    x_api_token: Annotated[str | None, Header(alias="X-API-Token")] = None,
) -> None:
    """
    API 鉴权占位：后续可校验 Bearer / X-API-Token 与环境变量等。
    """
    # TODO: 校验 token，失败时 raise HTTPException(status_code=401, detail="...")
    _ = (authorization, x_api_token)
    return None
