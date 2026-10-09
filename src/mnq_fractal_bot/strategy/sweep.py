from dataclasses import dataclass

from mnq_fractal_bot.models.candle import Candle


@dataclass(frozen=True)
class SweepState:
    bearish_breached: bool
    bearish_confirmed: bool
    bullish_breached: bool
    bullish_confirmed: bool


def detect_sweep(
    previous_htf: Candle,
    current_candle: Candle,
) -> SweepState:
    bearish_breached = (
        current_candle.high
        > previous_htf.high
    )

    bullish_breached = (
        current_candle.low
        < previous_htf.low
    )

    bearish_confirmed = (
        bearish_breached
        and current_candle.close
        < previous_htf.high
    )

    bullish_confirmed = (
        bullish_breached
        and current_candle.close
        > previous_htf.low
    )

    return SweepState(
        bearish_breached=bearish_breached,
        bearish_confirmed=bearish_confirmed,
        bullish_breached=bullish_breached,
        bullish_confirmed=bullish_confirmed,
    )