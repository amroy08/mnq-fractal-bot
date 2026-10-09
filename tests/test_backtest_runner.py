from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from mnq_fractal_bot.backtest.runner import (
    BacktestRunner,
)

from mnq_fractal_bot.models.candle import (
    Candle,
)


NOW = datetime(
    2026,
    10,
    9,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_candle(
    timestamp,
    open_price=100,
    high=110,
    low=90,
    close=105,
):
    return Candle(
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=100,
    )


def test_empty_backtest():
    runner = BacktestRunner()

    result = runner.run(
        []
    )

    assert result.candle_count == 0

    assert len(
        result.trades
    ) == 0

    assert (
        result.stats.total_trades
        == 0
    )

    assert (
        result.final_snapshot
        is None
    )


def test_backtest_processes_candles():
    runner = BacktestRunner()

    candles = [
        make_candle(
            NOW
        ),
        make_candle(
            NOW
            + timedelta(minutes=5)
        ),
        make_candle(
            NOW
            + timedelta(minutes=10)
        ),
    ]

    result = runner.run(
        candles
    )

    assert result.candle_count == 3

    assert result.final_snapshot is not None

    # Not enough data yet for a completed
    # Fractal trade, which is expected.
    assert (
        result.stats.total_trades
        == 0
    )


def test_out_of_order_candles_are_rejected():
    runner = BacktestRunner()

    candles = [
        make_candle(
            NOW
            + timedelta(minutes=5)
        ),
        make_candle(
            NOW
        ),
    ]

    with pytest.raises(
        ValueError,
        match="strictly increasing",
    ):
        runner.run(
            candles
        )