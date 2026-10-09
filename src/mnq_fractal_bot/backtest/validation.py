from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from mnq_fractal_bot.models.candle import (
    Candle,
)


@dataclass(frozen=True)
class ChronologicalSplit:
    total_candles: int

    warmup_candles: tuple[
        Candle,
        ...
    ]

    validation_candles: tuple[
        Candle,
        ...
    ]

    split_index: int

    validation_fraction: float

    validation_start: datetime

    validation_end: datetime


def split_chronologically(
    candles: Sequence[Candle],
    validation_fraction: float = 0.30,
) -> ChronologicalSplit:
    """
    Split candles chronologically.

    Example:

        validation_fraction = 0.30

        first 70%
            -> warm-up / earlier period

        final 30%
            -> validation period

    IMPORTANT:
    Data is never shuffled.
    """

    candles = list(
        candles
    )

    # ==================================================
    # BASIC VALIDATION
    # ==================================================

    if len(candles) < 2:
        raise ValueError(
            "At least 2 candles are required."
        )

    if not (
        0 < validation_fraction < 1
    ):
        raise ValueError(
            "validation_fraction must be "
            "between 0 and 1."
        )

    # ==================================================
    # VERIFY CHRONOLOGICAL ORDER
    # ==================================================

    for index in range(
        1,
        len(candles),
    ):
        previous = candles[
            index - 1
        ]

        current = candles[
            index
        ]

        if (
            current.timestamp
            <= previous.timestamp
        ):
            raise ValueError(
                "Candles must be in strictly "
                "increasing timestamp order."
            )

    # ==================================================
    # CALCULATE SPLIT
    # ==================================================

    validation_count = max(
        1,
        int(
            len(candles)
            * validation_fraction
        ),
    )

    split_index = (
        len(candles)
        - validation_count
    )

    # Protect against an empty warm-up period.
    if split_index <= 0:
        raise ValueError(
            "Validation period leaves no "
            "warm-up candles."
        )

    warmup_candles = tuple(
        candles[
            :split_index
        ]
    )

    validation_candles = tuple(
        candles[
            split_index:
        ]
    )

    # ==================================================
    # RESULT
    # ==================================================

    return ChronologicalSplit(
        total_candles=len(
            candles
        ),

        warmup_candles=(
            warmup_candles
        ),

        validation_candles=(
            validation_candles
        ),

        split_index=(
            split_index
        ),

        validation_fraction=(
            validation_fraction
        ),

        validation_start=(
            validation_candles[
                0
            ].timestamp
        ),

        validation_end=(
            validation_candles[
                -1
            ].timestamp
        ),
    )