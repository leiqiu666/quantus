"""量化交易 Router。"""

from fastapi import APIRouter, Depends, Query
from typing import Optional

from src.api.deps import verify_api_token
from src.api.schemas.factor_meta import FactorMetaItem
from src.service.kline.factor_meta_query_service import FactorMetaQueryService

router = APIRouter(
    prefix="/quant",
    tags=["量化交易"],
    dependencies=[Depends(verify_api_token)],
)


@router.get(
    "/factor/list",
    summary="因子列表",
    description="返回 factor_meta 表中所有因子，支持按来源和分类筛选。",
    response_model=list[FactorMetaItem],
)
def get_factor_list(
    source: Optional[str] = Query(default=None, description="来源筛选：自研 / tushare"),
    category: Optional[str] = Query(default=None, description="分类筛选：基本面 / 技术 等"),
) -> list[FactorMetaItem]:
    items = FactorMetaQueryService().list_factors(source=source, category=category)
    return [FactorMetaItem.model_validate(item) for item in items]
