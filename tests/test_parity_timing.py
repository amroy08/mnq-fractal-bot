from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from mnq_fractal_bot.backtest.parity import (
    ParitySignal,
)

from mnq_fractal_bot.backtest.parity_timing import (
    find_near_time_matches,
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


def test_exact_time_matches():
    tv = [
        make_signal()
    ]

    py = [
        make_signal()
    ]

    matches = (
        find_near_time_matches(
            tv,
            py,
        )
    )

    assert len(
        matches
    ) == 1

    assert (
        matches[0]
        .difference_minutes
        == 0
    )


def test_five_minute_shift_matches():
    tv = [
        make_signal(
            minutes=5
        )
    ]

    py = [
        make_signal(
            minutes=0
        )
    ]

    matches = (
        find_near_time_matches(
            tv,
            py,
            max_minutes=5,
        )
    )

    assert len(
        matches
    ) == 1

    assert (
        matches[0]
        .difference_minutes
        == 5
    )


def test_six_minute_shift_rejected():
    tv = [
        make_signal(
            minutes=6
        )
    ]

    py = [
        make_signal()
    ]

    matches = (
        find_near_time_matches(
            tv,
            py,
            max_minutes=5,
        )
    )

    assert matches == []


def test_price_difference_recorded():
    tv = [
        make_signal(
            entry=30000.25
        )
    ]

    py = [
        make_signal(
            entry=30000
        )
    ]

    matches = (
        find_near_time_matches(
            tv,
            py,
        )
    )

    assert (
        matches[0]
        .entry_difference
        == 0.25
    )

    assert (
        matches[0]
        .same_setup_values
        is False
    )


def test_identical_values_are_same_setup():
    tv = [
        make_signal(
            minutes=5
        )
    ]

    py = [
        make_signal(
            minutes=0
        )
    ]

    matches = (
        find_near_time_matches(
            tv,
            py,
        )
    )

    assert (
        matches[0]
        .same_setup_values
        is True
    )


def test_negative_window_rejected():
    with pytest.raises(
        ValueError
    ):
        find_near_time_matches(
            [],
            [],
            max_minutes=-1,
        )