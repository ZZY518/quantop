from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class HotRankRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    symbol: str
    name: str
    latest_price: Decimal | None
    change_amount: Decimal | None
    pct_chg: Decimal | None
    source: str
    fetched_at: datetime
