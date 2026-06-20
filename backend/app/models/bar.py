from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OdsStockBar(Base):
    __tablename__ = "ods_stock_bar"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    api_name: Mapped[str] = mapped_column(String(128), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    sync_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DwdStockBar(Base):
    __tablename__ = "dwd_stock_bar"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    period: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    pre_close: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    change_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    pct_chg: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False)
    adj_factor: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    adjust: Mapped[str] = mapped_column(String(16), default="qfq", nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    is_suspended: Mapped[bool] = mapped_column(default=False, nullable=False)
    data_status: Mapped[str] = mapped_column(String(32), default="normal", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
