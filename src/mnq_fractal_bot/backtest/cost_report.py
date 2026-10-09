from collections.abc import Sequence
from dataclasses import dataclass

from mnq_fractal_bot.execution.costs import (
    ExecutionCostConfig,
    calculate_trade_costs,
)

from mnq_fractal_bot.execution.paper_broker import (
    ClosedTrade,
)


@dataclass(frozen=True)
class ExecutionCostSummary:
    trade_count: int

    gross_pnl: float

    commission_cost: float
    entry_slippage_cost: float
    exit_slippage_cost: float

    total_slippage_cost: float
    total_execution_cost: float

    net_pnl: float

    average_cost_per_trade: float
    average_net_pnl_per_trade: float

    starting_balance: float
    net_ending_balance: float


def build_execution_cost_summary(
    trades: Sequence[ClosedTrade],
    config: ExecutionCostConfig,
    starting_balance: float = 25_000.0,
    quantity: int = 1,
) -> ExecutionCostSummary:
    if starting_balance <= 0:
        raise ValueError(
            "starting_balance must be greater than zero."
        )

    gross_pnl = 0.0

    commission_cost = 0.0
    entry_slippage_cost = 0.0
    exit_slippage_cost = 0.0

    for trade in trades:
        cost = calculate_trade_costs(
            gross_pnl=trade.gross_pnl,
            config=config,
            quantity=quantity,
        )

        gross_pnl += cost.gross_pnl

        commission_cost += (
            cost.commission_cost
        )

        entry_slippage_cost += (
            cost.entry_slippage_cost
        )

        exit_slippage_cost += (
            cost.exit_slippage_cost
        )

    total_slippage_cost = (
        entry_slippage_cost
        + exit_slippage_cost
    )

    total_execution_cost = (
        commission_cost
        + total_slippage_cost
    )

    net_pnl = (
        gross_pnl
        - total_execution_cost
    )

    trade_count = len(
        trades
    )

    if trade_count == 0:
        average_cost_per_trade = 0.0
        average_net_pnl_per_trade = 0.0

    else:
        average_cost_per_trade = (
            total_execution_cost
            / trade_count
        )

        average_net_pnl_per_trade = (
            net_pnl
            / trade_count
        )

    net_ending_balance = (
        starting_balance
        + net_pnl
    )

    return ExecutionCostSummary(
        trade_count=trade_count,

        gross_pnl=gross_pnl,

        commission_cost=(
            commission_cost
        ),

        entry_slippage_cost=(
            entry_slippage_cost
        ),

        exit_slippage_cost=(
            exit_slippage_cost
        ),

        total_slippage_cost=(
            total_slippage_cost
        ),

        total_execution_cost=(
            total_execution_cost
        ),

        net_pnl=(
            net_pnl
        ),

        average_cost_per_trade=(
            average_cost_per_trade
        ),

        average_net_pnl_per_trade=(
            average_net_pnl_per_trade
        ),

        starting_balance=(
            starting_balance
        ),

        net_ending_balance=(
            net_ending_balance
        ),
    )