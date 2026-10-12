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
    preferred_target=160,
    bot_trade_ready=True,
):
    return TradePlan(
        direction="LONG",

        entry_name=entry_name,

        entry_bottom=95,
        entry_top=105,
        entry_price=entry_price,

        stop_price=stop_price,

        tp_c1=preferred_target,
        tp_c0=180,
        preferred_target=preferred_target,

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


def test_min_stop_points_filter():
    config = TradeFilterConfig(min_stop_points=20.0)
    tight_plan = make_plan(entry_price=100.0, stop_price=110.0)  # 10 pts stop
    valid_plan = make_plan(entry_price=100.0, stop_price=125.0)  # 25 pts stop

    decision_tight = evaluate_trade_plan(tight_plan, config)
    assert decision_tight.allowed is False
    assert decision_tight.reason == "MIN_STOP_NOT_REACHED"

    decision_valid = evaluate_trade_plan(valid_plan, config)
    assert decision_valid.allowed is True
    assert decision_valid.reason == "ALLOWED"


def test_max_target_points_filter():
    config = TradeFilterConfig(max_target_points=30.0)
    far_plan = make_plan(entry_price=100.0, stop_price=80.0, preferred_target=145.0)  # 45 pts target
    near_plan = make_plan(entry_price=100.0, stop_price=80.0, preferred_target=125.0)  # 25 pts target

    decision_far = evaluate_trade_plan(far_plan, config)
    assert decision_far.allowed is False
    assert decision_far.reason == "MAX_TARGET_EXCEEDED"

    decision_near = evaluate_trade_plan(near_plan, config)
    assert decision_near.allowed is True
    assert decision_near.reason == "ALLOWED"