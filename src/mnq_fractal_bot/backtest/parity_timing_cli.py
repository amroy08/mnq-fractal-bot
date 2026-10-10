import argparse
from pathlib import Path

from mnq_fractal_bot.backtest.parity import (
    ParityReport,
    ParitySignal,
    compare_signals,
)

from mnq_fractal_bot.backtest.parity_cli import (
    calculate_strict_parity,
    filter_python_signals,
    parse_datetime,
)

from mnq_fractal_bot.backtest.parity_csv import (
    load_python_audit_signals,
)

from mnq_fractal_bot.backtest.parity_logs import (
    filter_tradingview_records,
    load_tradingview_parity_logs,
    records_to_signals,
)

from mnq_fractal_bot.backtest.parity_timing import (
    NearTimeMatch,
    find_near_time_matches,
)


# ==========================================================
# UNMATCHED SIGNALS
# ==========================================================


def extract_unmatched_signals(
    report: ParityReport,
) -> tuple[
    list[ParitySignal],
    list[ParitySignal],
]:
    """
    Return:

        TradingView signals missing in Python
        Python signals extra vs TradingView
    """

    missing_tv: list[
        ParitySignal
    ] = []

    extra_python: list[
        ParitySignal
    ] = []

    for match in report.matches:

        if (
            match.status
            == "MISSING_IN_PYTHON"
            and match.tradingview_signal
            is not None
        ):
            missing_tv.append(
                match.tradingview_signal
            )

        elif (
            match.status
            == "EXTRA_IN_PYTHON"
            and match.python_signal
            is not None
        ):
            extra_python.append(
                match.python_signal
            )

    return (
        missing_tv,
        extra_python,
    )


# ==========================================================
# ADJUSTED STRUCTURAL PARITY
# ==========================================================


def calculate_adjusted_structural_parity(
    report: ParityReport,
    near_matches: list[
        NearTimeMatch
    ],
) -> float:
    """
    A shifted pair currently appears in the
    strict report as TWO errors:

        1 missing TradingView signal
        +
        1 extra Python signal

    If they are paired as the same setup within
    the allowed timing window, collapse those
    two records into one comparison unit.

    Only shifted pairs with identical direction,
    zone, entry, stop and target count as correct.
    """

    collapsed_pairs = len(
        near_matches
    )

    denominator = (
        len(
            report.matches
        )
        - collapsed_pairs
    )

    if denominator <= 0:
        return 0.0

    shifted_exact = sum(
        1
        for match in near_matches
        if match.same_setup_values
    )

    numerator = (
        report.summary.exact_matches
        + shifted_exact
    )

    return (
        numerator
        / denominator
        * 100
    )


# ==========================================================
# DETAIL OUTPUT
# ==========================================================


def print_near_match_details(
    matches: list[
        NearTimeMatch
    ],
    limit: int,
) -> None:

    print()
    print("NEAR-TIME MATCH DETAILS")
    print("-" * 76)

    if not matches:
        print(
            "No missing/extra signals paired "
            "inside the timing window."
        )

        return

    for index, match in enumerate(
        matches[:limit],
        start=1,
    ):
        tv = match.tradingview
        py = match.python

        print()

        print(
            f"#{index}"
        )

        print(
            "TradingView : "
            f"{tv.timestamp.isoformat()}"
        )

        print(
            "Python      : "
            f"{py.timestamp.isoformat()}"
        )

        print(
            "Time shift  : "
            f"{match.difference_minutes:.0f} min"
        )

        print(
            "Direction   : "
            f"TV={tv.direction} | "
            f"PY={py.direction}"
        )

        print(
            "Entry zone  : "
            f"TV={tv.entry_name} | "
            f"PY={py.entry_name}"
        )

        print(
            "Entry diff  : "
            f"{match.entry_difference:.2f}"
        )

        print(
            "Stop diff   : "
            f"{match.stop_difference:.2f}"
        )

        print(
            "Target diff : "
            f"{match.target_difference:.2f}"
        )

        print(
            "Same setup values : "
            f"{'✅ YES' if match.same_setup_values else '❌ NO'}"
        )


# ==========================================================
# REPORT
# ==========================================================


def print_timing_report(
    report: ParityReport,
    near_matches: list[
        NearTimeMatch
    ],
    missing_count: int,
    extra_count: int,
    max_minutes: int,
) -> None:

    shifted_exact = sum(
        1
        for match in near_matches
        if match.same_setup_values
    )

    shifted_value_mismatch = (
        len(
            near_matches
        )
        - shifted_exact
    )

    remaining_missing = (
        missing_count
        - len(
            near_matches
        )
    )

    remaining_extra = (
        extra_count
        - len(
            near_matches
        )
    )

    strict_parity = (
        calculate_strict_parity(
            report
        )
    )

    adjusted_parity = (
        calculate_adjusted_structural_parity(
            report=report,
            near_matches=near_matches,
        )
    )

    print()
    print("=" * 76)

    print(
        "PINE ↔ PYTHON TIMING DIAGNOSTIC"
    )

    print("=" * 76)

    print()
    print("ORIGINAL EXACT-TIMESTAMP RESULT")
    print("-" * 76)

    print(
        f"TradingView signals       : "
        f"{report.summary.tradingview_signals}"
    )

    print(
        f"Python signals            : "
        f"{report.summary.python_signals}"
    )

    print(
        f"Exact matches             : "
        f"{report.summary.exact_matches}"
    )

    print(
        f"Missing in Python         : "
        f"{missing_count}"
    )

    print(
        f"Extra in Python           : "
        f"{extra_count}"
    )

    print(
        f"Strict parity             : "
        f"{strict_parity:.2f}%"
    )

    print()
    print(
        f"±{max_minutes}-MINUTE TIMING CHECK"
    )

    print("-" * 76)

    print(
        f"Missing/extra pairs found : "
        f"{len(near_matches)}"
    )

    print(
        f"Same values except time   : "
        f"{shifted_exact}"
    )

    print(
        f"Paired but values differ  : "
        f"{shifted_value_mismatch}"
    )

    print(
        f"Still missing in Python   : "
        f"{remaining_missing}"
    )

    print(
        f"Still extra in Python     : "
        f"{remaining_extra}"
    )

    print()
    print("ADJUSTED RESULT")
    print("-" * 76)

    print(
        "Exact timestamp strict parity : "
        f"{strict_parity:.2f}%"
    )

    print(
        "Adjusted structural parity     : "
        f"{adjusted_parity:.2f}%"
    )

    print()
    print("=" * 76)


# ==========================================================
# MAIN
# ==========================================================


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose 5-minute timing "
            "differences between TradingView "
            "Pine and Python Fractal signals."
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
        required=True,
    )

    parser.add_argument(
        "--end",
        required=True,
    )

    parser.add_argument(
        "--max-stop-points",
        type=float,
        default=50.0,
    )

    parser.add_argument(
        "--max-time-shift-minutes",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--detail-limit",
        type=int,
        default=20,
    )

    args = parser.parse_args()

    start_time = parse_datetime(
        args.start
    )

    end_time = parse_datetime(
        args.end
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

    tv_records = (
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
            tv_records
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

    python_signals = (
        filter_python_signals(
            signals=python_signals,

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
    # EXACT COMPARISON
    # ======================================================

    report = compare_signals(
        python_signals=(
            python_signals
        ),

        tradingview_signals=(
            tv_signals
        ),

        price_tolerance=0.001,
    )

    # ======================================================
    # GET ONLY MISSING + EXTRA
    # ======================================================

    (
        missing_tv,
        extra_python,
    ) = extract_unmatched_signals(
        report
    )

    # ======================================================
    # NEAR-TIME COMPARISON
    # ======================================================

    near_matches = (
        find_near_time_matches(
            tradingview_signals=(
                missing_tv
            ),

            python_signals=(
                extra_python
            ),

            max_minutes=(
                args.max_time_shift_minutes
            ),
        )
    )

    # ======================================================
    # OUTPUT
    # ======================================================

    print_timing_report(
        report=report,

        near_matches=(
            near_matches
        ),

        missing_count=len(
            missing_tv
        ),

        extra_count=len(
            extra_python
        ),

        max_minutes=(
            args.max_time_shift_minutes
        ),
    )

    print_near_match_details(
        matches=near_matches,

        limit=(
            args.detail_limit
        ),
    )


if __name__ == "__main__":
    main()