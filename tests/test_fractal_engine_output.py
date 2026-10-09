from datetime import (
    datetime,
    timedelta,
    timezone,
)

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.models.setup import Setup
from mnq_fractal_bot.strategy.fractal_engine import (
    FractalEngine,
)


NOW = datetime(
    2026,
    10,
    9,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_candle():
    return Candle(
        timestamp=NOW,
        open=106,
        high=110,
        low=102,
        close=108,
        volume=100,
    )


def test_snapshot_has_no_plan_without_setup():
    engine = FractalEngine(
        "5m"
    )

    snapshot = engine.on_candle(
        make_candle()
    )

    assert snapshot.selected_setup is None
    assert snapshot.both_sides is False
    assert snapshot.trade_plan is None


def test_active_c4_produces_trade_plan():
    engine = FractalEngine(
        "5m"
    )

    setup = Setup(
        is_bullish=False,
        is_confirmed=True,
        cisd_triggered=True,
        is_post_c2=True,

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

    engine.completed_setups.append(
        setup
    )

    snapshot = engine.on_candle(
        make_candle()
    )

    assert snapshot.selected_setup is setup

    assert snapshot.trade_plan is not None

    plan = snapshot.trade_plan

    assert plan.direction == "SHORT"
    assert plan.entry_name == "C4 ENTRY ZONE"

    assert plan.entry_price == 106
    assert plan.stop_price == 120.5

    assert plan.tp_c1 == 100
    assert plan.tp_c0 == 90

    assert plan.model_ready is True
    assert plan.bot_trade_ready is True