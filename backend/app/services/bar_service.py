from __future__ import annotations

import json
from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bar import DwdStockBar, OdsStockBar
from app.models.daily import DwdStockDaily
from app.core.constants import DEFAULT_ADJUST

DERIVED_PERIODS = ("1w", "1m")


class BarService:
    def __init__(self, db: Session, source: str):
        self.db = db
        self.source = source

    def aggregate_for_symbols(
        self,
        symbols: list[str],
        period: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        total = 0
        for symbol in symbols:
            total += self.aggregate_symbol(symbol, period, start_date=start_date, end_date=end_date)
        return total

    def aggregate_symbol(
        self,
        symbol: str,
        period: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        query = (
            select(DwdStockBar)
            .where(DwdStockBar.symbol == symbol, DwdStockBar.period == "1d", DwdStockBar.adjust == DEFAULT_ADJUST)
            .order_by(DwdStockBar.trade_date)
        )
        if start_date:
            query = query.where(DwdStockBar.trade_date >= start_date)
        if end_date:
            query = query.where(DwdStockBar.trade_date <= end_date)

        source_rows = [self._bar_to_full_dict(row) for row in self.db.execute(query).scalars()]
        if not source_rows:
            source_rows = [
                self._daily_to_full_dict(row)
                for row in self.db.execute(
                    select(DwdStockDaily)
                    .where(DwdStockDaily.symbol == symbol, DwdStockDaily.adjust == DEFAULT_ADJUST)
                    .order_by(DwdStockDaily.trade_date)
                ).scalars()
            ]

        rows = self._aggregate_rows(source_rows, period)
        for row in rows:
            self._insert_ods_bar_once(row, period, "stock_bar_aggregate")
            self.db.merge(DwdStockBar(**row, period=period, source=self.source))
        return len(rows)

    def _aggregate_rows(self, rows: list[dict], period: str) -> list[dict]:
        if not rows:
            return []
        rule = {"1w": "W-FRI", "1m": "ME"}[period]
        df = pd.DataFrame(rows).sort_values("trade_date")
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        records = []
        for _key, group in df.groupby(pd.Grouper(key="trade_date", freq=rule)):
            if group.empty:
                continue
            first = group.iloc[0]
            last = group.iloc[-1]
            pre_close = first.get("pre_close")
            close = last["close"]
            change_amount = None if pd.isna(pre_close) else close - pre_close
            pct_chg = None if not pre_close else change_amount / pre_close * 100
            records.append(
                {
                    "symbol": last["symbol"],
                    "trade_date": last["trade_date"].date(),
                    "open": first["open"],
                    "high": group["high"].max(),
                    "low": group["low"].min(),
                    "close": close,
                    "pre_close": pre_close,
                    "change_amount": change_amount,
                    "pct_chg": pct_chg,
                    "volume": group["volume"].sum(),
                    "amount": group["amount"].sum(),
                    "adj_factor": last.get("adj_factor"),
                    "adjust": last.get("adjust", DEFAULT_ADJUST),
                    "is_suspended": bool(group["is_suspended"].all()),
                    "data_status": "normal",
                }
            )
        return records

    def _insert_ods_bar_once(self, row: dict, period: str, api_name: str) -> None:
        exists = self.db.scalar(
            select(OdsStockBar.id).where(
                OdsStockBar.source == self.source,
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
                source=self.source,
                api_name=api_name,
                symbol=row["symbol"],
                period=period,
                trade_date=row["trade_date"],
                raw_json=json.dumps(row, ensure_ascii=False, default=str),
            )
        )

    def _daily_to_full_dict(self, row: DwdStockDaily) -> dict:
        return {
            column.name: getattr(row, column.name)
            for column in DwdStockDaily.__table__.columns
            if column.name not in {"created_at", "updated_at", "source"}
        }

    def _bar_to_full_dict(self, row: DwdStockBar) -> dict:
        return {
            column.name: getattr(row, column.name)
            for column in DwdStockBar.__table__.columns
            if column.name not in {"created_at", "updated_at", "source", "period"}
        }
