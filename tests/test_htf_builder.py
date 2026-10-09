from datetime import datetime, timedelta, timezone

import pytest

from mnq_fractal_bot.data.htf_builder import build_htf_candle
from mnq_fractal_bot.models.candle import Candle


def test_builds_1h_candle_from_12_5m_candles():
    start_time = datetime(
        2026,
        10,
        9,
        13,
        0,
        tzinfo=timezone.utc,
    )

    candles = []

    for i in range(12):
        candle = Candle(
            timestamp=start_time + timedelta(minutes=5 * i),
            open=31200 + i,
            high=31210 + i,
            low=31190 - i,
            close=31205 + i,
            volume=100 + i,
        )

        candles.append(candle)

    htf_candle = build_htf_candle(candles)

    assert htf_candle.timestamp == start_time

    assert htf_candle.open == 31200

    assert htf_candle.high == 31221

    assert htf_candle.low == 31179

    assert htf_candle.close == 31216

    assert htf_candle.volume == 1266


def test_rejects_empty_candle_list():
    with pytest.raises(ValueError):
        build_htf_candle([])