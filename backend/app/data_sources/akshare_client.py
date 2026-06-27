from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
import requests
import os

from app.data_sources.factory import DataSourceUnavailable
from app.core.constants import DEFAULT_ADJUST
from app.data_sources.normalize import normalize_price_series


class AkShareDataSourceClient:
    source = "akshare"

    def __init__(self):
        self._disable_broken_proxy_env()
        self._force_requests_direct()
        import akshare as ak

        self.ak = ak

    def get_top_amount_stocks(self, limit: int = 100, trade_date: date | None = None) -> list[dict]:
        try:
            df = self._get_top_amount_spot_eastmoney(limit)
        except requests.RequestException:
            df = self._get_top_amount_spot_sina()
        if df.empty:
            return []

        df = df.copy()
        df["成交额"] = pd.to_numeric(df["成交额"], errors="coerce").fillna(0)
        df = df.sort_values("成交额", ascending=False).head(limit)

        stocks: list[dict] = []
        for _, row in df.iterrows():
            code = self._normalize_code(row["代码"])
            stocks.append(
                {
                    "symbol": self._to_symbol(code),
                    "name": str(row["名称"]),
                    "market": "CN",
                    "exchange": self._exchange(code),
                    "industry": None,
                    "list_date": self._parse_yyyymmdd(row.get("上市日期")),
                    "status": "listed",
                }
            )
        return stocks

    def get_stock_basic(self) -> list[dict]:
        rows_by_code = {}
        page = 1
        page_size = 100
        while True:
            page_rows = self._get_stock_basic_eastmoney_page(page=page, page_size=page_size)
            if not page_rows:
                break
            for row in page_rows:
                code = row.get("f12")
                if code:
                    rows_by_code[str(code)] = row
            if len(page_rows) < page_size:
                break
            page += 1

        stocks: list[dict] = []
        for row in rows_by_code.values():
            code = self._normalize_code(row.get("f12"))
            stocks.append(
                {
                    "symbol": self._to_symbol(code),
                    "name": str(row.get("f14") or ""),
                    "market": "CN",
                    "exchange": self._exchange(code),
                    "industry": None,
                    "list_date": self._parse_yyyymmdd(row.get("f26")),
                    "status": "listed",
                }
            )
        return stocks

    def _get_top_amount_spot_eastmoney(self, limit: int) -> pd.DataFrame:
        rows_by_code = {}
        page = 1
        page_size = min(max(limit, 1), 100)
        target_count = limit + page_size
        while len(rows_by_code) < target_count:
            page_rows = self._get_top_amount_spot_eastmoney_page(page=page, page_size=page_size)
            if not page_rows:
                break
            for row in page_rows:
                code = row.get("f12")
                if code:
                    rows_by_code[str(code)] = row
            if len(page_rows) < page_size:
                break
            page += 1

        rows = list(rows_by_code.values())
        return pd.DataFrame(
            [
                {
                    "代码": item.get("f12"),
                    "名称": item.get("f14"),
                    "最新价": item.get("f2"),
                    "涨跌幅": item.get("f3"),
                    "成交额": item.get("f6"),
                    "上市日期": item.get("f26"),
                }
                for item in rows
            ]
        )

    def _get_top_amount_spot_eastmoney_page(self, page: int, page_size: int) -> list[dict]:
        session = requests.Session()
        session.trust_env = False
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": page,
            "pz": page_size,
            "po": 1,
            "np": 1,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": 2,
            "invt": 2,
            "fid": "f6",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
            "fields": "f12,f14,f2,f3,f6,f26",
        }
        response = session.get(url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        return payload.get("data", {}).get("diff", []) or []

    def _get_stock_basic_eastmoney_page(self, page: int, page_size: int) -> list[dict]:
        session = requests.Session()
        session.trust_env = False
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": page,
            "pz": page_size,
            "po": 0,
            "np": 1,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": 2,
            "invt": 2,
            "fid": "f12",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
            "fields": "f12,f14,f26",
        }
        response = session.get(url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        return payload.get("data", {}).get("diff", []) or []

    def get_stock_daily(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        rows = self._get_stock_daily_rows(symbol, start_date=start_date, end_date=end_date)
        return normalize_price_series(rows)

    def _get_stock_daily_rows(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        end_date = end_date or date.today()
        start_date = start_date or end_date - timedelta(days=180)
        code = self._plain_code(symbol)
        try:
            df = self.ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust="qfq",
            )
        except requests.RequestException as exc:
            df = self._get_daily_sina(symbol, start_date, end_date, exc)
        if df.empty:
            return []

        return self._rows_from_frame(code, df)

    def _rows_from_frame(self, code: str, df: pd.DataFrame) -> list[dict]:
        rows: list[dict] = []
        pre_close: Decimal | None = None
        for _, row in df.sort_values("日期").iterrows():
            open_price = self._decimal(row["开盘"])
            high = self._decimal(row["最高"])
            low = self._decimal(row["最低"])
            close = self._decimal(row["收盘"])
            trade_date = pd.to_datetime(row["日期"]).date()
            change_amount = self._decimal(row.get("涨跌额"))
            pct_chg = self._decimal(row.get("涨跌幅"))
            if pre_close is None and change_amount is not None:
                pre_close = close - change_amount
            if pre_close is None:
                pre_close = close
            volume = self._decimal(row["成交量"])
            amount = self._decimal(row["成交额"])
            rows.append(
                {
                    "symbol": self._to_symbol(code),
                    "trade_date": trade_date,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "pre_close": pre_close,
                    "change_amount": change_amount,
                    "pct_chg": pct_chg,
                    "volume": volume,
                    "amount": amount,
                    "adj_factor": Decimal("1"),
                    "adjust": DEFAULT_ADJUST,
                    "is_suspended": False,
                    "data_status": "normal",
                }
            )
            pre_close = close
        return rows


    def _get_top_amount_spot_sina(self) -> pd.DataFrame:
        try:
            return self.ak.stock_zh_a_spot()
        except requests.RequestException as exc:
            raise DataSourceUnavailable(f"AKShare spot data request failed: {exc}") from exc

    def _get_daily_tx(self, symbol: str, start_date: date, end_date: date, original_exc: Exception) -> pd.DataFrame:
        tx_symbol = self._tx_symbol(symbol)
        try:
            df = self.ak.stock_zh_a_hist_tx(
                symbol=tx_symbol,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust="qfq",
            )
        except requests.RequestException as exc:
            raise DataSourceUnavailable(
                f"AKShare daily data request failed for {symbol}: eastmoney={original_exc}; tencent={exc}"
            ) from exc
        if df.empty:
            return df
        df = df.rename(
            columns={
                "date": "日期",
                "open": "开盘",
                "close": "收盘",
                "high": "最高",
                "low": "最低",
                "amount": "成交量",
            }
        )
        df["成交额"] = pd.to_numeric(df["成交量"], errors="coerce") * 100 * pd.to_numeric(df["收盘"], errors="coerce")
        df["涨跌额"] = pd.to_numeric(df["收盘"], errors="coerce").diff()
        df["涨跌幅"] = pd.to_numeric(df["收盘"], errors="coerce").pct_change() * 100
        return df

    def _get_daily_sina(self, symbol: str, start_date: date, end_date: date, original_exc: Exception) -> pd.DataFrame:
        try:
            df = self.ak.stock_zh_a_daily(
                symbol=self._tx_symbol(symbol),
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust="",
            )
        except requests.RequestException:
            return self._get_daily_tx(symbol, start_date, end_date, original_exc)
        if df.empty:
            return df
        df = df.rename(
            columns={
                "date": "日期",
                "open": "开盘",
                "close": "收盘",
                "high": "最高",
                "low": "最低",
                "volume": "成交量",
                "amount": "成交额",
            }
        )
        df["涨跌额"] = pd.to_numeric(df["收盘"], errors="coerce").diff()
        df["涨跌幅"] = pd.to_numeric(df["收盘"], errors="coerce").pct_change() * 100
        return df

    def _plain_code(self, symbol: str) -> str:
        return self._normalize_code(symbol.split(".")[0])

    def _normalize_code(self, value) -> str:
        code = str(value).strip().lower()
        if code.startswith(("sh", "sz", "bj")):
            code = code[2:]
        return code.zfill(6)

    def _to_symbol(self, code: str) -> str:
        return f"{code}.{self._exchange(code)}"

    def _tx_symbol(self, symbol: str) -> str:
        code = self._plain_code(symbol)
        prefix = "sh" if self._exchange(code) == "SH" else "sz"
        return f"{prefix}{code}"

    def _exchange(self, code: str) -> str:
        code = self._normalize_code(code)
        if code.startswith(("6", "9")):
            return "SH"
        return "SZ"

    def _decimal(self, value) -> Decimal | None:
        if value is None or pd.isna(value):
            return None
        return Decimal(str(value))

    def _parse_yyyymmdd(self, value) -> date | None:
        if value is None or pd.isna(value):
            return None
        text = str(value).strip()
        if not text or text == "-":
            return None
        try:
            return pd.to_datetime(text, format="%Y%m%d").date()
        except ValueError:
            return pd.to_datetime(text).date()

    def _disable_broken_proxy_env(self) -> None:
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            os.environ.pop(key, None)

    def _force_requests_direct(self) -> None:
        original_request = requests.sessions.Session.request

        def direct_request(session, method, url, **kwargs):
            session.trust_env = False
            kwargs.setdefault("proxies", {})
            return original_request(session, method, url, **kwargs)

        requests.sessions.Session.request = direct_request
