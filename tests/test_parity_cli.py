from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from mnq_fractal_bot.backtest.parity import (
    ParitySignal,
    compare_signals,
)

from mnq_fractal_bot.backtest.parity_cli import (
    calculate_strict_parity,
    filter_python_signals,
    parse_datetime,
)


START = datetime(
    2026,
    9,
    20,
    22,
    10,
    tzinfo=timezone.utc,
)


def make_signal(
    minutes=0,
    entry_name="C3 ENTRY ZONE",
    entry=30000,
    stop=29975,
):
    return ParitySignal(
        timestamp=(
            START
            + timedelta(
                minutes=minutes
            )
        ),

        direction="LONG",

        entry_name=(
            entry_name
        ),

        entry_price=entry,

        stop_price=stop,

        target_price=30075,
    )


def test_parse_datetime():
    result = parse_datetime(
        "2026-09-20T22:10:00+00:00"
    )

    assert (
        result.tzinfo
        is not None
    )


def test_naive_datetime_rejected():
    with pytest.raises(
        ValueError
    ):
        parse_datetime(
            "2026-09-20T22:10:00"
        )


def test_python_stop_filter():
    signals = [
        make_signal(
            entry=30000,
            stop=29975,
        ),

        make_signal(
            minutes=5,
            entry=30000,
            stop=29940,
        ),
    ]

    filtered = (
        filter_python_signals(
            signals,
            max_stop_points=50,
        )
    )

    assert len(
        filtered
    ) == 1


def test_python_c3_only():
    signals = [
        make_signal(
            entry_name=(
                "C3 ENTRY ZONE"
            )
        ),

        make_signal(
            minutes=5,
            entry_name=(
                "C4 ENTRY ZONE"
            ),
        ),
    ]

    filtered = (
        filter_python_signals(
            signals,
            c3_only=True,
        )
    )

    assert len(
        filtered
    ) == 1


def test_strict_parity_penalizes_extra_python():
    tv = [
        make_signal()
    ]

    python = [
        make_signal(),

        make_signal(
            minutes=5
        ),
    ]

    report = compare_signals(
        python_signals=python,
        tradingview_signals=tv,
    )

    strict = (
        calculate_strict_parity(
            report
        )
    )

    assert strict == 50