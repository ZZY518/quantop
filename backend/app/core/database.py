from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.constants import DEFAULT_ADJUST
from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(
    settings.resolved_database_url,
    connect_args={"check_same_thread": False}
    if settings.resolved_database_url.startswith("sqlite")
    else {},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema()


def ensure_sqlite_schema() -> None:
    if not settings.resolved_database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table in ("dwd_stock_daily", "dwd_stock_bar"):
            if table not in existing_tables:
                continue
            columns = {column["name"] for column in inspector.get_columns(table)}
            if "adjust" not in columns:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN adjust VARCHAR(16) NOT NULL DEFAULT '{DEFAULT_ADJUST}'"))
            conn.execute(text(f"UPDATE {table} SET adjust = :adjust WHERE adjust IS NULL OR adjust = ''"), {"adjust": DEFAULT_ADJUST})
