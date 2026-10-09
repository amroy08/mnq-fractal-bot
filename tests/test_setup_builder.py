from datetime import datetime, timezone

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.strategy.setup_builder import (
    create_setup_candidates,
)


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


def test_creates_bearish_setup():
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

    result = create_setup_candidates(
        previous_htf=previous_htf,
        current_candle=current,
        bar_index=100,
        previous_htf_index=90,
    )

    assert result.bearish is not None
    assert result.bullish is None

    assert result.bearish.is_bullish is False
    assert result.bearish.is_confirmed is True
    assert result.bearish.sweep_price == 31250
    assert result.bearish.tracked_extreme == 31260
    assert result.bearish.liq_c1_price == 31150


def test_creates_bullish_setup():
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

    result = create_setup_candidates(
        previous_htf=previous_htf,
        current_candle=current,
        bar_index=100,
        previous_htf_index=90,
    )

    assert result.bullish is not None
    assert result.bearish is None

    assert result.bullish.is_bullish is True
    assert result.bullish.is_confirmed is True
    assert result.bullish.sweep_price == 31150
    assert result.bullish.tracked_extreme == 31140
    assert result.bullish.liq_c1_price == 31250


def test_can_create_both_sides():
    previous_htf = make_candle(
        31200,
        31250,
        31150,
        31220,
    )

    current = make_candle(
        31200,
        31260,
        31140,
        31200,
    )

    result = create_setup_candidates(
        previous_htf=previous_htf,
        current_candle=current,
        bar_index=100,
        previous_htf_index=90,
    )

    assert result.bearish is not None
    assert result.bullish is not None


def test_no_sweep_creates_no_setup():
    previous_htf = make_candle(
        31200,
        31250,
        31150,
        31220,
    )

    current = make_candle(
        31220,
        31240,
        31160,
        31230,
    )

    result = create_setup_candidates(
        previous_htf=previous_htf,
        current_candle=current,
        bar_index=100,
        previous_htf_index=90,
    )

    assert result.bearish is None
    assert result.bullish is None