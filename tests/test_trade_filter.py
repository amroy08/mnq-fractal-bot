import pytest

from mnq_fractal_bot.risk.trade_filter import (
    TradeFilterConfig,
    evaluate_trade_plan,
)

from mnq_fractal_bot.strategy.trade_plan import (
    TradePlan,
)


def make_plan(
    entry_name="C3 ENTRY ZONE",
    entry_price=100,
    stop_price=140,
    bot_trade_ready=True,
):
    return TradePlan(
        direction="LONG",

        entry_name=entry_name,

        entry_bottom=95,
        entry_top=105,
        entry_price=entry_price,

        stop_price=stop_price,

        tp_c1=160,
        tp_c0=180,
        preferred_target=160,

        model_ready=True,
        has_valid_target=True,

        bot_trade_ready=bot_trade_ready,
    )


def test_default_filter_allows_c3():
    config = TradeFilterConfig()

    plan = make_plan(
        entry_name="C3 ENTRY ZONE",
    )

    decision = evaluate_trade_plan(
        plan=plan,
        config=config,
    )

    assert decision.allowed is True

    assert decision.reason == "ALLOWED"

    assert (
        decision.stop_distance_points
        == 40
    )


def test_c4_can_be_disabled():
    config = TradeFilterConfig(
        allow_c3=True,
        allow_c4=False,
    )

    plan = make_plan(
        entry_name="C4 ENTRY ZONE",
    )

    decision = evaluate_trade_plan(
        plan=plan,
        config=config,
    )

    assert decision.allowed is False

    assert (
        decision.reason
        == "C4_DISABLED"
    )


def test_stop_above_50_points_is_rejected():
    config = TradeFilterConfig(
        max_stop_points=50,
    )

    plan = make_plan(
        entry_price=100,
        stop_price=151,
    )

    decision = evaluate_trade_plan(
        plan=plan,
        config=config,
    )

    assert decision.allowed is False

    assert (
        decision.reason
        == "MAX_STOP_EXCEEDED"
    )

    assert (
        decision.stop_distance_points
        == 51
    )


def test_stop_exactly_50_points_is_allowed():
    config = TradeFilterConfig(
        max_stop_points=50,
    )

    plan = make_plan(
        entry_price=100,
        stop_price=150,
    )

    decision = evaluate_trade_plan(
        plan=plan,
        config=config,
    )

    assert decision.allowed is True

    assert decision.reason == "ALLOWED"

    assert (
        decision.stop_distance_points
        == 50
    )


def test_not_ready_trade_is_rejected():
    config = TradeFilterConfig(
        max_stop_points=50,
    )

    plan = make_plan(
        bot_trade_ready=False,
    )

    decision = evaluate_trade_plan(
        plan=plan,
        config=config,
    )

    assert decision.allowed is False

    assert (
        decision.reason
        == "BOT_NOT_READY"
    )


def test_negative_max_stop_is_rejected():
    with pytest.raises(ValueError):
        TradeFilterConfig(
            max_stop_points=-1,
        )