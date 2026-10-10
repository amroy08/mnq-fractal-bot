from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


@dataclass(frozen=True)
class ParitySignal:
    timestamp: datetime

    direction: str
    entry_name: str

    entry_price: float
    stop_price: float
    target_price: float


@dataclass(frozen=True)
class ParityMatch:
    python_signal: ParitySignal | None
    tradingview_signal: ParitySignal | None

    status: str

    time_match: bool
    direction_match: bool
    entry_name_match: bool
    entry_price_match: bool
    stop_price_match: bool
    target_price_match: bool

    @property
    def exact_match(self) -> bool:
        return (
            self.status == "MATCHED"
            and self.time_match
            and self.direction_match
            and self.entry_name_match
            and self.entry_price_match
            and self.stop_price_match
            and self.target_price_match
        )


@dataclass(frozen=True)
class ParitySummary:
    python_signals: int
    tradingview_signals: int

    matched_signals: int
    exact_matches: int

    missing_in_python: int
    extra_in_python: int

    direction_mismatches: int
    entry_name_mismatches: int

    entry_price_mismatches: int
    stop_price_mismatches: int
    target_price_mismatches: int

    parity_percent: float


@dataclass(frozen=True)
class ParityReport:
    matches: tuple[
        ParityMatch,
        ...
    ]

    summary: ParitySummary


def _price_equal(
    first: float,
    second: float,
    tolerance: float,
) -> bool:
    return (
        abs(
            first
            - second
        )
        <= tolerance
    )


def compare_signals(
    python_signals: Iterable[ParitySignal],
    tradingview_signals: Iterable[ParitySignal],
    price_tolerance: float = 0.001,
) -> ParityReport:

    if price_tolerance < 0:
        raise ValueError(
            "price_tolerance cannot be negative."
        )

    python_signals = list(
        python_signals
    )

    tradingview_signals = list(
        tradingview_signals
    )

    # ==================================================
    # GROUP BY TIMESTAMP
    #
    # For our first parity version:
    #
    # timestamp is the primary matching key.
    # ==================================================

    python_by_time = {
        signal.timestamp: signal
        for signal in python_signals
    }

    tradingview_by_time = {
        signal.timestamp: signal
        for signal in tradingview_signals
    }

    all_times = sorted(
        set(
            python_by_time
        )
        | set(
            tradingview_by_time
        )
    )

    matches: list[
        ParityMatch
    ] = []

    for timestamp in all_times:

        python_signal = (
            python_by_time.get(
                timestamp
            )
        )

        tradingview_signal = (
            tradingview_by_time.get(
                timestamp
            )
        )

        # ==================================================
        # MISSING IN PYTHON
        # ==================================================

        if python_signal is None:
            matches.append(
                ParityMatch(
                    python_signal=None,
                    tradingview_signal=(
                        tradingview_signal
                    ),

                    status=(
                        "MISSING_IN_PYTHON"
                    ),

                    time_match=False,
                    direction_match=False,
                    entry_name_match=False,
                    entry_price_match=False,
                    stop_price_match=False,
                    target_price_match=False,
                )
            )

            continue

        # ==================================================
        # EXTRA IN PYTHON
        # ==================================================

        if tradingview_signal is None:
            matches.append(
                ParityMatch(
                    python_signal=(
                        python_signal
                    ),

                    tradingview_signal=None,

                    status=(
                        "EXTRA_IN_PYTHON"
                    ),

                    time_match=False,
                    direction_match=False,
                    entry_name_match=False,
                    entry_price_match=False,
                    stop_price_match=False,
                    target_price_match=False,
                )
            )

            continue

        # ==================================================
        # SAME TIMESTAMP
        # ==================================================

        direction_match = (
            python_signal.direction
            ==
            tradingview_signal.direction
        )

        entry_name_match = (
            python_signal.entry_name
            ==
            tradingview_signal.entry_name
        )

        entry_price_match = (
            _price_equal(
                python_signal.entry_price,
                tradingview_signal.entry_price,
                price_tolerance,
            )
        )

        stop_price_match = (
            _price_equal(
                python_signal.stop_price,
                tradingview_signal.stop_price,
                price_tolerance,
            )
        )

        target_price_match = (
            _price_equal(
                python_signal.target_price,
                tradingview_signal.target_price,
                price_tolerance,
            )
        )

        matches.append(
            ParityMatch(
                python_signal=(
                    python_signal
                ),

                tradingview_signal=(
                    tradingview_signal
                ),

                status="MATCHED",

                time_match=True,

                direction_match=(
                    direction_match
                ),

                entry_name_match=(
                    entry_name_match
                ),

                entry_price_match=(
                    entry_price_match
                ),

                stop_price_match=(
                    stop_price_match
                ),

                target_price_match=(
                    target_price_match
                ),
            )
        )

    # ==================================================
    # SUMMARY
    # ==================================================

    matched = [
        match
        for match in matches
        if match.status == "MATCHED"
    ]

    exact_matches = sum(
        1
        for match in matched
        if match.exact_match
    )

    missing_in_python = sum(
        1
        for match in matches
        if (
            match.status
            == "MISSING_IN_PYTHON"
        )
    )

    extra_in_python = sum(
        1
        for match in matches
        if (
            match.status
            == "EXTRA_IN_PYTHON"
        )
    )

    direction_mismatches = sum(
        1
        for match in matched
        if not match.direction_match
    )

    entry_name_mismatches = sum(
        1
        for match in matched
        if not match.entry_name_match
    )

    entry_price_mismatches = sum(
        1
        for match in matched
        if not match.entry_price_match
    )

    stop_price_mismatches = sum(
        1
        for match in matched
        if not match.stop_price_match
    )

    target_price_mismatches = sum(
        1
        for match in matched
        if not match.target_price_match
    )

    tradingview_count = len(
        tradingview_signals
    )

    if tradingview_count == 0:
        parity_percent = 0.0

    else:
        parity_percent = (
            exact_matches
            / tradingview_count
            * 100
        )

    summary = ParitySummary(
        python_signals=len(
            python_signals
        ),

        tradingview_signals=(
            tradingview_count
        ),

        matched_signals=len(
            matched
        ),

        exact_matches=(
            exact_matches
        ),

        missing_in_python=(
            missing_in_python
        ),

        extra_in_python=(
            extra_in_python
        ),

        direction_mismatches=(
            direction_mismatches
        ),

        entry_name_mismatches=(
            entry_name_mismatches
        ),

        entry_price_mismatches=(
            entry_price_mismatches
        ),

        stop_price_mismatches=(
            stop_price_mismatches
        ),

        target_price_mismatches=(
            target_price_mismatches
        ),

        parity_percent=(
            parity_percent
        ),
    )

    return ParityReport(
        matches=tuple(
            matches
        ),

        summary=summary,
    )