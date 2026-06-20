from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class FactorStockDailyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    trade_date: date
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
    factor_version: str
    created_at: datetime
    updated_at: datetime


class FactorRankRead(FactorStockDailyRead):
    name: str | None = None
