from dataclasses import dataclass
from datetime import timedelta

from mnq_fractal_bot.backtest.parity import (
    ParitySignal,
)


@dataclass(frozen=True)
class NearTimeMatch:
    tradingview: ParitySignal
    python: ParitySignal

    difference_minutes: float

    direction_match: bool
    entry_name_match: bool

    entry_difference: float
    stop_difference: float
    target_difference: float

    @property
    def prices_exact(self) -> bool:
        return (
            self.entry_difference <= 0.001
            and self.stop_difference <= 0.001
            and self.target_difference <= 0.001
        )

    @property
    def same_setup_values(self) -> bool:
        return (
            self.direction_match
            and self.entry_name_match
            and self.prices_exact
        )


def find_near_time_matches(
    tradingview_signals: list[ParitySignal],
    python_signals: list[ParitySignal],
    max_minutes: int = 5,
) -> list[NearTimeMatch]:

    if max_minutes < 0:
        raise ValueError(
            "max_minutes cannot be negative."
        )

    max_difference = timedelta(
        minutes=max_minutes
    )

    used_python_indexes: set[int] = set()

    matches: list[
        NearTimeMatch
    ] = []

    for tv_signal in tradingview_signals:

        best_index = None
        best_difference = None

        for index, py_signal in enumerate(
            python_signals
        ):
            if index in used_python_indexes:
                continue

            if (
                tv_signal.direction
                != py_signal.direction
            ):
                continue

            if (
                tv_signal.entry_name
                != py_signal.entry_name
            ):
                continue

            difference = abs(
                tv_signal.timestamp
                - py_signal.timestamp
            )

            if difference > max_difference:
                continue

            if (
                best_difference is None
                or difference < best_difference
            ):
                best_difference = difference
                best_index = index

        if best_index is None:
            continue

        py_signal = python_signals[
            best_index
        ]

        used_python_indexes.add(
            best_index
        )

        matches.append(
            NearTimeMatch(
                tradingview=tv_signal,
                python=py_signal,

                difference_minutes=(
                    best_difference.total_seconds()
                    / 60
                ),

                direction_match=(
                    tv_signal.direction
                    == py_signal.direction
                ),

                entry_name_match=(
                    tv_signal.entry_name
                    == py_signal.entry_name
                ),

                entry_difference=abs(
                    tv_signal.entry_price
                    - py_signal.entry_price
                ),

                stop_difference=abs(
                    tv_signal.stop_price
                    - py_signal.stop_price
                ),

                target_difference=abs(
                    tv_signal.target_price
                    - py_signal.target_price
                ),
            )
        )

    return matches