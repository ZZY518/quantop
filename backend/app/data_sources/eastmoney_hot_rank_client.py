from __future__ import annotations

import os
import time

import requests

from app.data_sources.factory import DataSourceUnavailable


class EastmoneyHotRankClient:
    source = "eastmoney"

    def __init__(self):
        self._disable_broken_proxy_env()
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://guba.eastmoney.com/rank/",
                "Accept": "application/json, text/plain, */*",
            }
        )

    def get_hot_rank(self, limit: int = 100) -> list[dict]:
        payload = {
            "appId": "appId01",
            "globalId": "786e4c21-70dc-435a-93bb-38",
            "marketType": "",
            "pageNo": 1,
            "pageSize": limit,
        }
        last_error: Exception | None = None
        for _ in range(3):
            try:
                response = self.session.post(
                    "https://emappdata.eastmoney.com/stockrank/getAllCurrentList",
                    json=payload,
                    timeout=20,
                )
                response.raise_for_status()
                data = response.json().get("data", [])
                rows: list[dict] = []
                for item in data[:limit]:
                    rows.append(
                        {
                            "rank": int(item.get("rk") or len(rows) + 1),
                            "symbol": self._to_symbol(item.get("sc")),
                            "name": str(item.get("name") or item.get("n") or ""),
                            "latest_price": None,
                            "change_amount": None,
                            "pct_chg": None,
                        }
                    )
                return rows
            except Exception as exc:
                last_error = exc
                time.sleep(0.5)
        raise DataSourceUnavailable(f"Eastmoney hot rank request failed: {last_error}") from last_error

    def _normalize_code(self, value) -> str:
        code = str(value or "").strip().upper()
        if not code:
            return ""
        if code.startswith(("SH", "SZ", "BJ")):
            code = code[2:]
        return code.zfill(6)

    def _to_symbol(self, code: str) -> str:
        return f"{self._normalize_code(code)}.{self._exchange(code)}"

    def _exchange(self, code: str) -> str:
        raw_code = str(code or "").strip().upper()
        if raw_code.startswith(("SH", "SZ", "BJ")):
            return raw_code[:2]
        normalized_code = self._normalize_code(raw_code)
        if normalized_code.startswith(("6", "9")):
            return "SH"
        if normalized_code.startswith(("4", "8")):
            return "BJ"
        return "SZ"

    def _disable_broken_proxy_env(self) -> None:
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            os.environ.pop(key, None)
