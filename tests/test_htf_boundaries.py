from datetime import datetime

import pytest
from zoneinfo import ZoneInfo

from mnq_fractal_bot.data.htf_boundaries import (
    get_htf_bucket_start,
)


NY = ZoneInfo("America/New_York")


def test_4h_session_first_bucket():
    timestamp = datetime(
        2026, 10, 9, 19, 30, tzinfo=NY
    )

    result = get_htf_bucket_start(
        timestamp,
        "4h",
    )

    assert result == datetime(
        2026, 10, 9, 18, 0, tzinfo=NY
    )


def test_4h_second_bucket():
    timestamp = datetime(
        2026, 10, 9, 23, 15, tzinfo=NY
    )

    result = get_htf_bucket_start(
        timestamp,
        "4h",
    )

    assert result == datetime(
        2026, 10, 9, 22, 0, tzinfo=NY
    )


def test_4h_crosses_midnight():
    timestamp = datetime(
        2026, 10, 10, 3, 15, tzinfo=NY
    )

    result = get_htf_bucket_start(
        timestamp,
        "4h",
    )

    assert result == datetime(
        2026, 10, 10, 2, 0, tzinfo=NY
    )


def test_1h_boundary():
    timestamp = datetime(
        2026, 10, 9, 20, 42, tzinfo=NY
    )

    result = get_htf_bucket_start(
        timestamp,
        "1h",
    )

    assert result == datetime(
        2026, 10, 9, 20, 0, tzinfo=NY
    )


def test_rejects_timestamp_without_timezone():
    timestamp = datetime(
        2026, 10, 9, 20, 0
    )

    with pytest.raises(ValueError):
        get_htf_bucket_start(
            timestamp,
            "4h",
        )


def test_rejects_unsupported_htf():
    timestamp = datetime(
        2026, 10, 9, 20, 0, tzinfo=NY
    )

    with pytest.raises(ValueError):
        get_htf_bucket_start(
            timestamp,
            "3h",
        )
        