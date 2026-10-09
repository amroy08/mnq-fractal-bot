from collections.abc import Sequence

from mnq_fractal_bot.models.candle import Candle


def build_htf_candle(candles: Sequence[Candle]) -> Candle:
    if not candles:
        raise ValueError(
            "Cannot build an HTF candle from an empty candle list."
        )

    ordered = sorted(
        candles,
        key=lambda candle: candle.timestamp,
    )

    first = ordered[0]
    last = ordered[-1]

    return Candle(
        timestamp=first.timestamp,
        open=first.open,
        high=max(candle.high for candle in ordered),
        low=min(candle.low for candle in ordered),
        close=last.close,
        volume=sum(candle.volume for candle in ordered),
    )