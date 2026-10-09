from collections.abc import Sequence
from dataclasses import dataclass

from mnq_fractal_bot.models.candle import Candle


@dataclass(frozen=True)
class CisdLevel:
    price: float
    start_index: int


def candle_attitude(candle: Candle) -> int:
    if candle.close > candle.open:
        return 1

    if candle.close < candle.open:
        return -1

    return 0


def find_cisd_level(
    candles: Sequence[Candle],
    extreme_index: int,
    bias: int,
) -> CisdLevel | None:
    if bias not in (1, -1):
        raise ValueError(
            "CISD bias must be 1 or -1."
        )

    if not 0 <= extreme_index < len(candles):
        raise IndexError(
            "Extreme index is outside candle history."
        )

    found_first = False

    cisd_price = None
    cisd_index = None

    # Start at the extreme candle and move backwards.
    for index in range(
        extreme_index,
        -1,
        -1,
    ):
        candle = candles[index]

        attitude = candle_attitude(candle)

        # Pine skips doji candles.
        if attitude == 0:
            continue

        if not found_first:
            if attitude == bias:
                found_first = True

                cisd_price = candle.open
                cisd_index = index

        else:
            # Opposite candle ends the sequence.
            if attitude != bias:
                break

            cisd_price = candle.open
            cisd_index = index

    if cisd_price is None or cisd_index is None:
        return None

    return CisdLevel(
        price=cisd_price,
        start_index=cisd_index,
    )