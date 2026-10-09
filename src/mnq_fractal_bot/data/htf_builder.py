from collections.abc import Sequence

from mnq_fractal_bot.data.htf_boundaries import get_htf_bucket_start
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


class DevelopingHTFBuilder:
    def __init__(self, higher_timeframe: str):
        self.higher_timeframe = higher_timeframe
        self.current_candle: Candle | None = None
        self.current_bucket_start = None

    def update(
        self,
        candle: Candle,
    ) -> tuple[Candle | None, Candle]:
        bucket_start = get_htf_bucket_start(
            candle.timestamp,
            self.higher_timeframe,
        )

        # --------------------------------------------------
        # FIRST LTF CANDLE
        # Start the first developing HTF candle.
        # --------------------------------------------------
        if self.current_candle is None:
            self.current_bucket_start = bucket_start

            self.current_candle = Candle(
                timestamp=bucket_start,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
            )

            return None, self.current_candle

        # --------------------------------------------------
        # SAME HTF BUCKET
        # Update the developing HTF candle.
        # --------------------------------------------------
        if bucket_start == self.current_bucket_start:
            self.current_candle = Candle(
                timestamp=self.current_bucket_start,
                open=self.current_candle.open,
                high=max(
                    self.current_candle.high,
                    candle.high,
                ),
                low=min(
                    self.current_candle.low,
                    candle.low,
                ),
                close=candle.close,
                volume=(
                    self.current_candle.volume
                    + candle.volume
                ),
            )

            return None, self.current_candle

        # --------------------------------------------------
        # NEW HTF BUCKET
        # Previous HTF candle is now completed.
        # --------------------------------------------------
        completed_candle = self.current_candle

        self.current_bucket_start = bucket_start

        self.current_candle = Candle(
            timestamp=bucket_start,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
        )

        return completed_candle, self.current_candle