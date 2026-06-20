from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class StockBasicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    name: str
    market: str
    exchange: str
    industry: str | None
    list_date: date | None
    status: str
    created_at: datetime
    updated_at: datetime
