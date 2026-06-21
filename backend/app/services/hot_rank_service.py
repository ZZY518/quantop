from __future__ import annotations

from datetime import datetime, timezone, timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.data_sources.eastmoney_hot_rank_client import EastmoneyHotRankClient
from app.core.constants import DEFAULT_ADJUST
from app.models.daily import DwdStockDaily
from app.models.stock import StockBasic


def hot_rank(limit: int = 100, db: Session | None = None) -> list[dict]:
    client = EastmoneyHotRankClient()
    fetched_at = datetime.now(timezone(timedelta(hours=8)))
    rows = client.get_hot_rank(limit=limit)
    names: dict[str, str] = {}
    if db is not None:
        symbols = [row["symbol"] for row in rows]
        if symbols:
            stock_rows = db.execute(select(StockBasic.symbol, StockBasic.name).where(StockBasic.symbol.in_(symbols))).all()
            names = {symbol: name for symbol, name in stock_rows}
    quote_by_symbol = _load_latest_daily_quote_map(db, [row["symbol"] for row in rows]) if db is not None else {}
    return [
        {
            **row,
            "name": quote_by_symbol.get(row["symbol"], {}).get("name") or names.get(row["symbol"], row["name"]),
            "latest_price": quote_by_symbol.get(row["symbol"], {}).get("latest_price"),
            "change_amount": quote_by_symbol.get(row["symbol"], {}).get("change_amount"),
            "pct_chg": quote_by_symbol.get(row["symbol"], {}).get("pct_chg"),
            "source": client.source,
            "fetched_at": fetched_at,
        }
        for row in rows
    ]


def _load_latest_daily_quote_map(db: Session, symbols: list[str]) -> dict[str, dict]:
    if not symbols:
        return {}

    latest_subquery = (
        select(DwdStockDaily.symbol, func.max(DwdStockDaily.trade_date).label("trade_date"))
        .where(DwdStockDaily.symbol.in_(symbols), DwdStockDaily.adjust == DEFAULT_ADJUST)
        .group_by(DwdStockDaily.symbol)
        .subquery()
    )
    rows = db.execute(
        select(DwdStockDaily)
        .join(
            latest_subquery,
            (DwdStockDaily.symbol == latest_subquery.c.symbol)
            & (DwdStockDaily.trade_date == latest_subquery.c.trade_date),
        )
        .where(DwdStockDaily.adjust == DEFAULT_ADJUST)
    ).scalars().all()

    quote_map: dict[str, dict] = {}
    for row in rows:
        quote_map[row.symbol] = {
            "name": "",
            "latest_price": float(row.close) if row.close is not None else None,
            "change_amount": float(row.change_amount) if row.change_amount is not None else None,
            "pct_chg": float(row.pct_chg) if row.pct_chg is not None else None,
        }
    return quote_map
