from datetime import datetime, timedelta, timezone

import pytest

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.strategy.cisd import (
    candle_attitude,
    find_cisd_level,
)


BASE_TIME = datetime(
    2026,
    10,
    9,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_candle(
    index,
    open_price,
    close,
):
    high = max(open_price, close) + 5
    low = min(open_price, close) - 5

    return Candle(
        timestamp=BASE_TIME
        + timedelta(minutes=index * 5),
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=100,
    )


def test_candle_attitude():
    bullish = make_candle(
        0,
        100,
        105,
    )

    bearish = make_candle(
        1,
        105,
        100,
    )

    doji = make_candle(
        2,
        100,
        100,
    )

    assert candle_attitude(bullish) == 1
    assert candle_attitude(bearish) == -1
    assert candle_attitude(doji) == 0


def test_find_bearish_setup_cisd():
    candles = [
        make_candle(0, 110, 105),
        make_candle(1, 101, 103),
        make_candle(2, 103, 105),
        make_candle(3, 105, 108),
    ]

    result = find_cisd_level(
        candles=candles,
        extreme_index=3,
        bias=1,
    )

    assert result is not None

    assert result.price == 101
    assert result.start_index == 1


def test_find_bullish_setup_cisd():
    candles = [
        make_candle(0, 100, 105),
        make_candle(1, 110, 108),
        make_candle(2, 108, 106),
        make_candle(3, 106, 102),
    ]

    result = find_cisd_level(
        candles=candles,
        extreme_index=3,
        bias=-1,
    )

    assert result is not None

    assert result.price == 110
    assert result.start_index == 1


def test_doji_is_skipped():
    candles = [
        make_candle(0, 110, 105),
        make_candle(1, 101, 103),
        make_candle(2, 104, 104),
        make_candle(3, 105, 108),
    ]

    result = find_cisd_level(
        candles=candles,
        extreme_index=3,
        bias=1,
    )

    assert result is not None

    assert result.price == 101
    assert result.start_index == 1


def test_no_matching_candle_returns_none():
    candles = [
        make_candle(0, 110, 105),
        make_candle(1, 108, 104),
        make_candle(2, 106, 102),
    ]

    result = find_cisd_level(
        candles=candles,
        extreme_index=2,
        bias=1,
    )

    assert result is None


def test_invalid_bias_is_rejected():
    candles = [
        make_candle(0, 100, 105),
    ]

    with pytest.raises(ValueError):
        find_cisd_level(
            candles=candles,
            extreme_index=0,
            bias=5,
        )