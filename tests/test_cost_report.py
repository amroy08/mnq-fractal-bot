from dataclasses import dataclass

import pytest

from mnq_fractal_bot.backtest.cost_report import (
    build_execution_cost_summary,
)

from mnq_fractal_bot.execution.costs import (
    ExecutionCostConfig,
)


@dataclass
class FakeTrade:
    gross_pnl: float


def test_cost_summary_with_two_trades():
    trades = [
        FakeTrade(
            gross_pnl=100,
        ),
        FakeTrade(
            gross_pnl=-50,
        ),
    ]

    config = ExecutionCostConfig(
        commission_round_trip=2,
        slippage_ticks_entry=2,
        slippage_ticks_exit=2,
    )

    result = (
        build_execution_cost_summary(
            trades=trades,
            config=config,
            starting_balance=25_000,
        )
    )

    # Gross:
    # +100 - 50 = +50

    assert result.gross_pnl == 50

    # $4 cost per trade
    # × 2 trades
    # = $8

    assert (
        result.total_execution_cost
        == 8
    )

    assert result.net_pnl == 42

    assert (
        result.net_ending_balance
        == 25_042
    )


def test_cost_breakdown():
    trades = [
        FakeTrade(
            gross_pnl=100,
        )
    ]

    config = ExecutionCostConfig(
        commission_round_trip=2,
        slippage_ticks_entry=2,
        slippage_ticks_exit=2,
    )

    result = (
        build_execution_cost_summary(
            trades=trades,
            config=config,
        )
    )

    assert (
        result.commission_cost
        == 2
    )

    assert (
        result.entry_slippage_cost
        == 1
    )

    assert (
        result.exit_slippage_cost
        == 1
    )

    assert (
        result.total_slippage_cost
        == 2
    )

    assert (
        result.total_execution_cost
        == 4
    )


def test_no_trades():
    config = ExecutionCostConfig(
        commission_round_trip=2,
        slippage_ticks_entry=2,
        slippage_ticks_exit=2,
    )

    result = (
        build_execution_cost_summary(
            trades=[],
            config=config,
        )
    )

    assert result.trade_count == 0
    assert result.gross_pnl == 0
    assert result.net_pnl == 0

    assert (
        result.total_execution_cost
        == 0
    )

    assert (
        result.net_ending_balance
        == 25_000
    )


def test_invalid_starting_balance():
    config = ExecutionCostConfig()

    with pytest.raises(ValueError):
        build_execution_cost_summary(
            trades=[],
            config=config,
            starting_balance=0,
        )