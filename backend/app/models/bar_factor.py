from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FactorStockBar(Base):
    __tablename__ = "factor_stock_bar"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    period: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    factor_version: Mapped[str] = mapped_column(String(32), primary_key=True, default="v1")
    ma5: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    ma10: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    ma20: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    ma60: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    rsi6: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    rsi12: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    macd: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    macd_signal: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    macd_hist: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    return_1d: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    return_5d: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    return_20d: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    volatility_20d: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    score_trend: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    score_momentum: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    score_risk: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
