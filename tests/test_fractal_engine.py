from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.strategy.fractal_engine import (
    FractalEngine,
)


NY = ZoneInfo(
    "America/New_York"
)


def make_candle(
    timestamp,
    open_price,
    high,
    low,
    close,
    volume=100,
):
    return Candle(
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def test_engine_maps_5m_to_1h():
    engine = FractalEngine(
        "5m"
    )

    assert (
        engine.lower_timeframe
        == "5m"
    )

    assert (
        engine.higher_timeframe
        == "1h"
    )


def test_engine_maps_15m_to_4h():
    engine = FractalEngine(
        "15m"
    )

    assert (
        engine.higher_timeframe
        == "4h"
    )


def test_no_setup_before_completed_htf_exists():
    engine = FractalEngine(
        "5m"
    )

    candle = make_candle(
        datetime(
            2026,
            10,
            9,
            18,
            0,
            tzinfo=NY,
        ),
        100,
        110,
        90,
        105,
    )

    snapshot = engine.on_candle(
        candle
    )

    assert (
        snapshot.previous_completed_htf
        is None
    )

    assert (
        snapshot.bearish_setup
        is None
    )

    assert (
        snapshot.bullish_setup
        is None
    )


def test_engine_creates_bearish_sweep_setup():
    engine = FractalEngine(
        "5m"
    )

    start = datetime(
        2026,
        10,
        9,
        18,
        0,
        tzinfo=NY,
    )

    # --------------------------------------------------
    # BUILD FIRST COMPLETED 1H CANDLE
    #
    # High = 110
    # Low  = 90
    # --------------------------------------------------
    for i in range(12):
        candle = make_candle(
            start
            + timedelta(
                minutes=i * 5
            ),
            100,
            110,
            90,
            105,
        )

        engine.on_candle(
            candle
        )

    # --------------------------------------------------
    # 19:00 starts the new 1H candle.
    #
    # High breaches previous 110.
    # Close returns below 110.
    #
    # Therefore:
    # bearish sweep confirmed.
    # --------------------------------------------------
    sweep_candle = make_candle(
        start
        + timedelta(hours=1),
        105,
        115,
        100,
        108,
    )

    snapshot = engine.on_candle(
        sweep_candle
    )

    assert (
        snapshot.previous_completed_htf
        is not None
    )

    assert (
        snapshot.previous_completed_htf.high
        == 110
    )

    assert (
        snapshot.previous_completed_htf.low
        == 90
    )

    assert (
        snapshot.bearish_setup
        is not None
    )

    setup = (
        snapshot.bearish_setup
    )

    assert (
        setup.is_bullish
        is False
    )

    assert (
        setup.is_confirmed
        is True
    )

    assert (
        setup.sweep_price
        == 110
    )

    assert (
        setup.tracked_extreme
        == 115
    )

    assert (
        setup.liq_c1_price
        == 90
    )


def test_existing_bearish_setup_tracks_new_high():
    engine = FractalEngine(
        "5m"
    )

    start = datetime(
        2026,
        10,
        9,
        18,
        0,
        tzinfo=NY,
    )

    # Build previous 1H.
    for i in range(12):
        engine.on_candle(
            make_candle(
                start
                + timedelta(
                    minutes=i * 5
                ),
                100,
                110,
                90,
                105,
            )
        )

    # Initial sweep.
    engine.on_candle(
        make_candle(
            start
            + timedelta(hours=1),
            105,
            115,
            100,
            108,
        )
    )

    # Next LTF candle creates
    # a higher C2 extreme.
    snapshot = engine.on_candle(
        make_candle(
            start
            + timedelta(
                hours=1,
                minutes=5,
            ),
            108,
            120,
            102,
            109,
        )
    )

    assert (
        snapshot.bearish_setup
        is not None
    )

    assert (
        snapshot.bearish_setup.tracked_extreme
        == 120
    )