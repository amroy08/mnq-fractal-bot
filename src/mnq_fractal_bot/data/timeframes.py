TIMEFRAME_MAP = {
    "1s": "1m",
    "15s": "5m",
    "1m": "15m",
    "3m": "30m",
    "5m": "1h",
    "15m": "4h",
    "30m": "4h",
    "1h": "1d",
    "2h": "1d",
    "4h": "1w",
    "1d": "1M",
    "1w": "3M",
    "1M": "12M",
}


def get_higher_timeframe(lower_timeframe: str) -> str:
    try:
        return TIMEFRAME_MAP[lower_timeframe]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported lower timeframe: {lower_timeframe}"
        ) from exc