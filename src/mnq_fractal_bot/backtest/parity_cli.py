import argparse
from datetime import datetime
from pathlib import Path

from mnq_fractal_bot.backtest.parity import (
    ParityReport,
    ParitySignal,
    compare_signals,
)

from mnq_fractal_bot.backtest.parity_csv import (
    load_python_audit_signals,
)

from mnq_fractal_bot.backtest.parity_logs import (
    filter_tradingview_records,
    load_tradingview_parity_logs,
    records_to_signals,
)


# ==========================================================
# DATETIME
# ==========================================================


def parse_datetime(
    value: str,
) -> datetime:
    """
    Example:

        2026-09-20T22:10:00+00:00
    """

    value = value.strip()

    if value.endswith("Z"):
        value = (
            value[:-1]
            + "+00:00"
        )

    timestamp = datetime.fromisoformat(
        value
    )

    if timestamp.tzinfo is None:
        raise ValueError(
            "Datetime must include timezone."
        )

    return timestamp


# ==========================================================
# PYTHON FILTER
# ==========================================================


def filter_python_signals(
    signals: list[ParitySignal],
    max_stop_points: float | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    c3_only: bool = True,
) -> list[ParitySignal]:
    filtered = []

    for signal in signals:

        # ----------------------------------------------
        # C3 ONLY
        # ----------------------------------------------

        if (
            c3_only
            and signal.entry_name
            != "C3 ENTRY ZONE"
        ):
            continue

        # ----------------------------------------------
        # STOP DISTANCE
        # ----------------------------------------------

        stop_points = abs(
            signal.entry_price
            - signal.stop_price
        )

        if (
            max_stop_points
            is not None
            and stop_points
            > max_stop_points
        ):
            continue

        # ----------------------------------------------
        # TIME RANGE
        # ----------------------------------------------

        if (
            start_time is not None
            and signal.timestamp
            < start_time
        ):
            continue

        if (
            end_time is not None
            and signal.timestamp
            > end_time
        ):
            continue

        filtered.append(
            signal
        )

    return filtered


# ==========================================================
# STRICT PARITY
# ==========================================================


def calculate_strict_parity(
    report: ParityReport,
) -> float:
    """
    Existing parity_percent measures:

        exact TradingView matches
        -------------------------
        TradingView signals

    That is useful, but does not fully penalize
    EXTRA Python signals.

    Strict parity uses every unique comparison
    record in the denominator.
    """

    total = len(
        report.matches
    )

    if total == 0:
        return 0.0

    return (
        report.summary.exact_matches
        / total
        * 100
    )


# ==========================================================
# HELPERS
# ==========================================================


def price_text(
    value: float,
) -> str:
    return f"{value:.2f}"


def signal_time(
    signal: ParitySignal | None,
) -> str:
    if signal is None:
        return "-"

    return (
        signal.timestamp
        .isoformat()
    )


# ==========================================================
# MISMATCH DETAILS
# ==========================================================


def print_mismatch_details(
    report: ParityReport,
    limit: int = 10,
) -> None:

    mismatches = [
        match
        for match in report.matches
        if not match.exact_match
    ]

    print()
    print("MISMATCH EXAMPLES")
    print("-" * 72)

    if not mismatches:
        print(
            "No mismatches found. ✅"
        )

        return

    for index, match in enumerate(
        mismatches[:limit],
        start=1,
    ):
        python_signal = (
            match.python_signal
        )

        tv_signal = (
            match.tradingview_signal
        )

        print()

        print(
            f"#{index}  "
            f"{match.status}"
        )

        print(
            "TradingView time : "
            f"{signal_time(tv_signal)}"
        )

        print(
            "Python time      : "
            f"{signal_time(python_signal)}"
        )

        if (
            tv_signal is not None
            and python_signal is not None
        ):

            print(
                "Direction        : "
                f"TV={tv_signal.direction} | "
                f"PY={python_signal.direction} | "
                f"{'✅' if match.direction_match else '❌'}"
            )

            print(
                "Entry zone       : "
                f"TV={tv_signal.entry_name} | "
                f"PY={python_signal.entry_name} | "
                f"{'✅' if match.entry_name_match else '❌'}"
            )

            print(
                "Entry            : "
                f"TV={price_text(tv_signal.entry_price)} | "
                f"PY={price_text(python_signal.entry_price)} | "
                f"{'✅' if match.entry_price_match else '❌'}"
            )

            print(
                "Stop             : "
                f"TV={price_text(tv_signal.stop_price)} | "
                f"PY={price_text(python_signal.stop_price)} | "
                f"{'✅' if match.stop_price_match else '❌'}"
            )

            print(
                "Target           : "
                f"TV={price_text(tv_signal.target_price)} | "
                f"PY={price_text(python_signal.target_price)} | "
                f"{'✅' if match.target_price_match else '❌'}"
            )


# ==========================================================
# REPORT
# ==========================================================


def print_report(
    report: ParityReport,
    raw_tv_count: int,
    filtered_tv_count: int,
    raw_python_count: int,
    filtered_python_count: int,
    start_time: datetime | None,
    end_time: datetime | None,
    max_stop_points: float | None,
) -> None:

    summary = (
        report.summary
    )

    strict_parity = (
        calculate_strict_parity(
            report
        )
    )

    print()
    print("=" * 72)

    print(
        "TRADINGVIEW PINE ↔ PYTHON "
        "FRACTAL PARITY"
    )

    print("=" * 72)

    print()
    print("COMPARISON CONFIGURATION")
    print("-" * 72)

    print(
        "Entry zone         : C3 ONLY"
    )

    print(
        "Max stop points    : "
        f"{max_stop_points}"
    )

    print(
        "Start time         : "
        f"{start_time}"
    )

    print(
        "End time           : "
        f"{end_time}"
    )

    print(
        "Price tolerance    : 0.001"
    )

    # ======================================================
    # SOURCE COUNTS
    # ======================================================

    print()
    print("SOURCE DATA")
    print("-" * 72)

    print(
        f"TradingView raw    : "
        f"{raw_tv_count}"
    )

    print(
        f"TradingView filtered: "
        f"{filtered_tv_count}"
    )

    print(
        f"Python raw         : "
        f"{raw_python_count}"
    )

    print(
        f"Python filtered    : "
        f"{filtered_python_count}"
    )

    # ======================================================
    # PARITY
    # ======================================================

    print()
    print("PARITY RESULTS")
    print("-" * 72)

    print(
        f"TradingView signals: "
        f"{summary.tradingview_signals}"
    )

    print(
        f"Python signals     : "
        f"{summary.python_signals}"
    )

    print()

    print(
        f"Timestamp matches  : "
        f"{summary.matched_signals}"
    )

    print(
        f"Exact matches      : "
        f"{summary.exact_matches}"
    )

    print()

    print(
        f"Missing in Python  : "
        f"{summary.missing_in_python}"
    )

    print(
        f"Extra in Python    : "
        f"{summary.extra_in_python}"
    )

    # ======================================================
    # FIELD MISMATCHES
    # ======================================================

    print()
    print("FIELD MISMATCHES")
    print("-" * 72)

    print(
        f"Direction          : "
        f"{summary.direction_mismatches}"
    )

    print(
        f"Entry zone         : "
        f"{summary.entry_name_mismatches}"
    )

    print(
        f"Entry price        : "
        f"{summary.entry_price_mismatches}"
    )

    print(
        f"Stop price         : "
        f"{summary.stop_price_mismatches}"
    )

    print(
        f"Target price       : "
        f"{summary.target_price_mismatches}"
    )

    # ======================================================
    # SCORE
    # ======================================================

    print()
    print("PARITY SCORE")
    print("-" * 72)

    print(
        "TradingView exact coverage : "
        f"{summary.parity_percent:.2f}%"
    )

    print(
        "STRICT PARITY              : "
        f"{strict_parity:.2f}%"
    )

    print()
    print("=" * 72)


# ==========================================================
# MAIN
# ==========================================================


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Compare TradingView Fractal "
            "signals against Python."
        )
    )

    parser.add_argument(
        "--tradingview",
        required=True,
    )

    parser.add_argument(
        "--python-audit",
        required=True,
    )

    parser.add_argument(
        "--start",
        default=None,
    )

    parser.add_argument(
        "--end",
        default=None,
    )

    parser.add_argument(
        "--max-stop-points",
        type=float,
        default=None,
    )

    parser.add_argument(
        "--mismatch-limit",
        type=int,
        default=10,
    )

    args = parser.parse_args()

    # ======================================================
    # TIME RANGE
    # ======================================================

    start_time = (
        parse_datetime(
            args.start
        )
        if args.start
        else None
    )

    end_time = (
        parse_datetime(
            args.end
        )
        if args.end
        else None
    )

    # ======================================================
    # TRADINGVIEW
    # ======================================================

    tv_records = (
        load_tradingview_parity_logs(
            Path(
                args.tradingview
            )
        )
    )

    raw_tv_count = len(
        tv_records
    )

    tv_filtered = (
        filter_tradingview_records(
            records=tv_records,

            max_stop_points=(
                args.max_stop_points
            ),

            start_time=(
                start_time
            ),

            end_time=(
                end_time
            ),
        )
    )

    tv_signals = (
        records_to_signals(
            tv_filtered
        )
    )

    # ======================================================
    # PYTHON
    # ======================================================

    python_signals = (
        load_python_audit_signals(
            Path(
                args.python_audit
            )
        )
    )

    raw_python_count = len(
        python_signals
    )

    python_filtered = (
        filter_python_signals(
            signals=(
                python_signals
            ),

            max_stop_points=(
                args.max_stop_points
            ),

            start_time=(
                start_time
            ),

            end_time=(
                end_time
            ),

            c3_only=True,
        )
    )

    # ======================================================
    # COMPARE
    # ======================================================

    report = compare_signals(
        python_signals=(
            python_filtered
        ),

        tradingview_signals=(
            tv_signals
        ),

        price_tolerance=0.001,
    )

    # ======================================================
    # REPORT
    # ======================================================

    print_report(
        report=report,

        raw_tv_count=(
            raw_tv_count
        ),

        filtered_tv_count=len(
            tv_signals
        ),

        raw_python_count=(
            raw_python_count
        ),

        filtered_python_count=len(
            python_filtered
        ),

        start_time=(
            start_time
        ),

        end_time=(
            end_time
        ),

        max_stop_points=(
            args.max_stop_points
        ),
    )

    print_mismatch_details(
        report=report,

        limit=(
            args.mismatch_limit
        ),
    )


if __name__ == "__main__":
    main()