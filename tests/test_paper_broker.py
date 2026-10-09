from datetime import (
    datetime,
    timedelta,
    timezone,
)

from mnq_fractal_bot.execution.paper_broker import (
    PaperBroker,
)

from mnq_fractal_bot.models.candle import Candle

from mnq_fractal_bot.strategy.trade_plan import (
    TradePlan,
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
    high,
    low,
    timestamp=NOW,
):
    return Candle(
        timestamp=timestamp,
        open=(high + low) / 2,
        high=high,
        low=low,
        close=(high + low) / 2,
        volume=100,
    )


def make_short_plan(
    ready=True,
):
    return TradePlan(
        direction="SHORT",

        entry_name="C4 ENTRY ZONE",

        entry_bottom=108,
        entry_top=112,
        entry_price=110,

        stop_price=120,

        tp_c1=100,
        tp_c0=90,
        preferred_target=100,

        model_ready=True,
        has_valid_target=True,

        bot_trade_ready=ready,
    )


def make_long_plan(
    ready=True,
):
    return TradePlan(
        direction="LONG",

        entry_name="C3 ENTRY ZONE",

        entry_bottom=108,
        entry_top=112,
        entry_price=110,

        stop_price=100,

        tp_c1=120,
        tp_c0=130,
        preferred_target=120,

        model_ready=True,
        has_valid_target=True,

        bot_trade_ready=ready,
    )


def test_non_ready_plan_is_rejected():
    broker = PaperBroker()

    accepted = broker.submit_trade_plan(
        plan=make_short_plan(
            ready=False,
        ),
        signal_id="setup-1",
    )

    assert accepted is False

    assert broker.pending_order is None


def test_ready_plan_creates_pending_order():
    broker = PaperBroker()

    accepted = broker.submit_trade_plan(
        plan=make_short_plan(),
        signal_id="setup-1",
    )

    assert accepted is True

    assert broker.pending_order is not None

    assert (
        broker.pending_order.entry_price
        == 110
    )

    assert (
        broker.pending_order.quantity
        == 1
    )


def test_duplicate_signal_is_rejected():
    broker = PaperBroker()

    broker.submit_trade_plan(
        plan=make_short_plan(),
        signal_id="setup-1",
    )

    # Cancel pending order so the only
    # reason for rejection is duplication.
    broker.cancel_pending_order()

    accepted = broker.submit_trade_plan(
        plan=make_short_plan(),
        signal_id="setup-1",
    )

    assert accepted is False


def test_order_waits_until_entry_is_touched():
    broker = PaperBroker()

    broker.submit_trade_plan(
        plan=make_short_plan(),
        signal_id="setup-1",
    )

    event = broker.on_candle(
        make_candle(
            high=109,
            low=105,
        )
    )

    assert event is None
    assert broker.position is None
    assert broker.pending_order is not None


def test_entry_touch_opens_one_mnq():
    broker = PaperBroker()

    broker.submit_trade_plan(
        plan=make_short_plan(),
        signal_id="setup-1",
    )

    event = broker.on_candle(
        make_candle(
            high=112,
            low=108,
        )
    )

    assert event is not None

    assert (
        event.event_type
        == "ENTRY_FILLED"
    )

    assert broker.position is not None

    assert broker.position.quantity == 1

    assert broker.position.entry_price == 110

    assert broker.pending_order is None


def test_short_target_calculates_mnq_profit():
    broker = PaperBroker()

    broker.submit_trade_plan(
        plan=make_short_plan(),
        signal_id="setup-1",
    )

    # Entry candle.
    broker.on_candle(
        make_candle(
            high=112,
            low=108,
        )
    )

    # Next candle hits target 100.
    event = broker.on_candle(
        make_candle(
            high=109,
            low=99,
            timestamp=(
                NOW + timedelta(minutes=5)
            ),
        )
    )

    assert event is not None

    assert (
        event.event_type
        == "POSITION_TARGET"
    )

    # SHORT:
    #
    # 110 -> 100
    # = 10 points
    #
    # MNQ = $2 / point
    #
    # Gross P&L = $20
    assert event.gross_pnl == 20

    assert broker.position is None

    assert len(
        broker.closed_trades
    ) == 1


def test_long_target_calculates_mnq_profit():
    broker = PaperBroker()

    broker.submit_trade_plan(
        plan=make_long_plan(),
        signal_id="setup-long-1",
    )

    broker.on_candle(
        make_candle(
            high=112,
            low=108,
        )
    )

    event = broker.on_candle(
        make_candle(
            high=121,
            low=109,
            timestamp=(
                NOW + timedelta(minutes=5)
            ),
        )
    )

    assert event is not None

    assert (
        event.event_type
        == "POSITION_TARGET"
    )

    assert event.gross_pnl == 20


def test_stop_loss_records_loss():
    broker = PaperBroker()

    broker.submit_trade_plan(
        plan=make_short_plan(),
        signal_id="setup-1",
    )

    broker.on_candle(
        make_candle(
            high=112,
            low=108,
        )
    )

    event = broker.on_candle(
        make_candle(
            high=121,
            low=105,
            timestamp=(
                NOW + timedelta(minutes=5)
            ),
        )
    )

    assert event is not None

    assert (
        event.event_type
        == "POSITION_STOPPED"
    )

    # SHORT:
    #
    # Entry = 110
    # Stop  = 120
    #
    # -10 points
    # x $2
    # = -$20
    assert event.gross_pnl == -20


def test_when_stop_and_target_both_hit_stop_wins():
    broker = PaperBroker()

    broker.submit_trade_plan(
        plan=make_short_plan(),
        signal_id="setup-1",
    )

    broker.on_candle(
        make_candle(
            high=112,
            low=108,
        )
    )

    # Both:
    #
    # stop 120
    # target 100
    #
    # occur inside this candle.
    event = broker.on_candle(
        make_candle(
            high=121,
            low=99,
            timestamp=(
                NOW + timedelta(minutes=5)
            ),
        )
    )

    assert event is not None

    assert (
        event.event_type
        == "POSITION_STOPPED"
    )

    assert event.gross_pnl == -20


def test_pending_order_can_expire():
    broker = PaperBroker()

    expiry = (
        NOW + timedelta(minutes=10)
    )

    broker.submit_trade_plan(
        plan=make_short_plan(),
        signal_id="setup-1",
        expires_at=expiry,
    )

    event = broker.on_candle(
        make_candle(
            high=112,
            low=108,
            timestamp=expiry,
        )
    )

    assert event is not None

    assert (
        event.event_type
        == "ORDER_EXPIRED"
    )

    assert broker.pending_order is None
    assert broker.position is None