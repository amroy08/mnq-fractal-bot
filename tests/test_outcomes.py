from datetime import (
    datetime,
    timedelta,
    timezone,
)

from mnq_fractal_bot.backtest.audit import (
    build_signal_audit,
)

from mnq_fractal_bot.backtest.outcomes import (
    build_signal_outcomes,
)

from mnq_fractal_bot.execution.bot_runner import (
    RecordedBrokerEvent,
)

from mnq_fractal_bot.models.setup import Setup

from mnq_fractal_bot.strategy.trade_plan import (
    build_trade_plan,
)


NOW = datetime(
    2026,
    10,
    9,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_audit(
    signal_id="signal-1",
):
    setup = Setup(
        is_bullish=False,

        is_confirmed=True,
        cisd_triggered=True,

        sweep_price=112,
        cisd_level=109,

        c2_extreme=120,

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

    plan = build_trade_plan(
        setup=setup,
        tick_size=0.25,
        sl_buffer_ticks=2,
    )

    return build_signal_audit(
        setup=setup,
        plan=plan,
        signal_id=signal_id,
        created_at=NOW,
    )


def test_target_outcome():
    audit = make_audit()

    events = [
        RecordedBrokerEvent(
            timestamp=NOW,
            event_type="ORDER_SUBMITTED",
            signal_id="signal-1",
            price=106,
        ),

        RecordedBrokerEvent(
            timestamp=(
                NOW + timedelta(minutes=5)
            ),
            event_type="ENTRY_FILLED",
            signal_id="signal-1",
            price=106,
        ),

        RecordedBrokerEvent(
            timestamp=(
                NOW + timedelta(minutes=10)
            ),
            event_type="POSITION_TARGET",
            signal_id="signal-1",
            price=100,
            gross_pnl=12,
        ),
    ]

    outcomes = build_signal_outcomes(
        audits=[audit],
        broker_events=events,
    )

    outcome = outcomes[0]

    assert outcome.order_submitted is True
    assert outcome.entry_filled is True

    assert outcome.final_status == "TARGET"

    assert outcome.exit_price == 100
    assert outcome.gross_pnl == 12


def test_expired_order_outcome():
    audit = make_audit()

    events = [
        RecordedBrokerEvent(
            timestamp=NOW,
            event_type="ORDER_SUBMITTED",
            signal_id="signal-1",
            price=106,
        ),

        RecordedBrokerEvent(
            timestamp=(
                NOW + timedelta(hours=1)
            ),
            event_type="ORDER_EXPIRED",
            signal_id="signal-1",
        ),
    ]

    outcome = build_signal_outcomes(
        audits=[audit],
        broker_events=events,
    )[0]

    assert outcome.order_submitted is True
    assert outcome.entry_filled is False

    assert outcome.final_status == "EXPIRED"

    assert outcome.gross_pnl is None


def test_signal_not_submitted():
    audit = make_audit()

    outcome = build_signal_outcomes(
        audits=[audit],
        broker_events=[],
    )[0]

    assert outcome.order_submitted is False
    assert outcome.entry_filled is False

    assert (
        outcome.final_status
        == "NOT_SUBMITTED"
    )


def test_open_position_at_end_of_dataset():
    audit = make_audit()

    events = [
        RecordedBrokerEvent(
            timestamp=NOW,
            event_type="ORDER_SUBMITTED",
            signal_id="signal-1",
            price=106,
        ),

        RecordedBrokerEvent(
            timestamp=(
                NOW + timedelta(minutes=5)
            ),
            event_type="ENTRY_FILLED",
            signal_id="signal-1",
            price=106,
        ),
    ]

    outcome = build_signal_outcomes(
        audits=[audit],
        broker_events=events,
    )[0]

    assert outcome.entry_filled is True

    assert (
        outcome.final_status
        == "OPEN_POSITION"
    )

    assert outcome.exit_time is None
    assert outcome.gross_pnl is None