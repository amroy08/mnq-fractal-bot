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


def build_first_hour(
    engine,
    start,
):
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


def test_c2_close_moves_bearish_setup_into_c3():
    engine = FractalEngine("5m")

    start = datetime(
        2026,
        10,
        9,
        18,
        0,
        tzinfo=NY,
    )

    build_first_hour(
        engine,
        start,
    )

    # 19:00 sweep previous HTF high 110.
    engine.on_candle(
        make_candle(
            start + timedelta(hours=1),
            105,
            115,
            100,
            108,
        )
    )

    # Finish C2 hour without breaking higher.
    for minute in range(
        5,
        60,
        5,
    ):
        engine.on_candle(
            make_candle(
                start
                + timedelta(
                    hours=1,
                    minutes=minute,
                ),
                108,
                115,
                100,
                108,
            )
        )

    # 20:00 starts C3.
    snapshot = engine.on_candle(
        make_candle(
            start + timedelta(hours=2),
            108,
            114,
            101,
            107,
        )
    )

    assert snapshot.bearish_setup is not None

    setup = snapshot.bearish_setup

    assert setup.is_post_c2 is True
    assert setup.is_confirmed is True
    assert setup.c2_extreme == 115

    assert setup.c2_mid == 107.5
    assert setup.c3_open == 108


def test_unconfirmed_c2_is_removed():
    engine = FractalEngine("5m")

    start = datetime(
        2026,
        10,
        9,
        18,
        0,
        tzinfo=NY,
    )

    build_first_hour(
        engine,
        start,
    )

    # Sweep high, but stay ABOVE sweep level.
    engine.on_candle(
        make_candle(
            start + timedelta(hours=1),
            111,
            115,
            100,
            112,
        )
    )

    for minute in range(
        5,
        60,
        5,
    ):
        engine.on_candle(
            make_candle(
                start
                + timedelta(
                    hours=1,
                    minutes=minute,
                ),
                112,
                115,
                100,
                112,
            )
        )

    snapshot = engine.on_candle(
        make_candle(
            start + timedelta(hours=2),
            112,
            114,
            105,
            110,
        )
    )

    assert snapshot.bearish_setup is None


def test_c3_close_moves_triggered_setup_to_c4_history():
    engine = FractalEngine("5m")

    start = datetime(
        2026,
        10,
        9,
        18,
        0,
        tzinfo=NY,
    )

    build_first_hour(
        engine,
        start,
    )

    engine.on_candle(
        make_candle(
            start + timedelta(hours=1),
            105,
            115,
            100,
            108,
        )
    )

    for minute in range(
        5,
        60,
        5,
    ):
        engine.on_candle(
            make_candle(
                start
                + timedelta(
                    hours=1,
                    minutes=minute,
                ),
                108,
                115,
                100,
                108,
            )
        )

    # Start C3.
    engine.on_candle(
        make_candle(
            start + timedelta(hours=2),
            108,
            114,
            101,
            107,
        )
    )

    assert engine.live_bearish is not None

    # For this orchestration test we mark CISD as
    # confirmed so we can specifically test the
    # C3 -> C4 engine transition.
    engine.live_bearish.has_cisd = True
    engine.live_bearish.cisd_triggered = True

    # Keep C3 below C2 extreme 115.
    for minute in range(
        5,
        60,
        5,
    ):
        engine.on_candle(
            make_candle(
                start
                + timedelta(
                    hours=2,
                    minutes=minute,
                ),
                107,
                114,
                100,
                106,
            )
        )

    # 21:00 starts C4.
    snapshot = engine.on_candle(
        make_candle(
            start + timedelta(hours=3),
            106,
            110,
            102,
            108,
        )
    )

    assert snapshot.bearish_setup is None

    assert len(
        snapshot.completed_setups
    ) == 1

    completed = (
        snapshot.completed_setups[0]
    )

    assert completed.c4_zone_set is True
    assert completed.c3_extreme == 114
    assert completed.c4_open == 106


def test_post_c2_without_cisd_expires_after_c3():
    engine = FractalEngine("5m")

    start = datetime(
        2026,
        10,
        9,
        18,
        0,
        tzinfo=NY,
    )

    build_first_hour(
        engine,
        start,
    )

    engine.on_candle(
        make_candle(
            start + timedelta(hours=1),
            105,
            115,
            100,
            108,
        )
    )

    for minute in range(
        5,
        60,
        5,
    ):
        engine.on_candle(
            make_candle(
                start
                + timedelta(
                    hours=1,
                    minutes=minute,
                ),
                108,
                115,
                100,
                108,
            )
        )

    engine.on_candle(
        make_candle(
            start + timedelta(hours=2),
            108,
            114,
            101,
            107,
        )
    )

    # Explicitly keep CISD untriggered.
    assert engine.live_bearish is not None
    engine.live_bearish.cisd_triggered = False

    for minute in range(
        5,
        60,
        5,
    ):
        engine.on_candle(
            make_candle(
                start
                + timedelta(
                    hours=2,
                    minutes=minute,
                ),
                107,
                114,
                100,
                106,
            )
        )

    snapshot = engine.on_candle(
        make_candle(
            start + timedelta(hours=3),
            106,
            110,
            102,
            108,
        )
    )

    assert snapshot.bearish_setup is None

    assert len(
        snapshot.completed_setups
    ) == 0