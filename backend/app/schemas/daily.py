from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DwdStockDailyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    pre_close: Decimal | None
    change_amount: Decimal | None
    pct_chg: Decimal | None
    volume: Decimal
    amount: Decimal
    adj_factor: Decimal | None
    adjust: str
    source: str
    is_suspended: bool
    data_status: str
    created_at: datetime
    updated_at: datetime


class MarketRankRead(DwdStockDailyRead):
    name: str | None = None
