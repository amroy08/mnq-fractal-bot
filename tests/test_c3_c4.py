from datetime import datetime, timezone

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.models.setup import Setup
from mnq_fractal_bot.strategy.c3_c4 import (
    start_c4_phase,
    update_c3_invalidation,
    update_c4_invalidation,
)


NOW = datetime(
    2026,
    10,
    9,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_candle(
    open_price,
    high,
    low,
    close,
):
    return Candle(
        timestamp=NOW,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=100,
    )


def test_bearish_c3_invalidates_above_c2_extreme():
    setup = Setup(
        is_bullish=False,
        is_post_c2=True,
        c2_extreme=120,
    )

    candle = make_candle(
        115,
        121,
        110,
        118,
    )

    result = update_c3_invalidation(
        setup,
        candle,
    )

    assert result.is_invalid is True


def test_bullish_c3_invalidates_below_c2_extreme():
    setup = Setup(
        is_bullish=True,
        is_post_c2=True,
        c2_extreme=100,
    )

    candle = make_candle(
        105,
        110,
        99,
        102,
    )

    result = update_c3_invalidation(
        setup,
        candle,
    )

    assert result.is_invalid is True


def test_bearish_c4_zone_is_created():
    setup = Setup(
        is_bullish=False,
        is_post_c2=True,
        cisd_triggered=True,
    )

    c3 = make_candle(
        110,
        120,
        100,
        108,
    )

    result = start_c4_phase(
        setup=setup,
        completed_c3=c3,
        c4_open=106,
        c4_start_time=NOW,
        c4_end_time=NOW,
    )

    # C3 midpoint:
    # (120 + 100) / 2 = 110

    assert result.c3_mid == 110
    assert result.c3_extreme == 120

    assert result.c4_open == 106

    assert result.c4_zone_set is True
    assert result.c4_zone_bottom == 106
    assert result.c4_zone_top == 110


def test_bullish_c4_zone_is_created():
    setup = Setup(
        is_bullish=True,
        is_post_c2=True,
        cisd_triggered=True,
    )

    c3 = make_candle(
        105,
        120,
        100,
        115,
    )

    result = start_c4_phase(
        setup=setup,
        completed_c3=c3,
        c4_open=112,
        c4_start_time=NOW,
        c4_end_time=NOW,
    )

    assert result.c3_mid == 110
    assert result.c3_extreme == 100

    assert result.c4_zone_set is True
    assert result.c4_zone_bottom == 110
    assert result.c4_zone_top == 112


def test_bearish_c4_invalidates_above_c3_high():
    setup = Setup(
        is_bullish=False,
        c4_zone_set=True,
        c3_extreme=120,
    )

    candle = make_candle(
        115,
        121,
        110,
        118,
    )

    result = update_c4_invalidation(
        setup,
        candle,
    )

    assert result.c4_invalid is True


def test_bullish_c4_invalidates_below_c3_low():
    setup = Setup(
        is_bullish=True,
        c4_zone_set=True,
        c3_extreme=100,
    )

    candle = make_candle(
        105,
        110,
        99,
        102,
    )

    result = update_c4_invalidation(
        setup,
        candle,
    )

    assert result.c4_invalid is True