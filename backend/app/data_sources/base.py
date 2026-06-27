from __future__ import annotations

from datetime import date
from typing import Protocol


class DataSourceClient(Protocol):
    source: str

    def get_stock_basic(self) -> list[dict]:
        ...

    def get_top_amount_stocks(self, limit: int = 100, trade_date: date | None = None) -> list[dict]:
        ...

    def get_stock_daily(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        ...
