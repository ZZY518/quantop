from __future__ import annotations

import pandas as pd


FACTOR_VERSION = "v2"


def calculate_factors(rows: list[dict]) -> list[dict]:
    if not rows:
        return []

    df = pd.DataFrame(rows).sort_values("trade_date").reset_index(drop=True)
    close = pd.to_numeric(df["close"])

    for window in (5, 10, 20, 60):
        df[f"ma{window}"] = close.rolling(window=window, min_periods=1).mean()

    df["rsi6"] = _rsi(close, 6)
    df["rsi12"] = _rsi(close, 12)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    df["return_1d"] = close.pct_change(1)
    df["return_5d"] = close.pct_change(5)
    df["return_20d"] = close.pct_change(20)
    df["volatility_20d"] = df["return_1d"].rolling(window=20, min_periods=2).std()
    ma_spread = (df["ma5"] / df["ma20"] - 1).replace([pd.NA, pd.NaT], 0)
    price_ma20_spread = (close / df["ma20"] - 1).replace([pd.NA, pd.NaT], 0)
    price_ma60_spread = (close / df["ma60"] - 1).replace([pd.NA, pd.NaT], 0)
    trend_raw = price_ma20_spread * 0.45 + ma_spread * 0.35 + price_ma60_spread * 0.2
    df["score_trend"] = _linear_score(trend_raw, low=-0.08, high=0.08)

    return_60d = close.pct_change(60)
    momentum_raw = (
        df["return_20d"].fillna(0).clip(-0.2, 0.2) * 0.45
        + return_60d.fillna(df["return_20d"]).fillna(0).clip(-0.35, 0.35) * 0.35
        + ((df["rsi6"].fillna(50).clip(0, 100) - 50) / 100) * 0.2
    )
    df["score_momentum"] = _linear_score(momentum_raw, low=-0.18, high=0.18)

    risk_raw = df["volatility_20d"].fillna(df["volatility_20d"].median()).fillna(0.02)
    df["score_risk"] = (100 - risk_raw.clip(0.01, 0.08).sub(0.01).div(0.07).mul(100)).clip(0, 100)
    df["total_score"] = (
        df["score_trend"].fillna(0) * 0.35
        + df["score_momentum"].fillna(50) * 0.4
        + df["score_risk"].fillna(50) * 0.25
    )

    result = []
    for record in df.to_dict(orient="records"):
        result.append(
            {
                "symbol": record["symbol"],
                "trade_date": record["trade_date"],
                "ma5": _clean(record.get("ma5")),
                "ma10": _clean(record.get("ma10")),
                "ma20": _clean(record.get("ma20")),
                "ma60": _clean(record.get("ma60")),
                "rsi6": _clean(record.get("rsi6")),
                "rsi12": _clean(record.get("rsi12")),
                "macd": _clean(record.get("macd")),
                "macd_signal": _clean(record.get("macd_signal")),
                "macd_hist": _clean(record.get("macd_hist")),
                "return_1d": _clean(record.get("return_1d")),
                "return_5d": _clean(record.get("return_5d")),
                "return_20d": _clean(record.get("return_20d")),
                "volatility_20d": _clean(record.get("volatility_20d")),
                "score_trend": _clean(record.get("score_trend")),
                "score_momentum": _clean(record.get("score_momentum")),
                "score_risk": _clean(record.get("score_risk")),
                "total_score": _clean(record.get("total_score")),
                "factor_version": FACTOR_VERSION,
            }
        )
    return result


def calculate_daily_factors(rows: list[dict]) -> list[dict]:
    return calculate_factors(rows)


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window=window, min_periods=1).mean()
    loss = (-delta.clip(upper=0)).rolling(window=window, min_periods=1).mean()
    rs = gain / loss.replace(0, pd.NA)
    return (100 - (100 / (1 + rs))).fillna(100)


def _linear_score(series: pd.Series, low: float, high: float) -> pd.Series:
    return ((series.clip(low, high) - low) / (high - low) * 100).clip(0, 100)


def _clean(value):
    if pd.isna(value):
        return None
    return round(float(value), 6)
