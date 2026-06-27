from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.daily import DwdStockDaily
from app.models.bar import DwdStockBar
from app.models.bar_factor import FactorStockBar
from app.models.factor import FactorStockDaily
from app.models.stock import StockBasic
from app.models.sync_log import SyncTaskLog
from app.core.constants import DEFAULT_ADJUST


def latest_factor_subquery(db: Session):
    return (
        select(FactorStockDaily.symbol, func.max(FactorStockDaily.trade_date).label("trade_date"))
        .group_by(FactorStockDaily.symbol)
        .subquery()
    )


def market_rank(db: Session, limit: int = 20) -> list[dict]:
    latest = (
        select(DwdStockDaily.symbol, func.max(DwdStockDaily.trade_date).label("trade_date"))
        .where(DwdStockDaily.adjust == DEFAULT_ADJUST)
        .group_by(DwdStockDaily.symbol)
        .subquery()
    )
    rows = db.execute(
        select(DwdStockDaily, StockBasic.name)
        .join(latest, (DwdStockDaily.symbol == latest.c.symbol) & (DwdStockDaily.trade_date == latest.c.trade_date))
        .join(StockBasic, StockBasic.symbol == DwdStockDaily.symbol, isouter=True)
        .order_by(desc(DwdStockDaily.pct_chg))
        .limit(limit)
    ).all()
    return [{"name": name, **to_dict(daily)} for daily, name in rows]


def market_quotes(db: Session) -> list[dict]:
    latest = (
        select(DwdStockDaily.symbol, func.max(DwdStockDaily.trade_date).label("trade_date"))
        .where(DwdStockDaily.adjust == DEFAULT_ADJUST)
        .group_by(DwdStockDaily.symbol)
        .subquery()
    )
    rows = db.execute(
        select(DwdStockDaily, StockBasic.name)
        .join(latest, (DwdStockDaily.symbol == latest.c.symbol) & (DwdStockDaily.trade_date == latest.c.trade_date))
        .join(StockBasic, StockBasic.symbol == DwdStockDaily.symbol, isouter=True)
        .order_by(DwdStockDaily.symbol)
    ).all()
    return [{"name": name, **to_dict(daily)} for daily, name in rows]


def factor_rank(db: Session, limit: int = 20) -> list[dict]:
    latest = latest_factor_subquery(db)
    rows = db.execute(
        select(FactorStockDaily, StockBasic.name)
        .join(latest, (FactorStockDaily.symbol == latest.c.symbol) & (FactorStockDaily.trade_date == latest.c.trade_date))
        .join(StockBasic, StockBasic.symbol == FactorStockDaily.symbol, isouter=True)
        .order_by(desc(FactorStockDaily.total_score))
        .limit(limit)
    ).all()
    return [{"name": name, **to_dict(factor)} for factor, name in rows]


def to_dict(obj) -> dict:
    data = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        data[column.name] = value
    return data


def recent_logs(db: Session, limit: int = 50) -> list[dict]:
    rows = db.scalars(select(SyncTaskLog).order_by(desc(SyncTaskLog.start_time)).limit(limit)).all()
    return [_sync_log_to_read_dict(row) for row in rows]


def _sync_log_to_read_dict(row: SyncTaskLog) -> dict:
    data = to_dict(row)
    status = str(row.status or "").lower()
    if status in {"success", "partial_success"} and not data["progress_total"]:
        data["progress_total"] = 1
        data["progress_done"] = 1
        data["progress_message"] = data["progress_message"] or "同步完成"
    return data


def stock_chart_bars(db: Session, symbol: str, period: str, limit: int = 240) -> list[dict]:
    bar_rows = db.scalars(
        select(DwdStockBar)
        .where(DwdStockBar.symbol == symbol, DwdStockBar.period == period)
        .where(DwdStockBar.adjust == DEFAULT_ADJUST)
        .order_by(DwdStockBar.trade_date.desc())
        .limit(limit)
    ).all()
    bars = list(reversed(bar_rows))
    if not bars:
        return []
    factor_rows = db.scalars(
        select(FactorStockBar).where(
            FactorStockBar.symbol == symbol,
            FactorStockBar.period == period,
            FactorStockBar.trade_date.in_([bar.trade_date for bar in bars]),
        )
    ).all()
    factor_by_date = {row.trade_date: row for row in factor_rows}
    result = []
    for bar in bars:
        factor = factor_by_date.get(bar.trade_date)
        result.append(
            {
                "symbol": bar.symbol,
                "period": bar.period,
                "trade_date": bar.trade_date,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
                "amount": bar.amount,
                "adjust": bar.adjust,
                "ma5": factor.ma5 if factor else None,
                "ma10": factor.ma10 if factor else None,
                "ma20": factor.ma20 if factor else None,
                "ma60": factor.ma60 if factor else None,
                "macd": factor.macd if factor else None,
                "macd_signal": factor.macd_signal if factor else None,
                "macd_hist": factor.macd_hist if factor else None,
            }
        )
    return result
