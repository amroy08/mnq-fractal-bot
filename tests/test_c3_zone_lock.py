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

from mnq_fractal_bot.strategy.entry_zones import (
    set_c3_entry_zone,
)


START = datetime(
    2026,
    1,
    1,
    tzinfo=timezone.utc,
)


def make_candle(
    index: int,
    open_price: float,
    close_price: float,
) -> Candle:
    return Candle(
        timestamp=(
            START
            + timedelta(
                minutes=index * 5
            )
        ),

        open=open_price,

        high=max(
            open_price,
            close_price,
        ) + 10,

        low=min(
            open_price,
            close_price,
        ) - 10,

        close=close_price,

        volume=100,
    )


def make_setup() -> Setup:
    setup = Setup(
        is_bullish=True,
        sweep_price=99,
        sweep_bar_index=0,
        swept_htf_index=0,
    )

    setup.is_post_c2 = True
    setup.is_confirmed = True
    setup.cisd_triggered = True

    setup.c2_mid = 105
    setup.c3_open = 120

    setup.cisd_start_index = 0
    setup.extreme_bar_index = 1

    return setup


def test_c3_zone_is_created_once():
    candles = [
        make_candle(
            0,
            100,
            110,
        ),

        make_candle(
            1,
            108,
            112,
        ),
    ]

    setup = make_setup()

    set_c3_entry_zone(
        setup=setup,
        candles=candles,
    )

    original_bottom = (
        setup.c3_zone_bottom
    )

    original_top = (
        setup.c3_zone_top
    )

    assert (
        setup.c3_zone_set
        is True
    )

    # Deliberately change inputs that WOULD
    # produce a different zone if Python
    # recalculated it.
    setup.c2_mid = 500
    setup.c3_open = 600

    changed_candles = [
        make_candle(
            0,
            400,
            450,
        ),

        make_candle(
            1,
            450,
            475,
        ),
    ]

    set_c3_entry_zone(
        setup=setup,
        candles=changed_candles,
    )

    # Must remain frozen exactly like Pine.
    assert (
        setup.c3_zone_bottom
        == original_bottom
    )

    assert (
        setup.c3_zone_top
        == original_top
    )


def test_existing_c3_zone_is_not_overwritten():
    setup = make_setup()

    setup.c3_zone_set = True
    setup.c3_zone_bottom = 100.25
    setup.c3_zone_top = 110.75

    candles = [
        make_candle(
            0,
            200,
            250,
        ),

        make_candle(
            1,
            250,
            300,
        ),
    ]

    set_c3_entry_zone(
        setup=setup,
        candles=candles,
    )

    assert (
        setup.c3_zone_bottom
        == 100.25
    )

    assert (
        setup.c3_zone_top
        == 110.75
    )