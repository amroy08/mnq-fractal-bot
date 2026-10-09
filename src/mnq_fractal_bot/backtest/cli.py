import argparse
from pathlib import Path

from mnq_fractal_bot.backtest.audit_export import (
    export_signal_audits,
)

from mnq_fractal_bot.backtest.outcomes import (
    build_signal_outcomes,
)

from mnq_fractal_bot.backtest.outcomes_export import (
    export_signal_outcomes,
)

from mnq_fractal_bot.backtest.runner import (
    BacktestRunner,
)

from mnq_fractal_bot.data.csv_loader import (
    load_candles_from_csv,
)

from mnq_fractal_bot.execution.costs import (
    ExecutionCostConfig,
)

from mnq_fractal_bot.risk.trade_filter import (
    TradeFilterConfig,
)


def format_money(
    value: float,
) -> str:
    return f"${value:,.2f}"


def format_percentage(
    value: float,
) -> str:
    return f"{value:.2f}%"


def print_report(
    result,
    outcomes,
    trade_filter_config,
    execution_cost_config,
) -> None:
    stats = result.stats

    costs = (
        result.execution_cost_summary
    )

    submitted_count = sum(
        1
        for outcome in outcomes
        if outcome.order_submitted
    )

    filled_count = sum(
        1
        for outcome in outcomes
        if outcome.entry_filled
    )

    target_count = sum(
        1
        for outcome in outcomes
        if (
            outcome.final_status
            == "TARGET"
        )
    )

    stopped_count = sum(
        1
        for outcome in outcomes
        if (
            outcome.final_status
            == "STOPPED"
        )
    )

    expired_count = sum(
        1
        for outcome in outcomes
        if (
            outcome.final_status
            == "EXPIRED"
        )
    )

    cancelled_count = sum(
        1
        for outcome in outcomes
        if (
            outcome.final_status
            == "CANCELLED"
        )
    )

    not_submitted_count = sum(
        1
        for outcome in outcomes
        if (
            outcome.final_status
            == "NOT_SUBMITTED"
        )
    )

    print()
    print("=" * 60)
    print(
        "MNQ FRACTAL MODEL - PAPER BACKTEST"
    )
    print("=" * 60)

    # ==================================================
    # FILTERS
    # ==================================================

    print()
    print("TRADE FILTER")
    print("-" * 60)

    print(
        f"C3 allowed        : "
        f"{trade_filter_config.allow_c3}"
    )

    print(
        f"C4 allowed        : "
        f"{trade_filter_config.allow_c4}"
    )

    print(
        f"Max stop points   : "
        f"{trade_filter_config.max_stop_points}"
    )

    # ==================================================
    # EXECUTION ASSUMPTIONS
    # ==================================================

    print()
    print("EXECUTION COST ASSUMPTIONS")
    print("-" * 60)

    print(
        f"Round-trip fees   : "
        f"{format_money(execution_cost_config.commission_round_trip)}"
    )

    print(
        f"Entry slippage    : "
        f"{execution_cost_config.slippage_ticks_entry} ticks"
    )

    print(
        f"Exit slippage     : "
        f"{execution_cost_config.slippage_ticks_exit} ticks"
    )

    print(
        f"MNQ tick size     : "
        f"{execution_cost_config.tick_size}"
    )

    print(
        f"MNQ point value   : "
        f"{format_money(execution_cost_config.point_value)}"
    )

    # ==================================================
    # DATA
    # ==================================================

    print()
    print("DATA")
    print("-" * 60)

    print(
        f"Candles processed : "
        f"{result.candle_count:,}"
    )

    print(
        f"Signals audited   : "
        f"{len(result.signal_audits):,}"
    )

    # ==================================================
    # SIGNALS
    # ==================================================

    print()
    print("SIGNAL OUTCOMES")
    print("-" * 60)

    print(
        f"Orders submitted  : "
        f"{submitted_count}"
    )

    print(
        f"Entries filled    : "
        f"{filled_count}"
    )

    print(
        f"Targets hit       : "
        f"{target_count}"
    )

    print(
        f"Stops hit         : "
        f"{stopped_count}"
    )

    print(
        f"Expired           : "
        f"{expired_count}"
    )

    print(
        f"Cancelled         : "
        f"{cancelled_count}"
    )

    print(
        f"Not submitted     : "
        f"{not_submitted_count}"
    )

    # ==================================================
    # TRADES
    # ==================================================

    print()
    print("TRADES")
    print("-" * 60)

    print(
        f"Total trades      : "
        f"{stats.total_trades}"
    )

    print(
        f"Wins              : "
        f"{stats.wins}"
    )

    print(
        f"Losses            : "
        f"{stats.losses}"
    )

    print(
        f"Breakeven         : "
        f"{stats.breakeven}"
    )

    print(
        f"Win rate          : "
        f"{format_percentage(stats.win_rate_pct)}"
    )

    # ==================================================
    # GROSS RESULTS
    # ==================================================

    print()
    print("GROSS RESULTS")
    print("-" * 60)

    print(
        f"Gross profit      : "
        f"{format_money(stats.gross_profit)}"
    )

    print(
        f"Gross loss        : "
        f"{format_money(stats.gross_loss)}"
    )

    print(
        f"Gross P&L         : "
        f"{format_money(stats.gross_pnl)}"
    )

    print(
        f"Average trade     : "
        f"{format_money(stats.average_trade)}"
    )

    # ==================================================
    # EXECUTION COSTS
    # ==================================================

    print()
    print("EXECUTION COSTS")
    print("-" * 60)

    print(
        f"Fees              : "
        f"-{format_money(costs.commission_cost)}"
    )

    print(
        f"Entry slippage    : "
        f"-{format_money(costs.entry_slippage_cost)}"
    )

    print(
        f"Exit slippage     : "
        f"-{format_money(costs.exit_slippage_cost)}"
    )

    print(
        f"Total slippage    : "
        f"-{format_money(costs.total_slippage_cost)}"
    )

    print(
        f"Total costs       : "
        f"-{format_money(costs.total_execution_cost)}"
    )

    print(
        f"Avg cost / trade  : "
        f"{format_money(costs.average_cost_per_trade)}"
    )

    # ==================================================
    # NET RESULTS
    # ==================================================

    print()
    print("NET RESULTS")
    print("-" * 60)

    print(
        f"Gross P&L         : "
        f"{format_money(costs.gross_pnl)}"
    )

    print(
        f"Execution costs   : "
        f"-{format_money(costs.total_execution_cost)}"
    )

    print(
        f"NET P&L           : "
        f"{format_money(costs.net_pnl)}"
    )

    print(
        f"Avg net / trade   : "
        f"{format_money(costs.average_net_pnl_per_trade)}"
    )

    # ==================================================
    # RISK
    # ==================================================

    print()
    print("RISK")
    print("-" * 60)

    if stats.profit_factor is None:
        profit_factor_text = "N/A"
    else:
        profit_factor_text = (
            f"{stats.profit_factor:.2f}"
        )

    print(
        f"Gross PF          : "
        f"{profit_factor_text}"
    )

    print(
        f"Gross max DD      : "
        f"{format_money(stats.max_drawdown)}"
    )

    print(
        f"Gross max DD %    : "
        f"{format_percentage(stats.max_drawdown_pct)}"
    )

    # ==================================================
    # ACCOUNT
    # ==================================================

    print()
    print("ACCOUNT")
    print("-" * 60)

    print(
        f"Starting balance  : "
        f"{format_money(costs.starting_balance)}"
    )

    print(
        f"Gross ending      : "
        f"{format_money(stats.ending_balance)}"
    )

    print(
        f"Net ending        : "
        f"{format_money(costs.net_ending_balance)}"
    )

    print()
    print("=" * 60)

    print(
        "PAPER BACKTEST ONLY - "
        "NO LIVE BROKER ORDERS"
    )

    print("=" * 60)


def run_csv_backtest(
    csv_path: str | Path,
    lower_timeframe: str = "5m",
    starting_balance: float = 25_000.0,
    trade_filter_config: (
        TradeFilterConfig | None
    ) = None,
    execution_cost_config: (
        ExecutionCostConfig | None
    ) = None,
):
    candles = load_candles_from_csv(
        csv_path
    )

    runner = BacktestRunner(
        lower_timeframe=(
            lower_timeframe
        ),

        tick_size=0.25,

        sl_buffer_ticks=2,

        point_value=2.0,

        starting_balance=(
            starting_balance
        ),

        trade_filter_config=(
            trade_filter_config
        ),

        execution_cost_config=(
            execution_cost_config
        ),
    )

    return runner.run(
        candles
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run the MNQ Fractal Model "
            "paper backtest."
        )
    )

    parser.add_argument(
        "csv_path",
    )

    parser.add_argument(
        "--timeframe",
        default="5m",
        choices=[
            "5m",
            "15m",
        ],
    )

    parser.add_argument(
        "--starting-balance",
        type=float,
        default=25_000.0,
    )

    # ==================================================
    # TRADE FILTERS
    # ==================================================

    parser.add_argument(
        "--c3-only",
        action="store_true",
    )

    parser.add_argument(
        "--max-stop-points",
        type=float,
        default=None,
    )

    # ==================================================
    # EXECUTION COSTS
    # ==================================================

    parser.add_argument(
        "--commission-round-trip",
        type=float,
        default=0.0,
    )

    parser.add_argument(
        "--entry-slippage-ticks",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--exit-slippage-ticks",
        type=int,
        default=0,
    )

    # ==================================================
    # OUTPUT FILES
    # ==================================================

    parser.add_argument(
        "--audit-output",
        default=(
            "data/fractal_signal_audit.csv"
        ),
    )

    parser.add_argument(
        "--outcomes-output",
        default=(
            "data/fractal_signal_outcomes.csv"
        ),
    )

    args = parser.parse_args()

    # ==================================================
    # FILTER CONFIG
    # ==================================================

    trade_filter_config = (
        TradeFilterConfig(
            allow_c3=True,

            allow_c4=(
                not args.c3_only
            ),

            max_stop_points=(
                args.max_stop_points
            ),
        )
    )

    # ==================================================
    # COST CONFIG
    # ==================================================

    execution_cost_config = (
        ExecutionCostConfig(
            commission_round_trip=(
                args.commission_round_trip
            ),

            slippage_ticks_entry=(
                args.entry_slippage_ticks
            ),

            slippage_ticks_exit=(
                args.exit_slippage_ticks
            ),

            tick_size=0.25,

            point_value=2.0,
        )
    )

    # ==================================================
    # RUN BACKTEST
    # ==================================================

    result = run_csv_backtest(
        csv_path=args.csv_path,

        lower_timeframe=(
            args.timeframe
        ),

        starting_balance=(
            args.starting_balance
        ),

        trade_filter_config=(
            trade_filter_config
        ),

        execution_cost_config=(
            execution_cost_config
        ),
    )

    # ==================================================
    # EXPORT SIGNAL AUDIT
    # ==================================================

    audit_path = export_signal_audits(
        audits=result.signal_audits,

        output_path=(
            args.audit_output
        ),
    )

    # ==================================================
    # BUILD + EXPORT OUTCOMES
    # ==================================================

    outcomes = build_signal_outcomes(
        audits=result.signal_audits,

        broker_events=(
            result.broker_events
        ),
    )

    outcomes_path = (
        export_signal_outcomes(
            outcomes=outcomes,

            output_path=(
                args.outcomes_output
            ),
        )
    )

    # ==================================================
    # PRINT
    # ==================================================

    print_report(
        result=result,

        outcomes=outcomes,

        trade_filter_config=(
            trade_filter_config
        ),

        execution_cost_config=(
            execution_cost_config
        ),
    )

    print()
    print(
        "Signal audit saved to:"
    )

    print(
        audit_path
    )

    print()

    print(
        "Signal outcomes saved to:"
    )

    print(
        outcomes_path
    )


if __name__ == "__main__":
    main()