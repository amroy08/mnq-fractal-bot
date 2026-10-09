import argparse
from pathlib import Path

from mnq_fractal_bot.backtest.audit_export import (
    export_signal_audits,
)

from mnq_fractal_bot.backtest.runner import (
    BacktestRunner,
)

from mnq_fractal_bot.data.csv_loader import (
    load_candles_from_csv,
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
) -> None:
    stats = result.stats

    print()
    print("=" * 60)
    print("MNQ FRACTAL MODEL - PAPER BACKTEST")
    print("=" * 60)

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

    print(
        f"Average winner    : "
        f"{format_money(stats.average_win)}"
    )

    print(
        f"Average loser     : "
        f"{format_money(stats.average_loss)}"
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

    if result.trade_log:
        print("TRADE LOG")
        print("-" * 60)

        for trade in result.trade_log:
            print(
                f"#{trade.trade_number} | "
                f"{trade.direction} | "
                f"Entry {trade.entry_price:.2f} | "
                f"Exit {trade.exit_price:.2f} | "
                f"{trade.exit_reason} | "
                f"P&L "
                f"{format_money(trade.gross_pnl)}"
            )

    else:
        print(
            "No completed trades were generated "
            "from this dataset."
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
    )

    return runner.run(
        candles
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run the MNQ Fractal Model "
            "paper backtest from CSV."
        )
    )

    parser.add_argument(
        "csv_path",
        help=(
            "Path to historical MNQ CSV."
        ),
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
        "--audit-output",
        default=(
            "data/fractal_signal_audit.csv"
        ),
        help=(
            "Where to save the Fractal "
            "signal audit CSV."
        ),
    )

    args = parser.parse_args()

    result = run_csv_backtest(
        csv_path=args.csv_path,
        lower_timeframe=args.timeframe,
        starting_balance=(
            args.starting_balance
        ),
    )

    audit_path = export_signal_audits(
        audits=result.signal_audits,
        output_path=args.audit_output,
    )

    print_report(
        result
    )

    print()
    print(
        "Signal audit saved to:"
    )

    print(
        audit_path
    )


if __name__ == "__main__":
    main()
    
    