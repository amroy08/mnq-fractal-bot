from datetime import datetime, timezone

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.strategy.sweep import detect_sweep


def make_candle(
    open_price,
    high,
    low,
    close,
):
    return Candle(
        timestamp=datetime.now(timezone.utc),
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=100,
    )


def test_bearish_sweep_confirmed():
    previous_htf = make_candle(
        31200,
        31250,
        31150,
        31220,
    )

    current = make_candle(
        31220,
        31260,
        31200,
        31240,
    )

    result = detect_sweep(
        previous_htf,
        current,
    )

    assert result.bearish_breached is True
    assert result.bearish_confirmed is True

    assert result.bullish_breached is False
    assert result.bullish_confirmed is False


def test_bearish_breach_not_confirmed():
    previous_htf = make_candle(
        31200,
        31250,
        31150,
        31220,
    )

    current = make_candle(
        31220,
        31260,
        31200,
        31255,
    )

    result = detect_sweep(
        previous_htf,
        current,
    )

    assert result.bearish_breached is True
    assert result.bearish_confirmed is False


def test_bullish_sweep_confirmed():
    previous_htf = make_candle(
        31200,
        31250,
        31150,
        31220,
    )

    current = make_candle(
        31220,
        31230,
        31140,
        31170,
    )

    result = detect_sweep(
        previous_htf,
        current,
    )

    assert result.bullish_breached is True
    assert result.bullish_confirmed is True

    assert result.bearish_breached is False
    assert result.bearish_confirmed is False


def test_bullish_breach_not_confirmed():
    previous_htf = make_candle(
        31200,
        31250,
        31150,
        31220,
    )

    current = make_candle(
        31220,
        31230,
        31140,
        31145,
    )

    result = detect_sweep(
        previous_htf,
        current,
    )

    assert result.bullish_breached is True
    assert result.bullish_confirmed is False