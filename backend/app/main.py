from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.models.sync_log import SyncTaskLog

settings = get_settings()

app = FastAPI(title="quantop API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_prefix)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    mark_interrupted_sync_tasks()


def mark_interrupted_sync_tasks() -> None:
    db = SessionLocal()
    try:
        rows = db.query(SyncTaskLog).filter(SyncTaskLog.status == "running").all()
        for row in rows:
            row.status = "failed"
            row.end_time = row.end_time or row.start_time
            row.error_message = "backend restarted before task completed"
        if rows:
            db.commit()
    finally:
        db.close()
