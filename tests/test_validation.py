from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from mnq_fractal_bot.backtest.validation import (
    split_chronologically,
)

from mnq_fractal_bot.models.candle import (
    Candle,
)


START = datetime(
    2026,
    1,
    1,
    0,
    0,
    tzinfo=timezone.utc,
)


def make_candles(
    count: int,
):
    candles = []

    for index in range(
        count
    ):
        candles.append(
            Candle(
                timestamp=(
                    START
                    + timedelta(
                        minutes=(
                            index * 5
                        )
                    )
                ),

                open=100,
                high=101,
                low=99,
                close=100,

                volume=100,
            )
        )

    return candles


def test_70_30_split():
    candles = make_candles(
        100
    )

    result = (
        split_chronologically(
            candles,
            validation_fraction=0.30,
        )
    )

    assert (
        len(
            result.warmup_candles
        )
        == 70
    )

    assert (
        len(
            result.validation_candles
        )
        == 30
    )

    assert (
        result.split_index
        == 70
    )


def test_validation_starts_after_warmup():
    candles = make_candles(
        10
    )

    result = (
        split_chronologically(
            candles,
            validation_fraction=0.30,
        )
    )

    assert (
        result.validation_start
        ==
        candles[7].timestamp
    )

    assert (
        result.validation_end
        ==
        candles[9].timestamp
    )


def test_data_is_not_shuffled():
    candles = make_candles(
        20
    )

    result = (
        split_chronologically(
            candles,
            validation_fraction=0.25,
        )
    )

    combined = (
        list(
            result.warmup_candles
        )
        +
        list(
            result.validation_candles
        )
    )

    assert combined == candles


def test_invalid_fraction_zero():
    candles = make_candles(
        10
    )

    with pytest.raises(
        ValueError
    ):
        split_chronologically(
            candles,
            validation_fraction=0,
        )


def test_invalid_fraction_one():
    candles = make_candles(
        10
    )

    with pytest.raises(
        ValueError
    ):
        split_chronologically(
            candles,
            validation_fraction=1,
        )


def test_requires_multiple_candles():
    candles = make_candles(
        1
    )

    with pytest.raises(
        ValueError
    ):
        split_chronologically(
            candles,
        )


def test_rejects_out_of_order_data():
    candles = make_candles(
        5
    )

    candles[
        3
    ] = Candle(
        timestamp=(
            candles[
                1
            ].timestamp
        ),

        open=100,
        high=101,
        low=99,
        close=100,

        volume=100,
    )

    with pytest.raises(
        ValueError
    ):
        split_chronologically(
            candles,
        )
        
        