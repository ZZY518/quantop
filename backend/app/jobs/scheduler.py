from apscheduler.schedulers.background import BackgroundScheduler

from app.core.database import SessionLocal
from app.services.sync_service import SyncService


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(run_daily_sync, "cron", hour=18, minute=30, id="daily_sync", replace_existing=True)
    return scheduler


def run_daily_sync() -> None:
    db = SessionLocal()
    try:
        service = SyncService(db)
        service.sync_stock_basic()
        service.sync_stock_daily()
        service.sync_factors()
    finally:
        db.close()
