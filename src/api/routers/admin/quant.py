"""量化交易 Router。"""

from typing import Annotated, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query

from src.api.deps import verify_api_token
from src.api.schemas.backtest import (
    BacktestRunDetail,
    BacktestRunListItem,
    BacktestTableResponse,
    FactorComboCreateRequest,
    FactorComboOut,
    FactorComboUpdateRequest,
)
from src.api.schemas.factor_meta import (
    FactorMetaItem,
    FactorMetaListResponse,
    FactorMetaUpdateRequest,
    FactorSourceResponse,
)
from src.api.schemas.feature_meta import (
    FeatureCoverageResponse,
    FeatureMetaCreateRequest,
    FeatureMetaItem,
    FeatureMetaListResponse,
    FeatureMetaUpdateRequest,
    FeatureSeedResponse,
)
from src.service.kline.factor_meta_admin_service import FactorMetaAdminService
from src.service.kline.factor_meta_query_service import FactorMetaQueryService
from src.service.kline.feature_meta_service import FeatureMetaService
from src.service.quant.backtest_run_query_service import BacktestRunQueryService
from src.service.quant.factor_combo_service import FactorComboService

router = APIRouter(
    prefix="/quant",
    tags=["量化交易"],
    dependencies=[Depends(verify_api_token)],
)


@router.get(
    "/factor/list",
    summary="因子列表（分页）",
    description="返回 factor_meta 分页列表，支持来源/分类/关键字筛选。",
    response_model=FactorMetaListResponse,
)
def get_factor_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=500),
    source: Optional[str] = Query(default=None, description="来源筛选：自研 / tushare"),
    category: Optional[str] = Query(default=None, description="分类筛选"),
    keyword: Optional[str] = Query(default=None, description="名称关键字"),
) -> FactorMetaListResponse:
    data = FactorMetaQueryService().list_factors(
        page=page,
        page_size=page_size,
        source=source,
        category=category,
        keyword=keyword,
    )
    return FactorMetaListResponse(
        items=[FactorMetaItem.model_validate(x) for x in data["items"]],
        total=data["total"],
    )


@router.get(
    "/factor/{factor_name}/source",
    summary="Python 因子源码（只读）",
    response_model=FactorSourceResponse,
)
def get_factor_source(
    factor_name: Annotated[str, Path(min_length=1)],
) -> FactorSourceResponse:
    try:
        item = FactorMetaAdminService().read_source(factor_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return FactorSourceResponse.model_validate(item)


@router.get(
    "/factor/{factor_name}",
    summary="因子详情",
    response_model=FactorMetaItem,
)
def get_factor_detail(
    factor_name: Annotated[str, Path(min_length=1)],
) -> FactorMetaItem:
    item = FactorMetaAdminService().get_factor(factor_name)
    if item is None:
        raise HTTPException(status_code=404, detail=f"因子不存在: {factor_name}")
    return FactorMetaItem.model_validate(item)


@router.put(
    "/factor/{factor_name}",
    summary="更新因子元数据 / 公式",
    response_model=FactorMetaItem,
)
def update_factor_meta(
    factor_name: Annotated[str, Path(min_length=1)],
    body: Annotated[FactorMetaUpdateRequest, Body()],
) -> FactorMetaItem:
    try:
        item = FactorMetaAdminService().update_factor(
            factor_name, body.model_dump(exclude_unset=True)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return FactorMetaItem.model_validate(item)


@router.get(
    "/feature/list",
    summary="特征目录列表（分页）",
    response_model=FeatureMetaListResponse,
)
def get_feature_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    keyword: Optional[str] = Query(default=None),
    feature_kind: Optional[str] = Query(default=None),
    source_kind: Optional[str] = Query(default=None),
    enabled: Optional[int] = Query(default=None, ge=0, le=1),
) -> FeatureMetaListResponse:
    data = FeatureMetaService().list_features(
        page=page,
        page_size=page_size,
        keyword=keyword,
        feature_kind=feature_kind,
        source_kind=source_kind,
        enabled=enabled,
    )
    return FeatureMetaListResponse(
        items=[FeatureMetaItem.model_validate(x) for x in data["items"]],
        total=data["total"],
    )


@router.post(
    "/feature/seed",
    summary="初始化国泰 panel 特征种子",
    response_model=FeatureSeedResponse,
)
def seed_features() -> FeatureSeedResponse:
    return FeatureSeedResponse.model_validate(FeatureMetaService().seed_defaults())


@router.post(
    "/feature",
    summary="新建特征",
    response_model=FeatureMetaItem,
)
def create_feature(
    body: Annotated[FeatureMetaCreateRequest, Body()],
) -> FeatureMetaItem:
    try:
        item = FeatureMetaService().create_feature(body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return FeatureMetaItem.model_validate(item)


@router.post(
    "/feature/refresh-coverage",
    summary="刷新特征覆盖区间",
    response_model=FeatureCoverageResponse,
)
def refresh_feature_coverage() -> FeatureCoverageResponse:
    return FeatureCoverageResponse.model_validate(FeatureMetaService().refresh_coverage())


@router.put(
    "/feature/{feature_id}",
    summary="更新特征元数据",
    response_model=FeatureMetaItem,
)
def update_feature(
    feature_id: Annotated[int, Path(ge=1)],
    body: Annotated[FeatureMetaUpdateRequest, Body()],
) -> FeatureMetaItem:
    try:
        item = FeatureMetaService().update_feature(
            feature_id, body.model_dump(exclude_unset=True)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if item is None:
        raise HTTPException(status_code=404, detail=f"特征不存在: {feature_id}")
    return FeatureMetaItem.model_validate(item)


@router.get(
    "/factor-combo",
    summary="因子组合列表",
    response_model=list[FactorComboOut],
)
def list_factor_combos() -> list[FactorComboOut]:
    return [FactorComboOut.model_validate(x) for x in FactorComboService().list_combos()]


@router.post(
    "/factor-combo",
    summary="创建因子组合",
    response_model=FactorComboOut,
)
def create_factor_combo(
    body: Annotated[FactorComboCreateRequest, Body()],
) -> FactorComboOut:
    try:
        item = FactorComboService().create_combo(body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return FactorComboOut.model_validate(item)


@router.put(
    "/factor-combo/{combo_id}",
    summary="更新因子组合",
    response_model=FactorComboOut,
)
def update_factor_combo(
    combo_id: Annotated[int, Path(ge=1)],
    body: Annotated[FactorComboUpdateRequest, Body()],
) -> FactorComboOut:
    try:
        item = FactorComboService().update_combo(
            combo_id, body.model_dump(exclude_unset=True)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return FactorComboOut.model_validate(item)


@router.delete(
    "/factor-combo/{combo_id}",
    summary="删除因子组合",
)
def delete_factor_combo(combo_id: Annotated[int, Path(ge=1)]) -> dict:
    try:
        FactorComboService().delete_combo(combo_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True}


@router.get(
    "/backtest/runs",
    summary="回测历史列表",
    response_model=list[BacktestRunListItem],
)
def list_backtest_runs(
    limit: int = Query(default=50, ge=1, le=200),
) -> list[BacktestRunListItem]:
    items = BacktestRunQueryService().list_runs(limit=limit)
    return [BacktestRunListItem.model_validate(x) for x in items]


@router.get(
    "/backtest/runs/{run_id}",
    summary="回测运行详情",
    response_model=BacktestRunDetail,
)
def get_backtest_run(run_id: Annotated[str, Path(min_length=1)]) -> BacktestRunDetail:
    item = BacktestRunQueryService().get_run(run_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"run 不存在: {run_id}")
    return BacktestRunDetail.model_validate(item)


@router.get(
    "/backtest/runs/{run_id}/tables",
    summary="回测明细表",
    response_model=BacktestTableResponse,
)
def get_backtest_table(
    run_id: Annotated[str, Path(min_length=1)],
    name: Annotated[str, Query(description="portfolio | trades | returns")],
    trade_date: Optional[str] = Query(default=None),
    group_id: Optional[str] = Query(default=None),
    ts_code: Optional[str] = Query(default=None),
    limit: int = Query(default=5000, ge=1, le=20000),
) -> BacktestTableResponse:
    try:
        item = BacktestRunQueryService().get_table(
            run_id,
            name,
            trade_date=trade_date,
            group_id=group_id,
            ts_code=ts_code,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if item is None:
        raise HTTPException(status_code=404, detail=f"明细不存在: {run_id}/{name}")
    return BacktestTableResponse.model_validate(item)
