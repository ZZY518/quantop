from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DwdStockBarRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    period: str
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


class FactorStockBarRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    period: str
    trade_date: date
    factor_version: str
    ma5: Decimal | None
    ma10: Decimal | None
    ma20: Decimal | None
    ma60: Decimal | None
    rsi6: Decimal | None
    rsi12: Decimal | None
    macd: Decimal | None
    macd_signal: Decimal | None
    macd_hist: Decimal | None
    return_1d: Decimal | None
    return_5d: Decimal | None
    return_20d: Decimal | None
    volatility_20d: Decimal | None
    score_trend: Decimal | None
    score_momentum: Decimal | None
    score_risk: Decimal | None
    total_score: Decimal | None
    created_at: datetime
    updated_at: datetime


class StockChartBarRead(BaseModel):
    symbol: str
    period: str
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    amount: Decimal
    adjust: str
    ma5: Decimal | None = None
    ma10: Decimal | None = None
    ma20: Decimal | None = None
    ma60: Decimal | None = None
    macd: Decimal | None = None
    macd_signal: Decimal | None = None
    macd_hist: Decimal | None = None
