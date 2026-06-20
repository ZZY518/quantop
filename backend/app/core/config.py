from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "quantop"
    api_prefix: str = "/api"
    database_url: str | None = None
    data_source: str = "akshare"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    model_config = {"env_prefix": "QUANTOP_"}

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        root = Path(__file__).resolve().parents[3]
        db_path = root / "data" / "quantop.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path.as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
