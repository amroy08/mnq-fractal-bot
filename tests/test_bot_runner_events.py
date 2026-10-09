from datetime import (
    datetime,
    timedelta,
    timezone,
)

from mnq_fractal_bot.execution.bot_runner import (
    BotRunner,
)

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.models.setup import Setup


NOW = datetime(
    2026,
    10,
    9,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_candle(
    timestamp,
    open_price=106,
    high=110,
    low=102,
    close=108,
):
    return Candle(
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=100,
    )


def add_ready_short_setup(
    runner,
):
    setup = Setup(
        is_bullish=False,

        is_confirmed=True,
        cisd_triggered=True,
        is_post_c2=True,

        sweep_price=112,
        cisd_level=109,

        sweep_bar_index=100,
        swept_htf_index=5,

        c2_extreme=120,
        c3_extreme=120,

        c4_zone_set=True,
        c4_invalid=False,

        c4_zone_bottom=104,
        c4_zone_top=108,

        c4_start_time=NOW,
        c4_end_time=(
            NOW + timedelta(hours=1)
        ),

        liq_c1_price=100,
        liq_c0_price=90,
    )

    runner.engine.completed_setups.append(
        setup
    )

    return setup


def test_order_submission_is_recorded():
    runner = BotRunner()

    add_ready_short_setup(
        runner
    )

    snapshot = runner.on_candle(
        make_candle(
            timestamp=NOW,
        )
    )

    assert (
        snapshot.broker_event_count
        == 1
    )

    event = (
        runner
        .broker_event_history[0]
    )

    assert (
        event.event_type
        == "ORDER_SUBMITTED"
    )

    assert event.price == 106

    assert event.timestamp == NOW


def test_entry_fill_is_recorded():
    runner = BotRunner()

    add_ready_short_setup(
        runner
    )

    # Signal + pending order.
    runner.on_candle(
        make_candle(
            timestamp=NOW,
        )
    )

    # Next candle touches entry.
    runner.on_candle(
        make_candle(
            timestamp=(
                NOW
                + timedelta(minutes=5)
            ),
            open_price=106,
            high=108,
            low=104,
            close=107,
        )
    )

    event_types = [
        event.event_type
        for event
        in runner.broker_event_history
    ]

    assert (
        "ORDER_SUBMITTED"
        in event_types
    )

    assert (
        "ENTRY_FILLED"
        in event_types
    )


def test_target_exit_is_recorded():
    runner = BotRunner()

    add_ready_short_setup(
        runner
    )

    # Signal.
    runner.on_candle(
        make_candle(
            timestamp=NOW,
        )
    )

    # Entry.
    runner.on_candle(
        make_candle(
            timestamp=(
                NOW
                + timedelta(minutes=5)
            ),
            open_price=106,
            high=108,
            low=104,
            close=107,
        )
    )

    # Target.
    runner.on_candle(
        make_candle(
            timestamp=(
                NOW
                + timedelta(minutes=10)
            ),
            open_price=104,
            high=105,
            low=99,
            close=101,
        )
    )

    target_events = [
        event
        for event
        in runner.broker_event_history
        if (
            event.event_type
            == "POSITION_TARGET"
        )
    ]

    assert len(target_events) == 1

    assert (
        target_events[0].price
        == 100
    )

    assert (
        target_events[0].gross_pnl
        == 12
    )


def test_stale_order_cancellation_is_recorded():
    runner = BotRunner()

    setup = add_ready_short_setup(
        runner
    )

    runner.on_candle(
        make_candle(
            timestamp=NOW,
        )
    )

    # Remove model so pending order
    # becomes stale.
    runner.engine.completed_setups.remove(
        setup
    )

    runner.on_candle(
        make_candle(
            timestamp=(
                NOW
                + timedelta(minutes=5)
            ),
            open_price=104,
            high=105,
            low=103,
            close=104,
        )
    )

    event_types = [
        event.event_type
        for event
        in runner.broker_event_history
    ]

    assert (
        "ORDER_CANCELLED"
        in event_types
    )