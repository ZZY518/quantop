from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.factors.calculator import calculate_daily_factors, calculate_factors
from app.models.bar import DwdStockBar
from app.models.bar_factor import FactorStockBar
from app.models.daily import DwdStockDaily
from app.models.factor import FactorStockDaily
from app.core.constants import DEFAULT_ADJUST


class FactorService:
    def __init__(self, db: Session):
        self.db = db

    def calculate_daily_for_symbols(self, symbols: list[str]) -> int:
        total = 0
        for symbol in symbols:
            rows = self.db.execute(
                select(DwdStockDaily)
                .where(DwdStockDaily.symbol == symbol, DwdStockDaily.adjust == DEFAULT_ADJUST)
                .order_by(DwdStockDaily.trade_date)
            ).scalars()
            factor_rows = calculate_daily_factors([self._daily_to_dict(row) for row in rows])
            total += len(factor_rows)
            for factor in factor_rows:
                self.db.merge(FactorStockDaily(**factor))
        return total

    def calculate_bar_for_symbols(self, symbols: list[str], period: str) -> int:
        total = 0
        for symbol in symbols:
            rows = self.db.execute(
                select(DwdStockBar)
                .where(DwdStockBar.symbol == symbol, DwdStockBar.period == period, DwdStockBar.adjust == DEFAULT_ADJUST)
                .order_by(DwdStockBar.trade_date)
            ).scalars()
            factor_rows = calculate_factors([self._bar_to_dict(row) for row in rows])
            total += len(factor_rows)
            for factor in factor_rows:
                self.db.merge(FactorStockBar(**factor, period=period))
        return total

    def _daily_to_dict(self, row: DwdStockDaily) -> dict:
        return {"symbol": row.symbol, "trade_date": row.trade_date, "close": float(row.close)}

    def _bar_to_dict(self, row: DwdStockBar) -> dict:
        return {"symbol": row.symbol, "trade_date": row.trade_date, "close": float(row.close)}
