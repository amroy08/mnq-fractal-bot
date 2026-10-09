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

from mnq_fractal_bot.backtest.validation_runner import (
    ChronologicalValidationRunner,
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


def print_validation_report(
    result,
    outcomes,
    trade_filter_config,
    execution_cost_config,
):
    split = result.split
    backtest = result.backtest

    stats = backtest.stats

    costs = (
        backtest.execution_cost_summary
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
    print("=" * 68)

    print(
        "MNQ FRACTAL MODEL - "
        "CHRONOLOGICAL VALIDATION"
    )

    print("=" * 68)

    # ==================================================
    # SPLIT
    # ==================================================

    print()
    print("CHRONOLOGICAL SPLIT")
    print("-" * 68)

    print(
        f"Total candles      : "
        f"{split.total_candles:,}"
    )

    print(
        f"Warm-up candles    : "
        f"{len(split.warmup_candles):,}"
    )

    print(
        f"Validation candles : "
        f"{len(split.validation_candles):,}"
    )

    print(
        f"Validation %       : "
        f"{split.validation_fraction * 100:.2f}%"
    )

    print(
        f"Validation start   : "
        f"{split.validation_start}"
    )

    print(
        f"Validation end     : "
        f"{split.validation_end}"
    )

    # ==================================================
    # IMPORTANT BEHAVIOR
    # ==================================================

    print()
    print("VALIDATION MODE")
    print("-" * 68)

    print(
        "Warm-up engine     : ON"
    )

    print(
        "Warm-up trading    : OFF"
    )

    print(
        "Validation engine  : CONTINUED"
    )

    print(
        "Validation trading : ON"
    )

    print(
        "Engine reset       : NO"
    )

    # ==================================================
    # FILTERS
    # ==================================================

    print()
    print("TRADE FILTER")
    print("-" * 68)

    print(
        f"C3 allowed         : "
        f"{trade_filter_config.allow_c3}"
    )

    print(
        f"C4 allowed         : "
        f"{trade_filter_config.allow_c4}"
    )

    print(
        f"Max stop points    : "
        f"{trade_filter_config.max_stop_points}"
    )

    # ==================================================
    # COSTS
    # ==================================================

    print()
    print("EXECUTION ASSUMPTIONS")
    print("-" * 68)

    print(
        f"Round-trip fees    : "
        f"{format_money(execution_cost_config.commission_round_trip)}"
    )

    print(
        f"Entry slippage     : "
        f"{execution_cost_config.slippage_ticks_entry} ticks"
    )

    print(
        f"Exit slippage      : "
        f"{execution_cost_config.slippage_ticks_exit} ticks"
    )

    print(
        f"Tick size          : "
        f"{execution_cost_config.tick_size}"
    )

    print(
        f"Point value        : "
        f"{format_money(execution_cost_config.point_value)}"
    )

    # ==================================================
    # SIGNALS
    # ==================================================

    print()
    print("VALIDATION SIGNALS")
    print("-" * 68)

    print(
        f"Signals audited    : "
        f"{len(backtest.signal_audits)}"
    )

    print(
        f"Orders submitted   : "
        f"{submitted_count}"
    )

    print(
        f"Entries filled     : "
        f"{filled_count}"
    )

    print(
        f"Targets hit        : "
        f"{target_count}"
    )

    print(
        f"Stops hit          : "
        f"{stopped_count}"
    )

    print(
        f"Expired            : "
        f"{expired_count}"
    )

    print(
        f"Cancelled          : "
        f"{cancelled_count}"
    )

    print(
        f"Not submitted      : "
        f"{not_submitted_count}"
    )

    # ==================================================
    # TRADES
    # ==================================================

    print()
    print("VALIDATION TRADES")
    print("-" * 68)

    print(
        f"Total trades       : "
        f"{stats.total_trades}"
    )

    print(
        f"Wins               : "
        f"{stats.wins}"
    )

    print(
        f"Losses             : "
        f"{stats.losses}"
    )

    print(
        f"Breakeven          : "
        f"{stats.breakeven}"
    )

    print(
        f"Win rate           : "
        f"{format_percentage(stats.win_rate_pct)}"
    )

    # ==================================================
    # GROSS
    # ==================================================

    print()
    print("VALIDATION GROSS RESULTS")
    print("-" * 68)

    print(
        f"Gross profit       : "
        f"{format_money(stats.gross_profit)}"
    )

    print(
        f"Gross loss         : "
        f"{format_money(stats.gross_loss)}"
    )

    print(
        f"Gross P&L          : "
        f"{format_money(stats.gross_pnl)}"
    )

    print(
        f"Average trade      : "
        f"{format_money(stats.average_trade)}"
    )

    if stats.profit_factor is None:
        profit_factor = "N/A"

    else:
        profit_factor = (
            f"{stats.profit_factor:.2f}"
        )

    print(
        f"Gross PF           : "
        f"{profit_factor}"
    )

    # ==================================================
    # COSTS
    # ==================================================

    print()
    print("VALIDATION EXECUTION COSTS")
    print("-" * 68)

    print(
        f"Fees               : "
        f"-{format_money(costs.commission_cost)}"
    )

    print(
        f"Entry slippage     : "
        f"-{format_money(costs.entry_slippage_cost)}"
    )

    print(
        f"Exit slippage      : "
        f"-{format_money(costs.exit_slippage_cost)}"
    )

    print(
        f"Total slippage     : "
        f"-{format_money(costs.total_slippage_cost)}"
    )

    print(
        f"Total costs        : "
        f"-{format_money(costs.total_execution_cost)}"
    )

    print(
        f"Avg cost / trade   : "
        f"{format_money(costs.average_cost_per_trade)}"
    )

    # ==================================================
    # NET
    # ==================================================

    print()
    print("VALIDATION NET RESULTS")
    print("-" * 68)

    print(
        f"Gross P&L          : "
        f"{format_money(costs.gross_pnl)}"
    )

    print(
        f"Execution costs    : "
        f"-{format_money(costs.total_execution_cost)}"
    )

    print(
        f"NET P&L            : "
        f"{format_money(costs.net_pnl)}"
    )

    print(
        f"Avg net / trade    : "
        f"{format_money(costs.average_net_pnl_per_trade)}"
    )

    # ==================================================
    # RISK
    # ==================================================

    print()
    print("VALIDATION RISK")
    print("-" * 68)

    print(
        f"Gross max DD       : "
        f"{format_money(stats.max_drawdown)}"
    )

    print(
        f"Gross max DD %     : "
        f"{format_percentage(stats.max_drawdown_pct)}"
    )

    # ==================================================
    # ACCOUNT
    # ==================================================

    print()
    print("VALIDATION ACCOUNT")
    print("-" * 68)

    print(
        f"Starting balance   : "
        f"{format_money(costs.starting_balance)}"
    )

    print(
        f"Gross ending       : "
        f"{format_money(stats.ending_balance)}"
    )

    print(
        f"Net ending         : "
        f"{format_money(costs.net_ending_balance)}"
    )

    print()
    print("=" * 68)

    print(
        "CHRONOLOGICAL STABILITY TEST ONLY"
    )

    print(
        "NOT YET A TRUE UNSEEN OUT-OF-SAMPLE TEST"
    )

    print(
        "PAPER SIMULATION ONLY - "
        "NO BROKER ORDERS"
    )

    print("=" * 68)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run chronological validation "
            "for the MNQ Fractal Model."
        )
    )

    parser.add_argument(
        "csv_path",
    )

    parser.add_argument(
        "--validation-fraction",
        type=float,
        default=0.30,
    )

    parser.add_argument(
        "--starting-balance",
        type=float,
        default=25_000.0,
    )

    parser.add_argument(
        "--c3-only",
        action="store_true",
    )

    parser.add_argument(
        "--max-stop-points",
        type=float,
        default=None,
    )

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

    parser.add_argument(
        "--audit-output",
        default=(
            "data/validation_audit.csv"
        ),
    )

    parser.add_argument(
        "--outcomes-output",
        default=(
            "data/validation_outcomes.csv"
        ),
    )

    args = parser.parse_args()

    # ==================================================
    # LOAD DATA
    # ==================================================

    candles = (
        load_candles_from_csv(
            Path(
                args.csv_path
            )
        )
    )

    # ==================================================
    # FILTER
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
    # COSTS
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
    # RUN
    # ==================================================

    runner = (
        ChronologicalValidationRunner(
            validation_fraction=(
                args.validation_fraction
            ),

            lower_timeframe="5m",

            tick_size=0.25,

            sl_buffer_ticks=2,

            point_value=2.0,

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
    )

    result = runner.run(
        candles
    )

    # ==================================================
    # SIGNAL OUTCOMES
    # ==================================================

    outcomes = (
        build_signal_outcomes(
            audits=(
                result.backtest
                .signal_audits
            ),

            broker_events=(
                result.backtest
                .broker_events
            ),
        )
    )

    # ==================================================
    # EXPORT
    # ==================================================

    audit_path = (
        export_signal_audits(
            audits=(
                result.backtest
                .signal_audits
            ),

            output_path=(
                args.audit_output
            ),
        )
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
    # REPORT
    # ==================================================

    print_validation_report(
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
        "Validation audit saved to:"
    )

    print(
        audit_path
    )

    print()

    print(
        "Validation outcomes saved to:"
    )

    print(
        outcomes_path
    )


if __name__ == "__main__":
    main()