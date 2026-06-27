from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.data_sources.base import DataSourceClient
from app.data_sources.factory import create_data_source_client
from app.core.constants import DEFAULT_ADJUST
from app.models.bar import DwdStockBar, OdsStockBar
from app.models.daily import DwdStockDaily, OdsStockDaily
from app.models.stock import StockBasic
from app.models.sync_log import SyncTaskLog
from app.services.bar_service import DERIVED_PERIODS, BarService
from app.services.factor_service import FactorService

SUPPORTED_PERIODS = {"1d", "1w", "1m"}
FACTOR_PERIODS = ("1d", "1w", "1m")
INITIAL_DAILY_START_DATE = date(2020, 1, 1)
MIN_LISTING_HISTORY_START_DATE = date(2010, 1, 1)


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
            self._update_progress(log, total=1, done=0, message="正在获取成交额榜")
            top_stocks = client.get_top_amount_stocks(limit=limit, trade_date=end_date)
            for stock in top_stocks:
                self.db.merge(StockBasic(**stock))
            self.db.flush()
            symbols = [stock["symbol"] for stock in top_stocks]
            progress_total = len(symbols) + 3
            self._update_progress(log, total=progress_total, done=0, message=f"已选出 {len(symbols)} 只股票")
            total = self._sync_daily_for_symbols(
                symbols,
                start_date=start_date,
                end_date=end_date,
                progress_log=log,
            )
            total += self._run_indicator_pipeline(
                symbols,
                start_date=start_date,
                end_date=end_date,
                progress_log=log,
            )
            self._finish_log(log, total, total, 0)
        except Exception as exc:
            self._fail_log(log, exc)
            raise
        return log

    def sync_listing_history_for_existing_stocks(self, log: SyncTaskLog | None = None) -> SyncTaskLog:
        log = log or self._start_log("stock_daily_listing_history", date.today())
        try:
            self._update_progress(log, total=1, done=0, message="正在补全股票上市日期")
            existing_symbols = set(self.db.scalars(select(StockBasic.symbol)).all())
            stock_basic_rows = self.data_client.get_stock_basic()
            for row in stock_basic_rows:
                if row["symbol"] in existing_symbols:
                    self.db.merge(StockBasic(**row))
            self.db.flush()

            symbols = sorted(existing_symbols)
            self._update_progress(log, total=len(symbols) + 3, done=0, message=f"准备回补 {len(symbols)} 只股票")
            total = self._sync_daily_for_symbols(symbols, progress_log=log)
            total += self._run_indicator_pipeline(symbols, progress_log=log)
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
        progress_log: SyncTaskLog | None = None,
    ) -> int:
        bar_service = BarService(self.db, self.data_client.source)
        factor_service = FactorService(self.db)

        total = 0
        self._update_progress(progress_log, message="正在聚合周线和月线")
        for period in DERIVED_PERIODS:
            total += bar_service.aggregate_for_symbols(symbols, period, start_date=start_date, end_date=end_date)
        self.db.flush()
        self._increment_progress(progress_log, "正在计算日线因子")
        total += factor_service.calculate_daily_for_symbols(symbols)
        self._increment_progress(progress_log, "正在计算周期因子")
        for period in FACTOR_PERIODS:
            total += factor_service.calculate_bar_for_symbols(symbols, period)
        self._increment_progress(progress_log, "同步结果写入完成")
        return total

    def _sync_daily_for_symbols(
        self,
        symbols: list[str],
        start_date: date | None = None,
        end_date: date | None = None,
        progress_log: SyncTaskLog | None = None,
    ) -> int:
        total = 0
        for index, symbol in enumerate(symbols, start=1):
            should_skip, effective_start, effective_end = self._resolve_daily_sync_range(
                symbol,
                start_date=start_date,
                end_date=end_date,
            )
            if should_skip:
                self._update_progress(progress_log, message=f"{symbol} 已是最新，跳过 ({index}/{len(symbols)})")
                self._increment_progress(progress_log, f"{symbol} 已是最新")
                continue

            self._update_progress(
                progress_log,
                message=f"正在同步 {symbol}{self._sync_range_label(effective_start, effective_end)} ({index}/{len(symbols)})",
            )
            rows = self.data_client.get_stock_daily(symbol, start_date=effective_start, end_date=effective_end)
            total += len(rows)
            for row in rows:
                self._insert_ods_daily_once(row)
                self._insert_ods_bar_once(row, "1d", "stock_bar")
                self.db.merge(DwdStockDaily(**row, source=self.data_client.source))
                self.db.merge(DwdStockBar(**row, period="1d", source=self.data_client.source))
            self._increment_progress(progress_log, f"{symbol} 日线同步完成")
        self.db.flush()
        return total

    def _resolve_daily_sync_range(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[bool, date | None, date | None]:
        if start_date is not None:
            return False, start_date, end_date

        earliest_date, latest_date = self.db.execute(
            select(func.min(DwdStockBar.trade_date), func.max(DwdStockBar.trade_date)).where(
                DwdStockBar.symbol == symbol,
                DwdStockBar.period == "1d",
                DwdStockBar.adjust == DEFAULT_ADJUST,
            )
        ).one()
        listing_start = self._initial_daily_start_date(symbol)
        if latest_date is None:
            return False, listing_start, end_date

        if end_date is None:
            if listing_start and earliest_date and listing_start < earliest_date:
                return False, listing_start, earliest_date - timedelta(days=1)
            return True, None, None

        target_end = end_date
        if latest_date >= target_end:
            return True, None, None
        return False, latest_date + timedelta(days=1), target_end

    def _initial_daily_start_date(self, symbol: str) -> date:
        list_date = self.db.scalar(select(StockBasic.list_date).where(StockBasic.symbol == symbol))
        if list_date is None:
            return INITIAL_DAILY_START_DATE
        return max(list_date, MIN_LISTING_HISTORY_START_DATE)

    def _sync_range_label(self, start_date: date | None, end_date: date | None) -> str:
        if start_date is None:
            return ""
        if end_date is None:
            return f"，从 {start_date.isoformat()} 开始"
        return f"，{start_date.isoformat()} 至 {end_date.isoformat()}"

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
        if not log.progress_total:
            log.progress_total = 1
        log.progress_done = log.progress_total
        log.progress_message = "同步完成"
        self.db.commit()
        self.db.refresh(log)

    def _fail_log(self, log: SyncTaskLog, exc: Exception) -> None:
        log.status = "failed"
        log.end_time = datetime.utcnow()
        log.progress_message = "同步失败"
        log.error_message = str(exc)
        self.db.commit()

    def _update_progress(
        self,
        log: SyncTaskLog | None,
        total: int | None = None,
        done: int | None = None,
        message: str | None = None,
    ) -> None:
        if log is None:
            return
        if total is not None:
            log.progress_total = max(total, 0)
        if done is not None:
            log.progress_done = max(done, 0)
        if message is not None:
            log.progress_message = message
        self.db.commit()

    def _increment_progress(self, log: SyncTaskLog | None, message: str | None = None) -> None:
        if log is None:
            return
        next_done = min((log.progress_done or 0) + 1, log.progress_total or 0)
        self._update_progress(log, done=next_done, message=message)
