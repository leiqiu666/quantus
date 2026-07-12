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
from src.api.schemas.factor_meta import FactorMetaItem
from src.service.kline.factor_meta_query_service import FactorMetaQueryService
from src.service.quant.backtest_run_query_service import BacktestRunQueryService
from src.service.quant.factor_combo_service import FactorComboService

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
