from datetime import datetime, timedelta, timezone

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.models.setup import Setup
from mnq_fractal_bot.strategy.c2_tracker import update_c2_setup


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


def test_bearish_new_high_recalculates_cisd():
    candles = [
        make_candle(0, 110, 112, 104, 105),
        make_candle(1, 101, 104, 100, 103),
        make_candle(2, 103, 106, 102, 105),
        make_candle(3, 105, 113, 104, 108),
    ]

    setup = Setup(
        is_bullish=False,
        sweep_price=112,
        tracked_extreme=110,
        extreme_bar_index=2,
    )

    result = update_c2_setup(
        setup,
        candles,
        current_index=3,
    )

    assert result.tracked_extreme == 113
    assert result.extreme_bar_index == 3

    assert result.has_cisd is True
    assert result.cisd_level == 101
    assert result.cisd_start_index == 1


def test_bullish_new_low_recalculates_cisd():
    candles = [
        make_candle(0, 100, 106, 99, 105),
        make_candle(1, 110, 111, 107, 108),
        make_candle(2, 108, 109, 105, 106),
        make_candle(3, 106, 107, 98, 102),
    ]

    setup = Setup(
        is_bullish=True,
        sweep_price=99,
        tracked_extreme=100,
        extreme_bar_index=2,
    )

    result = update_c2_setup(
        setup,
        candles,
        current_index=3,
    )

    assert result.tracked_extreme == 98
    assert result.extreme_bar_index == 3

    assert result.has_cisd is True
    assert result.cisd_level == 110
    assert result.cisd_start_index == 1


def test_bearish_cisd_triggers_after_confirmed_close():
    candles = [
        make_candle(0, 110, 112, 104, 105),
        make_candle(1, 101, 104, 100, 103),
        make_candle(2, 103, 113, 102, 108),
        make_candle(3, 102, 106, 95, 100),
    ]

    setup = Setup(
        is_bullish=False,
        sweep_price=112,
        tracked_extreme=113,
        extreme_bar_index=2,
        has_cisd=True,
        cisd_level=101,
        cisd_start_index=1,
    )

    result = update_c2_setup(
        setup,
        candles,
        current_index=3,
    )

    assert result.is_confirmed is True
    assert result.cisd_end_index == 3
    assert result.cisd_triggered is True


def test_bullish_cisd_triggers_after_confirmed_close():
    candles = [
        make_candle(0, 100, 106, 99, 105),
        make_candle(1, 110, 111, 107, 108),
        make_candle(2, 108, 109, 98, 102),
        make_candle(3, 109, 115, 105, 111),
    ]

    setup = Setup(
        is_bullish=True,
        sweep_price=99,
        tracked_extreme=98,
        extreme_bar_index=2,
        has_cisd=True,
        cisd_level=110,
        cisd_start_index=1,
    )

    result = update_c2_setup(
        setup,
        candles,
        current_index=3,
    )

    assert result.is_confirmed is True
    assert result.cisd_end_index == 3
    assert result.cisd_triggered is True