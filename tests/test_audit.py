from datetime import (
    datetime,
    timezone,
)

import pytest

from mnq_fractal_bot.backtest.audit import (
    build_signal_audit,
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


def make_setup():
    return Setup(
        is_bullish=False,

        is_confirmed=True,
        cisd_triggered=True,

        sweep_price=31233.50,
        cisd_level=31210.75,

        c2_extreme=31260.00,

        c3_zone_set=True,
        c3_zone_bottom=31220.00,
        c3_zone_top=31230.00,
        c3_start_time=NOW,

        c4_zone_set=True,
        c4_invalid=False,
        c4_zone_bottom=31215.00,
        c4_zone_top=31225.00,
        c4_start_time=NOW,

        liq_c1_price=31196.25,
        liq_c0_price=31150.00,
    )


def test_signal_audit_captures_fractal_state():
    setup = make_setup()

    plan = build_trade_plan(
        setup=setup,
        tick_size=0.25,
        sl_buffer_ticks=2,
    )

    audit = build_signal_audit(
        setup=setup,
        plan=plan,
        signal_id="short-test-1",
        created_at=NOW,
    )

    assert audit.direction == "SHORT"

    assert audit.sweep_price == 31233.50
    assert audit.cisd_level == 31210.75

    assert audit.c2_extreme == 31260.00

    assert audit.c4_zone_set is True

    assert audit.entry_name == "C4 ENTRY ZONE"

    assert audit.entry_price == 31220.00

    assert audit.stop_price == 31260.50

    assert audit.tp_c1 == 31196.25
    assert audit.tp_c0 == 31150.00

    assert audit.bot_trade_ready is True


def test_signal_audit_requires_signal_id():
    setup = make_setup()

    plan = build_trade_plan(
        setup
    )

    with pytest.raises(ValueError):
        build_signal_audit(
            setup=setup,
            plan=plan,
            signal_id="",
            created_at=NOW,
        )


def test_signal_audit_requires_timezone():
    setup = make_setup()

    plan = build_trade_plan(
        setup
    )

    naive_time = datetime(
        2026,
        10,
        9,
        12,
        0,
    )

    with pytest.raises(ValueError):
        build_signal_audit(
            setup=setup,
            plan=plan,
            signal_id="short-test-1",
            created_at=naive_time,
        )