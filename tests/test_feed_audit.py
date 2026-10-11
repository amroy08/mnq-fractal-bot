from datetime import datetime, timedelta, timezone

from mnq_fractal_bot.data.feed_audit import audit_candle_feed_gaps
from mnq_fractal_bot.models.candle import Candle


def make_candle(ts: datetime) -> Candle:
    return Candle(
        timestamp=ts,
        open=100.0,
        high=105.0,
        low=95.0,
        close=102.0,
        volume=10,
    )


def test_audit_empty_candles():
    report = audit_candle_feed_gaps([])
    assert report.total_candles == 0
    assert report.gap_count == 0
    assert report.has_intraday_gaps is False


def test_audit_continuous_candles():
    start = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)
    candles = [
        make_candle(start + timedelta(minutes=5 * i))
        for i in range(12)
    ]

    report = audit_candle_feed_gaps(candles)
    assert report.total_candles == 12
    assert report.gap_count == 0
    assert report.has_intraday_gaps is False


def test_audit_detects_single_missing_bar():
    # 03:50, 03:55, (skips 04:00), 04:05
    c1 = make_candle(datetime(2026, 9, 22, 3, 50, tzinfo=timezone.utc))
    c2 = make_candle(datetime(2026, 9, 22, 3, 55, tzinfo=timezone.utc))
    c3 = make_candle(datetime(2026, 9, 22, 4, 5, tzinfo=timezone.utc))

    report = audit_candle_feed_gaps([c1, c2, c3])
    assert report.total_candles == 3
    assert report.gap_count == 1
    assert report.missing_session_breaks == 1
    assert 4 in report.affected_hours
    assert report.has_intraday_gaps is True
