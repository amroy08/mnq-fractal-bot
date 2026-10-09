from datetime import datetime, timezone

import pytest

from mnq_fractal_bot.models.candle import Candle


def test_valid_candle():
    candle = Candle(
        timestamp=datetime(2026, 10, 9, 13, 45, tzinfo=timezone.utc),
        open=31210.00,
        high=31235.25,
        low=31202.50,
        close=31228.75,
        volume=4850,
    )

    assert candle.open == 31210.00
    assert candle.high == 31235.25
    assert candle.low == 31202.50
    assert candle.close == 31228.75
    assert candle.volume == 4850


def test_rejects_high_below_open():
    with pytest.raises(ValueError):
        Candle(
            timestamp=datetime.now(timezone.utc),
            open=31210,
            high=31000,
            low=30900,
            close=31225,
            volume=100,
        )


def test_rejects_negative_volume():
    with pytest.raises(ValueError):
        Candle(
            timestamp=datetime.now(timezone.utc),
            open=31210,
            high=31220,
            low=31200,
            close=31215,
            volume=-1,
        )


def test_rejects_timestamp_without_timezone():
    with pytest.raises(ValueError):
        Candle(
            timestamp=datetime(2026, 10, 9, 13, 45),
            open=31210,
            high=31220,
            low=31200,
            close=31215,
            volume=100,
        )