from datetime import (
    datetime,
    timedelta,
    timezone,
)

from mnq_fractal_bot.backtest.parity import (
    ParitySignal,
    compare_signals,
)

from mnq_fractal_bot.backtest.parity_timing import (
    find_near_time_matches,
)

from mnq_fractal_bot.backtest.parity_timing_cli import (
    calculate_adjusted_structural_parity,
    extract_unmatched_signals,
)


START = datetime(
    2026,
    9,
    25,
    5,
    0,
    tzinfo=timezone.utc,
)


def make_signal(
    minutes=0,
    entry=30000,
    stop=29975,
    target=30075,
):
    return ParitySignal(
        timestamp=(
            START
            + timedelta(
                minutes=minutes
            )
        ),

        direction="LONG",

        entry_name="C3 ENTRY ZONE",

        entry_price=entry,
        stop_price=stop,
        target_price=target,
    )


def test_extract_unmatched_signals():
    tv = [
        make_signal(
            minutes=5
        )
    ]

    python = [
        make_signal(
            minutes=0
        )
    ]

    report = compare_signals(
        python_signals=python,
        tradingview_signals=tv,
    )

    missing, extra = (
        extract_unmatched_signals(
            report
        )
    )

    assert len(
        missing
    ) == 1

    assert len(
        extra
    ) == 1


def test_shifted_identical_setup_can_reach_100_percent():
    tv = [
        make_signal(
            minutes=0
        ),

        make_signal(
            minutes=10
        ),
    ]

    python = [
        make_signal(
            minutes=0
        ),

        make_signal(
            minutes=5
        ),
    ]

    report = compare_signals(
        python_signals=python,
        tradingview_signals=tv,
    )

    missing, extra = (
        extract_unmatched_signals(
            report
        )
    )

    near = find_near_time_matches(
        tradingview_signals=missing,
        python_signals=extra,
        max_minutes=5,
    )

    adjusted = (
        calculate_adjusted_structural_parity(
            report,
            near,
        )
    )

    assert adjusted == 100


def test_shifted_price_mismatch_not_counted_exact():
    tv = [
        make_signal(
            minutes=0
        ),

        make_signal(
            minutes=10,
            entry=30000.25,
        ),
    ]

    python = [
        make_signal(
            minutes=0
        ),

        make_signal(
            minutes=5,
            entry=30000,
        ),
    ]

    report = compare_signals(
        python_signals=python,
        tradingview_signals=tv,
    )

    missing, extra = (
        extract_unmatched_signals(
            report
        )
    )

    near = find_near_time_matches(
        tradingview_signals=missing,
        python_signals=extra,
        max_minutes=5,
    )

    adjusted = (
        calculate_adjusted_structural_parity(
            report,
            near,
        )
    )

    assert adjusted == 50