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
) -> None:
    stats = result.stats

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
        if outcome.final_status == "TARGET"
    )

    stopped_count = sum(
        1
        for outcome in outcomes
        if outcome.final_status == "STOPPED"
    )

    expired_count = sum(
        1
        for outcome in outcomes
        if outcome.final_status == "EXPIRED"
    )

    cancelled_count = sum(
        1
        for outcome in outcomes
        if outcome.final_status == "CANCELLED"
    )

    print()
    print("=" * 60)
    print("MNQ FRACTAL MODEL - PAPER BACKTEST")
    print("=" * 60)

    print()
    print("FILTER")
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
        f"Win rate          : "
        f"{format_percentage(stats.win_rate_pct)}"
    )

    print()
    print("P&L")
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
        f"Profit factor     : "
        f"{profit_factor_text}"
    )

    print(
        f"Max drawdown      : "
        f"{format_money(stats.max_drawdown)}"
    )

    print(
        f"Max drawdown %    : "
        f"{format_percentage(stats.max_drawdown_pct)}"
    )

    print()
    print("ACCOUNT")
    print("-" * 60)

    print(
        f"Starting balance  : "
        f"{format_money(stats.starting_balance)}"
    )

    print(
        f"Ending balance    : "
        f"{format_money(stats.ending_balance)}"
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
    trade_filter_config: TradeFilterConfig | None = None,
):
    candles = load_candles_from_csv(
        csv_path
    )

    runner = BacktestRunner(
        lower_timeframe=lower_timeframe,
        tick_size=0.25,
        sl_buffer_ticks=2,
        point_value=2.0,
        starting_balance=starting_balance,
        trade_filter_config=(
            trade_filter_config
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

    parser.add_argument(
        "--c3-only",
        action="store_true",
        help=(
            "Allow C3 trades and "
            "disable C4 trades."
        ),
    )

    parser.add_argument(
        "--max-stop-points",
        type=float,
        default=None,
        help=(
            "Reject trades whose entry-to-stop "
            "distance exceeds this many points."
        ),
    )

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

    result = run_csv_backtest(
        csv_path=args.csv_path,
        lower_timeframe=args.timeframe,
        starting_balance=(
            args.starting_balance
        ),
        trade_filter_config=(
            trade_filter_config
        ),
    )

    audit_path = export_signal_audits(
        audits=result.signal_audits,
        output_path=args.audit_output,
    )

    outcomes = build_signal_outcomes(
        audits=result.signal_audits,
        broker_events=result.broker_events,
    )

    outcomes_path = (
        export_signal_outcomes(
            outcomes=outcomes,
            output_path=(
                args.outcomes_output
            ),
        )
    )

    print_report(
        result=result,
        outcomes=outcomes,
        trade_filter_config=(
            trade_filter_config
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