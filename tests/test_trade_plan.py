import pytest

from mnq_fractal_bot.models.setup import Setup
from mnq_fractal_bot.strategy.trade_plan import (
    build_trade_plan,
    round_to_tick,
)


def make_ready_bearish_setup():
    return Setup(
        is_bullish=False,
        is_confirmed=True,
        cisd_triggered=True,
        c2_extreme=120,
    )


def make_ready_bullish_setup():
    return Setup(
        is_bullish=True,
        is_confirmed=True,
        cisd_triggered=True,
        c2_extreme=100,
    )


def test_round_to_mnq_tick():
    result = round_to_tick(
        100.13,
        0.25,
    )

    assert result == 100.25


def test_c3_zone_creates_entry_midpoint():
    setup = make_ready_bearish_setup()

    setup.c3_zone_set = True
    setup.c3_zone_bottom = 108
    setup.c3_zone_top = 112

    plan = build_trade_plan(
        setup
    )

    assert plan.entry_name == "C3 ENTRY ZONE"
    assert plan.entry_bottom == 108
    assert plan.entry_top == 112
    assert plan.entry_price == 110


def test_valid_c4_is_preferred_over_c3():
    setup = make_ready_bearish_setup()

    setup.c3_zone_set = True
    setup.c3_zone_bottom = 108
    setup.c3_zone_top = 112

    setup.c4_zone_set = True
    setup.c4_invalid = False
    setup.c4_zone_bottom = 104
    setup.c4_zone_top = 108

    plan = build_trade_plan(
        setup
    )

    assert plan.entry_name == "C4 ENTRY ZONE"
    assert plan.entry_price == 106


def test_invalid_c4_falls_back_to_c3():
    setup = make_ready_bearish_setup()

    setup.c3_zone_set = True
    setup.c3_zone_bottom = 108
    setup.c3_zone_top = 112

    setup.c4_zone_set = True
    setup.c4_invalid = True
    setup.c4_zone_bottom = 104
    setup.c4_zone_top = 108

    plan = build_trade_plan(
        setup
    )

    assert plan.entry_name == "C3 ENTRY ZONE"
    assert plan.entry_price == 110


def test_bearish_stop_is_above_c2_extreme():
    setup = make_ready_bearish_setup()

    setup.c3_zone_set = True
    setup.c3_zone_bottom = 108
    setup.c3_zone_top = 112

    plan = build_trade_plan(
        setup=setup,
        tick_size=0.25,
        sl_buffer_ticks=2,
    )

    assert plan.stop_price == 120.5


def test_bullish_stop_is_below_c2_extreme():
    setup = make_ready_bullish_setup()

    setup.c3_zone_set = True
    setup.c3_zone_bottom = 108
    setup.c3_zone_top = 112

    plan = build_trade_plan(
        setup=setup,
        tick_size=0.25,
        sl_buffer_ticks=2,
    )

    assert plan.stop_price == 99.5


def test_model_can_be_ready_without_valid_tp():
    setup = make_ready_bearish_setup()

    setup.c3_zone_set = True
    setup.c3_zone_bottom = 108
    setup.c3_zone_top = 112

    # Wrong side for a SHORT.
    setup.liq_c1_price = 130
    setup.liq_c0_price = 140

    plan = build_trade_plan(
        setup
    )

    assert plan.entry_price == 110

    assert plan.model_ready is True

    assert plan.has_valid_target is False

    assert plan.bot_trade_ready is False

    assert plan.preferred_target is None


def test_bot_ready_with_entry_stop_and_valid_target():
    setup = make_ready_bearish_setup()

    setup.c3_zone_set = True
    setup.c3_zone_bottom = 108
    setup.c3_zone_top = 112

    setup.liq_c1_price = 100
    setup.liq_c0_price = 90

    plan = build_trade_plan(
        setup
    )

    assert plan.direction == "SHORT"

    assert plan.entry_price == 110
    assert plan.stop_price == 120.5

    assert plan.tp_c1 == 100
    assert plan.tp_c0 == 90

    assert plan.preferred_target == 100

    assert plan.model_ready is True
    assert plan.has_valid_target is True
    assert plan.bot_trade_ready is True


def test_invalid_tick_size_is_rejected():
    setup = make_ready_bearish_setup()

    with pytest.raises(ValueError):
        build_trade_plan(
            setup=setup,
            tick_size=0,
        )