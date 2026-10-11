from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

from mnq_fractal_bot.models.candle import Candle


@dataclass(frozen=True)
class FeedQualityReport:
    total_candles: int
    start_time: datetime | None
    end_time: datetime | None
    gap_count: int
    missing_session_breaks: int
    affected_hours: tuple[int, ...]

    @property
    def has_intraday_gaps(self) -> bool:
        return self.gap_count > 0


def audit_candle_feed_gaps(
    candles: Sequence[Candle],
    expected_step: timedelta = timedelta(minutes=5),
    max_normal_gap: timedelta = timedelta(minutes=15),
) -> FeedQualityReport:
    """
    Audit an intraday candle series for gaps.
    Identifies intraday gaps and recurring hourly missing bars (e.g. 04:00:00 UTC).
    """
    if not candles:
        return FeedQualityReport(
            total_candles=0,
            start_time=None,
            end_time=None,
            gap_count=0,
            missing_session_breaks=0,
            affected_hours=(),
        )

    gaps = 0
    missing_breaks = 0
    affected_hours_set: set[int] = set()

    for i in range(len(candles) - 1):
        c1 = candles[i]
        c2 = candles[i + 1]
        delta = c2.timestamp - c1.timestamp

        if delta > expected_step:
            gaps += 1
            # Check if this gap spans across an hour boundary
            missing_hour = (c1.timestamp + expected_step).hour
            affected_hours_set.add(missing_hour)

            # Specific check for 10m gaps (e.g. 03:55 -> 04:05 skipping single 04:00 bar)
            if delta <= max_normal_gap:
                missing_breaks += 1

    return FeedQualityReport(
        total_candles=len(candles),
        start_time=candles[0].timestamp,
        end_time=candles[-1].timestamp,
        gap_count=gaps,
        missing_session_breaks=missing_breaks,
        affected_hours=tuple(sorted(affected_hours_set)),
    )
