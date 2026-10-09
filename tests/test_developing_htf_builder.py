from datetime import datetime
from zoneinfo import ZoneInfo

from mnq_fractal_bot.data.htf_builder import (
    DevelopingHTFBuilder,
)
from mnq_fractal_bot.models.candle import Candle


NY = ZoneInfo("America/New_York")


def make_candle(
    hour,
    minute,
    open_price,
    high,
    low,
    close,
    volume=100,
):
    return Candle(
        timestamp=datetime(
            2026,
            10,
            9,
            hour,
            minute,
            tzinfo=NY,
        ),
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def test_first_candle_starts_developing_htf():
    builder = DevelopingHTFBuilder("1h")

    completed, developing = builder.update(
        make_candle(
            19,
            0,
            31200,
            31210,
            31190,
            31205,
        )
    )

    assert completed is None

    assert developing.open == 31200
    assert developing.high == 31210
    assert developing.low == 31190
    assert developing.close == 31205
    assert developing.volume == 100


def test_same_bucket_updates_developing_htf():
    builder = DevelopingHTFBuilder("1h")

    builder.update(
        make_candle(
            19,
            0,
            31200,
            31210,
            31190,
            31205,
        )
    )

    completed, developing = builder.update(
        make_candle(
            19,
            5,
            31205,
            31220,
            31195,
            31218,
            150,
        )
    )

    assert completed is None

    assert developing.open == 31200
    assert developing.high == 31220
    assert developing.low == 31190
    assert developing.close == 31218
    assert developing.volume == 250


def test_new_bucket_completes_previous_htf():
    builder = DevelopingHTFBuilder("1h")

    builder.update(
        make_candle(
            19,
            0,
            31200,
            31210,
            31190,
            31205,
        )
    )

    builder.update(
        make_candle(
            19,
            55,
            31205,
            31225,
            31180,
            31220,
            150,
        )
    )

    completed, developing = builder.update(
        make_candle(
            20,
            0,
            31220,
            31230,
            31215,
            31228,
            120,
        )
    )

    assert completed is not None

    assert completed.open == 31200
    assert completed.high == 31225
    assert completed.low == 31180
    assert completed.close == 31220
    assert completed.volume == 250

    assert developing.open == 31220
    assert developing.high == 31230
    assert developing.low == 31215
    assert developing.close == 31228
    assert developing.volume == 120


def test_4h_builder_uses_session_boundary():
    builder = DevelopingHTFBuilder("4h")

    _, first = builder.update(
        make_candle(
            21,
            45,
            31200,
            31215,
            31190,
            31210,
        )
    )

    completed, second = builder.update(
        make_candle(
            22,
            0,
            31210,
            31225,
            31205,
            31220,
        )
    )

    assert completed is not None

    assert first.timestamp == datetime(
        2026,
        10,
        9,
        18,
        0,
        tzinfo=NY,
    )

    assert second.timestamp == datetime(
        2026,
        10,
        9,
        22,
        0,
        tzinfo=NY,
    )