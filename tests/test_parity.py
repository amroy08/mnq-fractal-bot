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


START = datetime(
    2026,
    10,
    1,
    14,
    0,
    tzinfo=timezone.utc,
)


def make_signal(
    minutes=0,
    direction="LONG",
    entry_name="C3 ENTRY ZONE",
    entry_price=30000.00,
    stop_price=29975.00,
    target_price=30075.00,
):
    return ParitySignal(
        timestamp=(
            START
            + timedelta(
                minutes=minutes
            )
        ),

        direction=direction,

        entry_name=entry_name,

        entry_price=entry_price,

        stop_price=stop_price,

        target_price=target_price,
    )


def test_exact_match():
    python_signal = (
        make_signal()
    )

    tradingview_signal = (
        make_signal()
    )

    report = compare_signals(
        python_signals=[
            python_signal
        ],

        tradingview_signals=[
            tradingview_signal
        ],
    )

    assert (
        report.summary
        .exact_matches
        == 1
    )

    assert (
        report.summary
        .parity_percent
        == 100
    )


def test_missing_in_python():
    report = compare_signals(
        python_signals=[],

        tradingview_signals=[
            make_signal()
        ],
    )

    assert (
        report.summary
        .missing_in_python
        == 1
    )

    assert (
        report.summary
        .exact_matches
        == 0
    )


def test_extra_in_python():
    report = compare_signals(
        python_signals=[
            make_signal()
        ],

        tradingview_signals=[],
    )

    assert (
        report.summary
        .extra_in_python
        == 1
    )


def test_direction_mismatch():
    python_signal = (
        make_signal(
            direction="LONG"
        )
    )

    tradingview_signal = (
        make_signal(
            direction="SHORT"
        )
    )

    report = compare_signals(
        python_signals=[
            python_signal
        ],

        tradingview_signals=[
            tradingview_signal
        ],
    )

    assert (
        report.summary
        .direction_mismatches
        == 1
    )

    assert (
        report.summary
        .exact_matches
        == 0
    )


def test_price_mismatch():
    python_signal = (
        make_signal(
            entry_price=30000
        )
    )

    tradingview_signal = (
        make_signal(
            entry_price=30000.25
        )
    )

    report = compare_signals(
        python_signals=[
            python_signal
        ],

        tradingview_signals=[
            tradingview_signal
        ],

        price_tolerance=0.001,
    )

    assert (
        report.summary
        .entry_price_mismatches
        == 1
    )


def test_price_tolerance():
    python_signal = (
        make_signal(
            entry_price=30000
        )
    )

    tradingview_signal = (
        make_signal(
            entry_price=30000.0005
        )
    )

    report = compare_signals(
        python_signals=[
            python_signal
        ],

        tradingview_signals=[
            tradingview_signal
        ],

        price_tolerance=0.001,
    )

    assert (
        report.summary
        .exact_matches
        == 1
    )


def test_negative_tolerance_rejected():
    with pytest.raises(
        ValueError
    ):
        compare_signals(
            python_signals=[],
            tradingview_signals=[],
            price_tolerance=-1,
        )