from __future__ import annotations

import atexit
import os
from datetime import date, timedelta
from decimal import Decimal

import pandas as pd

from app.data_sources.factory import DataSourceUnavailable
from app.core.constants import DEFAULT_ADJUST
from app.data_sources.normalize import normalize_price_series


class BaoStockDataSourceClient:
    source = "baostock"

    def __init__(self):
        self._disable_broken_proxy_env()
        import baostock as bs

        self.bs = bs
        login = self.bs.login()
        if login.error_code != "0":
            raise DataSourceUnavailable(f"BaoStock login failed: {login.error_msg}")
        atexit.register(self.bs.logout)

    def get_top_amount_stocks(self, limit: int = 100, trade_date: date | None = None) -> list[dict]:
        target_date = self._latest_trade_date(trade_date or date.today())
        stocks = self._all_stocks(target_date)
        if not stocks:
            return []

        ranked = []
        for stock in stocks:
            rows = self.get_stock_daily(stock["symbol"], start_date=target_date, end_date=target_date)
            if not rows:
                continue
            ranked.append({**stock, "amount": rows[-1]["amount"] or Decimal("0")})

        ranked.sort(key=lambda row: row["amount"], reverse=True)
        return [{key: row[key] for key in ("symbol", "name", "market", "exchange", "industry", "list_date", "status")} for row in ranked[:limit]]

    def get_stock_basic(self) -> list[dict]:
        return self._all_stocks(self._latest_trade_date(date.today()))

    def get_stock_daily(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        end_date = end_date or date.today()
        start_date = start_date or end_date - timedelta(days=180)
        code = self._to_baostock_code(symbol)
        fields = "date,code,open,high,low,close,preclose,volume,amount,pctChg,tradestatus"
        rs = self.bs.query_history_k_data_plus(
            code,
            fields,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            frequency="d",
            adjustflag="2",
        )
        df = self._result_to_frame(rs, f"BaoStock daily data request failed for {symbol}")
        if df.empty:
            return []

        rows: list[dict] = []
        for _, row in df.sort_values("date").iterrows():
            close = self._decimal(row["close"])
            pre_close = self._decimal(row["preclose"])
            change_amount = None
            if close is not None and pre_close is not None:
                change_amount = close - pre_close
            rows.append(
                {
                    "symbol": self._to_symbol(row["code"]),
                    "trade_date": pd.to_datetime(row["date"]).date(),
                    "open": self._decimal(row["open"]),
                    "high": self._decimal(row["high"]),
                    "low": self._decimal(row["low"]),
                    "close": close,
                    "pre_close": pre_close,
                    "change_amount": change_amount,
                    "pct_chg": self._decimal(row["pctChg"]),
                    "volume": self._decimal(row["volume"]) or Decimal("0"),
                    "amount": self._decimal(row["amount"]) or Decimal("0"),
                    "adj_factor": Decimal("1"),
                    "adjust": DEFAULT_ADJUST,
                    "is_suspended": str(row.get("tradestatus")) != "1",
                    "data_status": "normal",
                }
            )
        return normalize_price_series(rows)

    def _latest_trade_date(self, end_date: date) -> date:
        start_date = end_date - timedelta(days=14)
        rs = self.bs.query_trade_dates(start_date=start_date.isoformat(), end_date=end_date.isoformat())
        df = self._result_to_frame(rs, "BaoStock trade calendar request failed")
        if df.empty:
            return end_date
        trade_days = df[df["is_trading_day"] == "1"]
        if trade_days.empty:
            return end_date
        return pd.to_datetime(trade_days.iloc[-1]["calendar_date"]).date()

    def _all_stocks(self, trade_date: date) -> list[dict]:
        rs = self.bs.query_all_stock(day=trade_date.isoformat())
        df = self._result_to_frame(rs, "BaoStock stock list request failed")
        if df.empty:
            return []
        stocks = []
        for _, row in df.iterrows():
            symbol = self._to_symbol(row["code"])
            stocks.append(
                {
                    "symbol": symbol,
                    "name": str(row.get("code_name") or ""),
                    "market": "CN",
                    "exchange": symbol.split(".")[1],
                    "industry": None,
                    "list_date": None,
                    "status": "listed",
                }
            )
        return stocks

    def _result_to_frame(self, rs, message: str) -> pd.DataFrame:
        if rs.error_code != "0":
            raise DataSourceUnavailable(f"{message}: {rs.error_msg}")
        rows = []
        while rs.next():
            rows.append(rs.get_row_data())
        return pd.DataFrame(rows, columns=rs.fields)

    def _to_baostock_code(self, symbol: str) -> str:
        code = symbol.strip().lower()
        if code.startswith(("sh.", "sz.")):
            return code
        plain, exchange = symbol.split(".")
        return f"{exchange.lower()}.{plain}"

    def _to_symbol(self, baostock_code: str) -> str:
        exchange, code = baostock_code.split(".")
        return f"{code}.{exchange.upper()}"

    def _decimal(self, value) -> Decimal | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return Decimal(text)

    def _disable_broken_proxy_env(self) -> None:
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            os.environ.pop(key, None)
