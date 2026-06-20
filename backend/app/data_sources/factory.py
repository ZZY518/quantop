from app.core.runtime_state import get_data_source


class DataSourceNotConfigured(RuntimeError):
    pass


class DataSourceUnavailable(RuntimeError):
    pass


def create_data_source_client():
    data_source = get_data_source()
    if data_source == "akshare":
        from app.data_sources.akshare_client import AkShareDataSourceClient

        return AkShareDataSourceClient()
    if data_source == "baostock":
        from app.data_sources.baostock_client import BaoStockDataSourceClient

        return BaoStockDataSourceClient()
    if data_source == "none":
        raise DataSourceNotConfigured("No real data source is configured. Set QUANTOP_DATA_SOURCE before syncing.")
    raise DataSourceNotConfigured(f"Unsupported data source: {data_source}")
