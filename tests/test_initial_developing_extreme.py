from datetime import (
    datetime,
    timedelta,
    timezone,
)

from mnq_fractal_bot.models.candle import (
    Candle,
)

from mnq_fractal_bot.models.setup import (
    Setup,
)

from mnq_fractal_bot.strategy.fractal_engine import (
    FractalEngine,
)


START = datetime(
    2026,
    1,
    1,
    10,
    0,
    tzinfo=timezone.utc,
)


def make_candle(
    minutes: int,
    open_price: float,
    high: float,
    low: float,
    close: float,
) -> Candle:
    return Candle(
        timestamp=(
            START
            + timedelta(
                minutes=minutes
            )
        ),
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=100,
    )


def test_bullish_new_setup_uses_developing_htf_low():
    engine = FractalEngine(
        lower_timeframe="5m",
    )

    engine.htf_builder.current_bucket_start = (
        START
    )

    engine.ltf_candles = [
        make_candle(
            0,
            100,
            105,
            95,
            101,
        ),
        make_candle(
            5,
            101,
            104,
            90,
            99,
        ),
        make_candle(
            10,
            99,
            103,
            93,
            100,
        ),
    ]

    setup = Setup(
        is_bullish=True,
        sweep_price=94,
        sweep_bar_index=2,
        swept_htf_index=5,

        # This is what the old Python
        # candidate initially stored.
        tracked_extreme=93,
        extreme_bar_index=2,
    )

    previous_htf = make_candle(
        -60,
        100,
        110,
        94,
        102,
    )

    result = engine._prepare_new_setup(
        setup=setup,
        previous_htf=previous_htf,
        older_htf=None,
        current_index=2,
    )

    # Pine should use the lowest low
    # of the whole developing HTF.
    assert result.tracked_extreme == 90

    # That low occurred on index 1,
    # not on the sweep-detection bar.
    assert result.extreme_bar_index == 1


def test_bearish_new_setup_uses_developing_htf_high():
    engine = FractalEngine(
        lower_timeframe="5m",
    )

    engine.htf_builder.current_bucket_start = (
        START
    )

    engine.ltf_candles = [
        make_candle(
            0,
            100,
            105,
            95,
            101,
        ),
        make_candle(
            5,
            101,
            112,
            98,
            104,
        ),
        make_candle(
            10,
            104,
            109,
            100,
            103,
        ),
    ]

    setup = Setup(
        is_bullish=False,
        sweep_price=108,
        sweep_bar_index=2,
        swept_htf_index=5,

        # Old Python assumed the
        # current candle was extreme.
        tracked_extreme=109,
        extreme_bar_index=2,
    )

    previous_htf = make_candle(
        -60,
        100,
        108,
        90,
        98,
    )

    result = engine._prepare_new_setup(
        setup=setup,
        previous_htf=previous_htf,
        older_htf=None,
        current_index=2,
    )

    assert result.tracked_extreme == 112

    assert result.extreme_bar_index == 1