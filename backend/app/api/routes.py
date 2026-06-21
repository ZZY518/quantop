from datetime import date, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.database import get_db
from app.core.constants import DEFAULT_ADJUST
from app.core.runtime_state import SUPPORTED_DATA_SOURCES, get_data_source, set_data_source
from app.models.bar import DwdStockBar
from app.models.bar_factor import FactorStockBar
from app.models.daily import DwdStockDaily
from app.models.factor import FactorStockDaily
from app.models.stock import StockBasic
from app.models.sync_log import SyncTaskLog
from app.schemas.bar import DwdStockBarRead, FactorStockBarRead, StockChartBarRead
from app.schemas.hot_rank import HotRankRead
from app.schemas.daily import DwdStockDailyRead, MarketRankRead
from app.schemas.factor import FactorRankRead, FactorStockDailyRead
from app.schemas.stock import StockBasicRead
from app.schemas.sync_log import SyncTaskLogRead
from app.data_sources.factory import DataSourceNotConfigured, DataSourceUnavailable
from app.services.hot_rank_service import hot_rank
from app.services.query_service import factor_rank, market_quotes, market_rank, recent_logs, stock_chart_bars
from app.services.sync_service import SyncService

router = APIRouter()


@router.post("/sync/run", response_model=SyncTaskLogRead)
def run_sync(
    background_tasks: BackgroundTasks,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    try:
        running_log = db.scalars(
            select(SyncTaskLog)
            .where(SyncTaskLog.task_name == "stock_daily_top_amount_with_indicators", SyncTaskLog.status == "running")
            .order_by(SyncTaskLog.start_time.desc())
            .limit(1)
        ).first()
        if running_log:
            return running_log

        data_source = get_data_source()
        if data_source == "none":
            raise DataSourceNotConfigured("No real data source is configured. Set QUANTOP_DATA_SOURCE before syncing.")
        log = SyncTaskLog(
            task_name="stock_daily_top_amount_with_indicators",
            source=data_source,
            biz_date=date.today(),
            status="running",
            start_time=datetime.utcnow(),
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        background_tasks.add_task(_run_stock_daily_top_amount_sync, log.id, limit)
        return log
    except DataSourceNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DataSourceUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _run_stock_daily_top_amount_sync(log_id: int, limit: int) -> None:
    db = SessionLocal()
    try:
        log = db.get(SyncTaskLog, log_id)
        if log is None:
            return
        SyncService(db).sync_stock_daily_top_amount(limit=limit, log=log)
    finally:
        db.close()


@router.get("/settings/data-source")
def get_runtime_data_source():
    return {"current": get_data_source(), "options": list(SUPPORTED_DATA_SOURCES)}


@router.post("/settings/data-source")
def update_runtime_data_source(source: str = Query(..., pattern="^(akshare|baostock)$")):
    try:
        return {"current": set_data_source(source), "options": list(SUPPORTED_DATA_SOURCES)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/stocks", response_model=list[StockBasicRead])
def list_stocks(db: Session = Depends(get_db)):
    return db.scalars(select(StockBasic).order_by(StockBasic.symbol)).all()


@router.get("/stocks/{symbol}", response_model=StockBasicRead)
def get_stock(symbol: str, db: Session = Depends(get_db)):
    stock = db.get(StockBasic, symbol)
    if not stock:
        raise HTTPException(status_code=404, detail="stock not found")
    return stock


@router.get("/stocks/{symbol}/daily", response_model=list[DwdStockDailyRead])
def get_stock_daily(
    symbol: str,
    limit: int = Query(default=120, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(DwdStockDaily)
        .where(DwdStockDaily.symbol == symbol, DwdStockDaily.adjust == DEFAULT_ADJUST)
        .order_by(DwdStockDaily.trade_date.desc())
        .limit(limit)
    ).all()
    return list(reversed(rows))


@router.get("/stocks/{symbol}/bars", response_model=list[DwdStockBarRead])
def get_stock_bars(
    symbol: str,
    period: str = Query(default="1d", pattern="^(1d|1w|1m)$"),
    limit: int = Query(default=240, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(DwdStockBar)
        .where(DwdStockBar.symbol == symbol, DwdStockBar.period == period, DwdStockBar.adjust == DEFAULT_ADJUST)
        .order_by(DwdStockBar.trade_date.desc())
        .limit(limit)
    ).all()
    return list(reversed(rows))


@router.get("/stocks/{symbol}/factors", response_model=list[FactorStockDailyRead])
def get_stock_factors(
    symbol: str,
    limit: int = Query(default=120, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(FactorStockDaily)
        .where(FactorStockDaily.symbol == symbol)
        .order_by(FactorStockDaily.trade_date.desc())
        .limit(limit)
    ).all()
    return list(reversed(rows))


@router.get("/stocks/{symbol}/bar-factors", response_model=list[FactorStockBarRead])
def get_stock_bar_factors(
    symbol: str,
    period: str = Query(default="1d", pattern="^(1d|1w|1m)$"),
    limit: int = Query(default=240, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(FactorStockBar)
        .where(FactorStockBar.symbol == symbol, FactorStockBar.period == period)
        .order_by(FactorStockBar.trade_date.desc())
        .limit(limit)
    ).all()
    return list(reversed(rows))


@router.get("/stocks/{symbol}/chart", response_model=list[StockChartBarRead])
def get_stock_chart(
    symbol: str,
    period: str = Query(default="1d", pattern="^(1d|1w|1m)$"),
    limit: int = Query(default=240, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    return stock_chart_bars(db, symbol=symbol, period=period, limit=limit)


@router.get("/market/rank", response_model=list[MarketRankRead] | list[FactorRankRead])
def get_market_rank(
    limit: int = Query(default=20, ge=1, le=500),
    rank_type: str = Query(default="pct_chg", pattern="^(pct_chg|score)$"),
    db: Session = Depends(get_db),
):
    if rank_type == "score":
        return factor_rank(db, limit)
    return market_rank(db, limit)


@router.get("/market/quotes", response_model=list[MarketRankRead])
def get_market_quotes(db: Session = Depends(get_db)):
    return market_quotes(db)


@router.get("/market/hot-rank", response_model=list[HotRankRead])
def get_market_hot_rank(limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)):
    try:
        return hot_rank(limit, db=db)
    except DataSourceUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/sync/logs", response_model=list[SyncTaskLogRead])
def get_sync_logs(limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)):
    return recent_logs(db, limit)


@router.get("/health")
def health():
    return {"status": "ok"}
