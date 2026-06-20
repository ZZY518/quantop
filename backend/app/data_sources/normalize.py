from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

PRICE_FIELDS = ("open", "high", "low", "close")


def normalize_price_series(rows: list[dict], jump_threshold: float = 0.25) -> list[dict]:
    if len(rows) < 2:
        return rows

    normalized = deepcopy(rows)
    changed = True
    while changed:
        changed = False
        for index in range(len(normalized) - 1, 0, -1):
            previous_close = normalized[index - 1].get("close")
            current_close = normalized[index].get("close")
            if previous_close in (None, 0) or current_close in (None, 0):
                continue

            ratio = float(current_close) / float(previous_close)
            if abs(ratio - 1.0) <= jump_threshold:
                continue

            factor = Decimal(str(ratio))
            for row in normalized[:index]:
                for field in PRICE_FIELDS:
                    value = row.get(field)
                    if value is not None:
                        row[field] = _mul(value, factor)
            changed = True

    previous_close = None
    for row in normalized:
        close = row.get("close")
        if previous_close is None or close is None:
            row["pre_close"] = close
            row["change_amount"] = None
            row["pct_chg"] = None
        else:
            row["pre_close"] = previous_close
            row["change_amount"] = _sub(close, previous_close)
            row["pct_chg"] = _pct(close, previous_close)
        previous_close = close
    return normalized


def _mul(value, factor: Decimal):
    if isinstance(value, Decimal):
        return value * factor
    return Decimal(str(value)) * factor


def _sub(current, previous):
    if isinstance(current, Decimal) and isinstance(previous, Decimal):
        return current - previous
    return Decimal(str(current)) - Decimal(str(previous))


def _pct(current, previous):
    prev = Decimal(str(previous))
    if prev == 0:
        return None
    return (_sub(current, previous) / prev) * Decimal("100")
