from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.api.deps import verify_api_token
from src.api.schemas.stock_list import StockListItem
from src.service.stock.stock_list_service import StockListService

router = APIRouter(
    prefix="/stock",
    tags=["stock"],
    dependencies=[Depends(verify_api_token)],
)


@router.get(
    "/list",
    summary="股票列表",
    description=(
        "返回 stock_list 表全字段列表。"
        "period：不传/空/0 不限制；“1” 表示截止今天在上市未退市；其它为 YYYYMMDD，表示该日在市。"
        "exchange（BSE/SSE/SZSE）等与 is_ggt、is_hs 为等值；is_hs 可传 Y/N 或 1/0。"
        "其余索引文本字段为模糊匹配（含 ts_code/name/market）；symbol 为股票代码，对应 ts_code 模糊。"
    ),
    response_model=list[StockListItem],
)
def get_stock_list(
    period: Annotated[
        str | None,
        Query(description="报告期/参考日：空或 0 不限；1=截止今天在上市未退市；否则 YYYYMMDD"),
    ] = None,
    ts_code: Annotated[
        str | None,
        Query(description="股票代码（模糊）"),
    ] = None,
    cnspell: Annotated[str | None, Query(description="拼音简称（模糊）")] = None,
    symbol: Annotated[
        str | None,
        Query(description="股票代码（/ts_code），模糊；与 ts_code 同时传则取交集"),
    ] = None,
    name: Annotated[str | None, Query(description="股票名称（模糊）")] = None,
    market: Annotated[
        str | None,
        Query(description="上市板（如主板、创业板、科创板、北交所等，模糊匹配 market 列）"),
    ] = None,
    exchange: Annotated[
        str | None,
        Query(description="交易所代码，等值：BSE / SSE / SZSE"),
    ] = None,
    shenwan_1: Annotated[str | None, Query(description="申万一级（模糊）")] = None,
    shenwan_2: Annotated[str | None, Query(description="申万二级（模糊）")] = None,
    shenwan_3: Annotated[str | None, Query(description="申万三级（模糊）")] = None,
    zhengjian_1: Annotated[str | None, Query(description="证监会一级（模糊）")] = None,
    zhengjian_2: Annotated[str | None, Query(description="证监会二级（模糊）")] = None,
    concept: Annotated[str | None, Query(description="概念（模糊）")] = None,
    area: Annotated[str | None, Query(description="地区（模糊）")] = None,
    city: Annotated[str | None, Query(description="城市（模糊）")] = None,
    country: Annotated[str | None, Query(description="国家（模糊）")] = None,
    is_ggt: Annotated[
        str | None,
        Query(description="是否港股通标的，等值，如 1 / 0"),
    ] = None,
    is_hs: Annotated[
        str | None,
        Query(description="是否沪深港通标的：Y/N 或 1/0"),
    ] = None,
) -> list[StockListItem]:
    rows = StockListService().get_stock_list(
        period=period,
        ts_code=ts_code,
        cnspell=cnspell,
        symbol=symbol,
        name=name,
        market=market,
        exchange=exchange,
        shenwan_1=shenwan_1,
        shenwan_2=shenwan_2,
        shenwan_3=shenwan_3,
        zhengjian_1=zhengjian_1,
        zhengjian_2=zhengjian_2,
        concept=concept,
        area=area,
        city=city,
        country=country,
        is_ggt=is_ggt,
        is_hs=is_hs,
    )
    # ORM 已加载 stock_list 全部列；API 层用 schema 序列化
    return [StockListItem.model_validate(r) for r in rows]
