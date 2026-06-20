from datetime import date

from sqlalchemy import Boolean, Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TradeCalendar(Base):
    __tablename__ = "trade_calendar"

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    market: Mapped[str] = mapped_column(String(32), primary_key=True)
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False)
    pre_trade_date: Mapped[date | None] = mapped_column(Date)
