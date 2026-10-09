from datetime import datetime, timezone

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.models.setup import Setup
from mnq_fractal_bot.strategy.post_c2 import (
    update_post_c2_setup,
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


def test_bearish_break_before_cisd_requires_replacement():
    setup = Setup(
        is_bullish=False,
        is_post_c2=True,
        c2_extreme=120,
        cisd_triggered=False,
    )

    candles = [
        make_candle(
            115,
            121,
            110,
            118,
        )
    ]

    result = update_post_c2_setup(
        setup=setup,
        candles=candles,
        current_index=0,
    )

    assert result.replacement_required is True
    assert result.setup.is_invalid is False


def test_bearish_break_after_cisd_invalidates():
    setup = Setup(
        is_bullish=False,
        is_post_c2=True,
        c2_extreme=120,
        cisd_triggered=True,
    )

    candles = [
        make_candle(
            115,
            121,
            110,
            118,
        )
    ]

    result = update_post_c2_setup(
        setup=setup,
        candles=candles,
        current_index=0,
    )

    assert result.replacement_required is False
    assert result.setup.is_invalid is True


def test_bullish_break_before_cisd_requires_replacement():
    setup = Setup(
        is_bullish=True,
        is_post_c2=True,
        c2_extreme=100,
        cisd_triggered=False,
    )

    candles = [
        make_candle(
            105,
            110,
            99,
            102,
        )
    ]

    result = update_post_c2_setup(
        setup=setup,
        candles=candles,
        current_index=0,
    )

    assert result.replacement_required is True
    assert result.setup.is_invalid is False


def test_bearish_cisd_can_trigger_during_c3():
    setup = Setup(
        is_bullish=False,
        is_post_c2=True,
        c2_extreme=120,
        c2_mid=112,
        c3_open=110,
        has_cisd=True,
        cisd_triggered=False,
        cisd_level=105,
        cisd_start_index=0,
        extreme_bar_index=0,
    )

    candles = [
        make_candle(
            110,
            115,
            100,
            104,
        )
    ]

    result = update_post_c2_setup(
        setup=setup,
        candles=candles,
        current_index=0,
    )

    assert result.setup.cisd_triggered is True
    assert result.setup.cisd_end_index == 0
    assert result.setup.c3_zone_set is True