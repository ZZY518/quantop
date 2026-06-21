from __future__ import annotations

import json
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data_sources.base import DataSourceClient
from app.data_sources.factory import create_data_source_client
from app.models.bar import DwdStockBar, OdsStockBar
from app.models.daily import DwdStockDaily, OdsStockDaily
from app.models.stock import StockBasic
from app.models.sync_log import SyncTaskLog
from app.services.bar_service import DERIVED_PERIODS, BarService
from app.services.factor_service import FactorService

SUPPORTED_PERIODS = {"1d", "1w", "1m"}
FACTOR_PERIODS = ("1d", "1w", "1m")


class SyncService:
    def __init__(self, db: Session, client: DataSourceClient | None = None):
        self.db = db
        self.client = client

    @property
    def data_client(self) -> DataSourceClient:
        if self.client is None:
            self.client = create_data_source_client()
        return self.client

    def sync_stock_basic(self) -> SyncTaskLog:
        client = self.data_client
        log = self._start_log("stock_basic", None)
        try:
            rows = client.get_stock_basic()
            for row in rows:
                self.db.merge(StockBasic(**row))
            self._finish_log(log, len(rows), len(rows), 0)
        except Exception as exc:
            self._fail_log(log, exc)
            raise
        return log

    def sync_stock_daily(
        self,
        symbol: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> SyncTaskLog:
        self.data_client
        log = self._start_log("stock_daily_with_indicators", end_date or date.today())
        try:
            symbols = self._resolve_symbols(symbol)
            total = self._sync_daily_for_symbols(symbols, start_date=start_date, end_date=end_date)
            total += self._run_indicator_pipeline(symbols, start_date=start_date, end_date=end_date)
            self._finish_log(log, total, total, 0)
        except Exception as exc:
            self._fail_log(log, exc)
            raise
        return log

    def sync_stock_daily_top_amount(
        self,
        limit: int = 100,
        start_date: date | None = None,
        end_date: date | None = None,
        log: SyncTaskLog | None = None,
    ) -> SyncTaskLog:
        log = log or self._start_log("stock_daily_top_amount_with_indicators", end_date or date.today())
        try:
            client = self.data_client
            top_stocks = client.get_top_amount_stocks(limit=limit, trade_date=end_date)
            for stock in top_stocks:
                self.db.merge(StockBasic(**stock))
            self.db.flush()
            symbols = [stock["symbol"] for stock in top_stocks]
            total = self._sync_daily_for_symbols(symbols, start_date=start_date, end_date=end_date)
            total += self._run_indicator_pipeline(symbols, start_date=start_date, end_date=end_date)
            self._finish_log(log, total, total, 0)
        except Exception as exc:
            self._fail_log(log, exc)
            raise
        return log

    def sync_factors(self, symbol: str | None = None) -> SyncTaskLog:
        log = self._start_log("factors", date.today())
        try:
            symbols = [symbol] if symbol else list(self.db.scalars(select(DwdStockDaily.symbol).distinct()).all())
            factor_service = FactorService(self.db)
            total = factor_service.calculate_daily_for_symbols(symbols)
            total += factor_service.calculate_bar_for_symbols(symbols, "1d")
            self._finish_log(log, total, total, 0)
        except Exception as exc:
            self._fail_log(log, exc)
            raise
        return log

    def sync_bars(
        self,
        period: str = "1d",
        symbol: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> SyncTaskLog:
        self._validate_period(period)
        client = self.data_client
        log = self._start_log(f"stock_bar_{period}", end_date or date.today())
        try:
            symbols = self._resolve_symbols(symbol)
            if period == "1d":
                total = self._sync_daily_for_symbols(symbols, start_date=start_date, end_date=end_date)
            else:
                total = BarService(self.db, client.source).aggregate_for_symbols(
                    symbols, period, start_date=start_date, end_date=end_date
                )
                self.db.flush()
            total += FactorService(self.db).calculate_bar_for_symbols(symbols, period)
            self._finish_log(log, total, total, 0)
        except Exception as exc:
            self._fail_log(log, exc)
            raise
        return log

    def sync_bar_factors(self, period: str = "1d", symbol: str | None = None) -> SyncTaskLog:
        self._validate_period(period)
        log = self._start_log(f"bar_factors_{period}", date.today())
        try:
            symbols = [symbol] if symbol else list(
                self.db.scalars(select(DwdStockBar.symbol).where(DwdStockBar.period == period).distinct()).all()
            )
            total = FactorService(self.db).calculate_bar_for_symbols(symbols, period)
            self._finish_log(log, total, total, 0)
        except Exception as exc:
            self._fail_log(log, exc)
            raise
        return log

    def _run_indicator_pipeline(
        self,
        symbols: list[str],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        bar_service = BarService(self.db, self.data_client.source)
        factor_service = FactorService(self.db)

        total = 0
        for period in DERIVED_PERIODS:
            total += bar_service.aggregate_for_symbols(symbols, period, start_date=start_date, end_date=end_date)
        self.db.flush()
        total += factor_service.calculate_daily_for_symbols(symbols)
        for period in FACTOR_PERIODS:
            total += factor_service.calculate_bar_for_symbols(symbols, period)
        return total

    def _sync_daily_for_symbols(
        self,
        symbols: list[str],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        total = 0
        for symbol in symbols:
            rows = self.data_client.get_stock_daily(symbol, start_date=start_date, end_date=end_date)
            total += len(rows)
            for row in rows:
                self._insert_ods_daily_once(row)
                self._insert_ods_bar_once(row, "1d", "stock_bar")
                self.db.merge(DwdStockDaily(**row, source=self.data_client.source))
                self.db.merge(DwdStockBar(**row, period="1d", source=self.data_client.source))
        self.db.flush()
        return total

    def _insert_ods_daily_once(self, row: dict) -> None:
        exists = self.db.scalar(
            select(OdsStockDaily.id).where(
                OdsStockDaily.source == self.data_client.source,
                OdsStockDaily.api_name == "stock_daily",
                OdsStockDaily.symbol == row["symbol"],
                OdsStockDaily.trade_date == row["trade_date"],
            )
        )
        if exists:
            return
        self.db.add(
            OdsStockDaily(
                source=self.data_client.source,
                api_name="stock_daily",
                symbol=row["symbol"],
                trade_date=row["trade_date"],
                raw_json=json.dumps(row, ensure_ascii=False, default=str),
            )
        )

    def _insert_ods_bar_once(self, row: dict, period: str, api_name: str) -> None:
        exists = self.db.scalar(
            select(OdsStockBar.id).where(
                OdsStockBar.source == self.data_client.source,
                OdsStockBar.api_name == api_name,
                OdsStockBar.symbol == row["symbol"],
                OdsStockBar.period == period,
                OdsStockBar.trade_date == row["trade_date"],
            )
        )
        if exists:
            return
        self.db.add(
            OdsStockBar(
                source=self.data_client.source,
                api_name=api_name,
                symbol=row["symbol"],
                period=period,
                trade_date=row["trade_date"],
                raw_json=json.dumps(row, ensure_ascii=False, default=str),
            )
        )

    def _resolve_symbols(self, symbol: str | None = None) -> list[str]:
        if symbol:
            return [symbol]
        symbols = list(self.db.scalars(select(StockBasic.symbol)).all())
        if symbols:
            return symbols
        return [row["symbol"] for row in self.data_client.get_stock_basic()]

    def _validate_period(self, period: str) -> None:
        if period not in SUPPORTED_PERIODS:
            raise ValueError(f"unsupported period: {period}")

    def _start_log(self, task_name: str, biz_date: date | None) -> SyncTaskLog:
        log = SyncTaskLog(
            task_name=task_name,
            source=self.data_client.source if self.client else "local",
            biz_date=biz_date,
            status="running",
            start_time=datetime.utcnow(),
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def _finish_log(self, log: SyncTaskLog, total: int, success: int, fail: int) -> None:
        log.status = "success" if fail == 0 else "partial_success"
        log.end_time = datetime.utcnow()
        log.total_count = total
        log.success_count = success
        log.fail_count = fail
        self.db.commit()
        self.db.refresh(log)

    def _fail_log(self, log: SyncTaskLog, exc: Exception) -> None:
        log.status = "failed"
        log.end_time = datetime.utcnow()
        log.error_message = str(exc)
        self.db.commit()
