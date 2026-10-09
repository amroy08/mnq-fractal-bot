import pytest

from mnq_fractal_bot.execution.costs import (
    ExecutionCostConfig,
    calculate_trade_costs,
)


def test_zero_cost_keeps_gross_pnl():
    config = ExecutionCostConfig()

    result = calculate_trade_costs(
        gross_pnl=100,
        config=config,
    )

    assert result.total_cost == 0
    assert result.net_pnl == 100


def test_mnq_two_dollar_fee_and_two_ticks_each_side():
    config = ExecutionCostConfig(
        commission_round_trip=2.00,
        slippage_ticks_entry=2,
        slippage_ticks_exit=2,
        tick_size=0.25,
        point_value=2.0,
    )

    result = calculate_trade_costs(
        gross_pnl=100,
        config=config,
    )

    # MNQ:
    #
    # tick value =
    # 0.25 × $2
    # = $0.50
    #
    # entry:
    # 2 ticks = $1
    #
    # exit:
    # 2 ticks = $1
    #
    # commission:
    # $2
    #
    # total:
    # $4

    assert (
        result.commission_cost
        == 2.00
    )

    assert (
        result.entry_slippage_cost
        == 1.00
    )

    assert (
        result.exit_slippage_cost
        == 1.00
    )

    assert (
        result.total_cost
        == 4.00
    )

    assert (
        result.net_pnl
        == 96.00
    )


def test_costs_apply_to_losing_trade_too():
    config = ExecutionCostConfig(
        commission_round_trip=2.00,
        slippage_ticks_entry=2,
        slippage_ticks_exit=2,
    )

    result = calculate_trade_costs(
        gross_pnl=-50,
        config=config,
    )

    assert result.total_cost == 4

    assert result.net_pnl == -54


def test_quantity_two_doubles_costs():
    config = ExecutionCostConfig(
        commission_round_trip=2.00,
        slippage_ticks_entry=2,
        slippage_ticks_exit=2,
    )

    result = calculate_trade_costs(
        gross_pnl=200,
        config=config,
        quantity=2,
    )

    assert result.total_cost == 8

    assert result.net_pnl == 192


def test_negative_commission_rejected():
    with pytest.raises(ValueError):
        ExecutionCostConfig(
            commission_round_trip=-1,
        )


def test_negative_entry_slippage_rejected():
    with pytest.raises(ValueError):
        ExecutionCostConfig(
            slippage_ticks_entry=-1,
        )


def test_negative_exit_slippage_rejected():
    with pytest.raises(ValueError):
        ExecutionCostConfig(
            slippage_ticks_exit=-1,
        )


def test_zero_quantity_rejected():
    config = ExecutionCostConfig()

    with pytest.raises(ValueError):
        calculate_trade_costs(
            gross_pnl=100,
            config=config,
            quantity=0,
        )