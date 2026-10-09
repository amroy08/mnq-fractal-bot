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


def add_ready_short_c4(
    runner,
    end_time=None,
):
    if end_time is None:
        end_time = (
            NOW + timedelta(hours=1)
        )

    setup = Setup(
        is_bullish=False,

        is_confirmed=True,
        cisd_triggered=True,
        is_post_c2=True,

        sweep_bar_index=100,
        swept_htf_index=5,

        c2_extreme=120,
        c3_extreme=120,

        c4_zone_set=True,
        c4_invalid=False,

        c4_zone_bottom=104,
        c4_zone_top=108,

        c4_start_time=NOW,
        c4_end_time=end_time,

        liq_c1_price=100,
        liq_c0_price=90,
    )

    runner.engine.completed_setups.append(
        setup
    )

    return setup


def test_ready_model_automatically_submits_order():
    runner = BotRunner()

    add_ready_short_c4(
        runner
    )

    snapshot = runner.on_candle(
        make_candle(
            timestamp=NOW,
        )
    )

    assert snapshot.order_submitted is True

    assert snapshot.pending_order is not None

    assert snapshot.position is None

    assert (
        snapshot.pending_order.direction
        == "SHORT"
    )

    assert (
        snapshot.pending_order.entry_price
        == 106
    )


def test_new_signal_does_not_fill_on_signal_candle():
    runner = BotRunner()

    add_ready_short_c4(
        runner
    )

    # This candle already contains entry 106.
    #
    # But the Fractal signal is only produced
    # after this candle is processed.
    #
    # Therefore it must remain pending.
    snapshot = runner.on_candle(
        make_candle(
            timestamp=NOW,
            high=110,
            low=102,
        )
    )

    assert snapshot.order_submitted is True
    assert snapshot.pending_order is not None
    assert snapshot.position is None


def test_next_candle_can_fill_entry():
    runner = BotRunner()

    add_ready_short_c4(
        runner
    )

    # Signal candle.
    runner.on_candle(
        make_candle(
            timestamp=NOW,
        )
    )

    # Next candle touches entry 106.
    snapshot = runner.on_candle(
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

    assert snapshot.position is not None
    assert snapshot.pending_order is None

    assert (
        snapshot.position.entry_price
        == 106
    )

    assert any(
        event.event_type
        == "ENTRY_FILLED"
        for event in snapshot.events
    )


def test_runner_manages_trade_to_target():
    runner = BotRunner()

    add_ready_short_c4(
        runner
    )

    # Signal candle.
    runner.on_candle(
        make_candle(
            timestamp=NOW,
        )
    )

    # Entry candle.
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

    # Target candle.
    snapshot = runner.on_candle(
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

    assert snapshot.position is None

    assert (
        snapshot.closed_trade_count
        == 1
    )

    trade = (
        runner.broker.closed_trades[0]
    )

    assert trade.exit_reason == "TARGET"

    # Entry 106
    # Target 100
    #
    # 6 points x $2
    # = $12 gross paper P&L.
    assert trade.gross_pnl == 12


def test_stale_pending_order_is_cancelled():
    runner = BotRunner()

    setup = add_ready_short_c4(
        runner
    )

    first = runner.on_candle(
        make_candle(
            timestamp=NOW,
        )
    )

    assert first.pending_order is not None

    # Simulate model disappearing before
    # the next bar closes.
    runner.engine.completed_setups.remove(
        setup
    )

    # Valid OHLC candle:
    #
    # Low   = 103
    # Open  = 104
    # Close = 104
    # High  = 105
    #
    # Entry is 106, so entry is NOT touched.
    snapshot = runner.on_candle(
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

    assert snapshot.pending_order is None
    assert snapshot.position is None

    assert any(
        event.event_type
        == "ORDER_CANCELLED"
        for event in snapshot.events
    )


def test_no_valid_target_does_not_submit_order():
    runner = BotRunner()

    setup = add_ready_short_c4(
        runner
    )

    # Both targets are on the WRONG side
    # for a short entry around 106.
    setup.liq_c1_price = 130
    setup.liq_c0_price = 140

    snapshot = runner.on_candle(
        make_candle(
            timestamp=NOW,
        )
    )

    assert snapshot.engine.trade_plan is not None

    assert (
        snapshot.engine
        .trade_plan
        .model_ready
        is True
    )

    assert (
        snapshot.engine
        .trade_plan
        .bot_trade_ready
        is False
    )

    assert snapshot.order_submitted is False
    assert snapshot.pending_order is None


def test_c4_order_uses_c4_expiry():
    runner = BotRunner()

    expiry = (
        NOW + timedelta(minutes=30)
    )

    add_ready_short_c4(
        runner,
        end_time=expiry,
    )

    snapshot = runner.on_candle(
        make_candle(
            timestamp=NOW,
        )
    )

    assert snapshot.pending_order is not None

    assert (
        snapshot.pending_order.expires_at
        == expiry
    )


def test_order_expires_automatically():
    runner = BotRunner()

    expiry = (
        NOW + timedelta(minutes=10)
    )

    add_ready_short_c4(
        runner,
        end_time=expiry,
    )

    # Signal creates pending order.
    runner.on_candle(
        make_candle(
            timestamp=NOW,
        )
    )

    # No entry touch before expiry.
    #
    # Entry is 106.
    # This candle only reaches 105.
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

    # At expiry.
    #
    # Still no entry touch.
    snapshot = runner.on_candle(
        make_candle(
            timestamp=expiry,
            open_price=104,
            high=105,
            low=103,
            close=104,
        )
    )

    assert snapshot.pending_order is None
    assert snapshot.position is None

    assert any(
        event.event_type
        == "ORDER_EXPIRED"
        for event in snapshot.events
    )