from datetime import datetime, timedelta, timezone

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.models.setup import Setup
from mnq_fractal_bot.strategy.entry_zones import (
    get_cisd_body_range,
    set_c3_entry_zone,
    start_post_c2_phase,
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
    high,
    low,
    close,
):
    return Candle(
        timestamp=BASE_TIME
        + timedelta(minutes=index * 5),
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=100,
    )


def test_get_cisd_body_range():
    candles = [
        make_candle(
            0,
            100,
            110,
            95,
            105,
        ),
        make_candle(
            1,
            105,
            115,
            100,
            110,
        ),
        make_candle(
            2,
            110,
            120,
            105,
            108,
        ),
    ]

    body_low, body_high, body_mid = (
        get_cisd_body_range(
            candles,
            0,
            2,
        )
    )

    assert body_low == 100
    assert body_high == 110
    assert body_mid == 105


def test_c3_zone_uses_body_mid_when_c2_mid_inside():
    candles = [
        make_candle(
            0,
            100,
            110,
            95,
            105,
        ),
        make_candle(
            1,
            105,
            115,
            100,
            110,
        ),
        make_candle(
            2,
            110,
            120,
            105,
            108,
        ),
    ]

    setup = Setup(
        is_bullish=False,
        is_post_c2=True,
        cisd_triggered=True,
        cisd_start_index=0,
        extreme_bar_index=2,
        c2_mid=107,
        c3_open=112,
    )

    result = set_c3_entry_zone(
        setup,
        candles,
    )

    assert result.c3_zone_set is True
    assert result.c3_zone_bottom == 105
    assert result.c3_zone_top == 107


def test_c3_zone_uses_c3_open_when_c2_mid_outside():
    candles = [
        make_candle(
            0,
            100,
            110,
            95,
            105,
        ),
        make_candle(
            1,
            105,
            115,
            100,
            110,
        ),
    ]

    setup = Setup(
        is_bullish=False,
        is_post_c2=True,
        cisd_triggered=True,
        cisd_start_index=0,
        extreme_bar_index=1,
        c2_mid=120,
        c3_open=112,
    )

    result = set_c3_entry_zone(
        setup,
        candles,
    )

    assert result.c3_zone_set is True
    assert result.c3_zone_bottom == 112
    assert result.c3_zone_top == 120


def test_bearish_c2_moves_to_post_c2():
    candles = [
        make_candle(
            0,
            100,
            110,
            95,
            105,
        ),
        make_candle(
            1,
            105,
            115,
            100,
            110,
        ),
    ]

    setup = Setup(
        is_bullish=False,
        sweep_price=114,
    )

    completed_c2 = make_candle(
        2,
        113,
        120,
        105,
        110,
    )

    result = start_post_c2_phase(
        setup=setup,
        completed_c2=completed_c2,
        c3_open=111,
        c3_start_time=BASE_TIME,
        candles=candles,
    )

    assert result is not None
    assert result.is_post_c2 is True
    assert result.is_confirmed is True
    assert result.c2_extreme == 120
    assert result.c2_mid == 112.5
    assert result.c3_open == 111


def test_unconfirmed_c2_is_removed():
    candles = []

    setup = Setup(
        is_bullish=False,
        sweep_price=114,
    )

    completed_c2 = make_candle(
        2,
        113,
        120,
        105,
        116,
    )

    result = start_post_c2_phase(
        setup=setup,
        completed_c2=completed_c2,
        c3_open=117,
        c3_start_time=BASE_TIME,
        candles=candles,
    )

    assert result is None