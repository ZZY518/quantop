from app.core.config import get_settings

SUPPORTED_DATA_SOURCES = ("akshare", "baostock")

_data_source: str | None = None


def get_data_source() -> str:
    return _data_source or get_settings().data_source


def set_data_source(value: str) -> str:
    if value not in SUPPORTED_DATA_SOURCES:
        raise ValueError(f"Unsupported data source: {value}")
    global _data_source
    _data_source = value
    return _data_source
