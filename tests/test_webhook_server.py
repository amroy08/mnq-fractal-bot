import json
from datetime import datetime, timezone
import pytest

from mnq_fractal_bot.data.webhook_server import parse_candle_payload


def test_parse_candle_payload_iso():
    payload = {
        "time": "2026-10-11T12:00:00Z",
        "open": 31200.0,
        "high": 31220.5,
        "low": 31195.0,
        "close": 31215.25,
        "volume": 2500,
    }
    candle = parse_candle_payload(payload)
    assert candle.timestamp == datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
    assert candle.open == 31200.0
    assert candle.high == 31220.5
    assert candle.low == 31195.0
    assert candle.close == 31215.25
    assert candle.volume == 2500.0


def test_parse_candle_payload_unix_ms():
    payload = {
        "timestamp": 1791720000000,  # unix ms
        "open": 30000.0,
        "high": 30010.0,
        "low": 29990.0,
        "close": 30005.0,
    }
    candle = parse_candle_payload(payload)
    assert candle.timestamp.tzinfo == timezone.utc
    assert candle.open == 30000.0
    assert candle.volume == 0.0


def test_parse_candle_payload_missing_time():
    with pytest.raises(ValueError, match="Missing 'time' or 'timestamp'"):
        parse_candle_payload({"open": 100, "high": 105, "low": 95, "close": 102})
