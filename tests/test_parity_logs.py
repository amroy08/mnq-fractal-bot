from datetime import (
    datetime,
    timezone,
)

import pytest

from mnq_fractal_bot.backtest.parity_logs import (
    filter_tradingview_records,
    load_tradingview_parity_logs,
    parse_tradingview_parity_line,
    records_to_signals,
)


SAMPLE_LONG = (
    "PARITY|"
    "time=1,789,351,200,000|"
    "c3time=1,789,351,200,000|"
    "direction=1|"
    "zone=3|"
    "entry=29,346|"
    "stop=29,289.5|"
    "target=29,369.25|"
    "stopPoints=56.5"
)


SAMPLE_SHORT = (
    "PARITY|"
    "time=1,789,354,800,000|"
    "c3time=1,789,354,800,000|"
    "direction=-1|"
    "zone=3|"
    "entry=29,357|"
    "stop=29,377.75|"
    "target=29,290|"
    "stopPoints=20.75"
)


def test_parse_long_record():
    record = (
        parse_tradingview_parity_line(
            SAMPLE_LONG
        )
    )

    assert (
        record.signal.direction
        == "LONG"
    )

    assert (
        record.signal.entry_name
        == "C3 ENTRY ZONE"
    )

    assert (
        record.signal.entry_price
        == 29346
    )

    assert (
        record.signal.stop_price
        == 29289.5
    )

    assert (
        record.signal.target_price
        == 29369.25
    )

    assert (
        record.stop_points
        == 56.5
    )


def test_parse_short_record():
    record = (
        parse_tradingview_parity_line(
            SAMPLE_SHORT
        )
    )

    assert (
        record.signal.direction
        == "SHORT"
    )

    assert (
        record.stop_points
        == 20.75
    )


def test_timestamp_is_utc():
    record = (
        parse_tradingview_parity_line(
            SAMPLE_LONG
        )
    )

    assert (
        record.signal.timestamp.tzinfo
        == timezone.utc
    )


def test_filter_max_stop():
    records = [
        parse_tradingview_parity_line(
            SAMPLE_LONG
        ),

        parse_tradingview_parity_line(
            SAMPLE_SHORT
        ),
    ]

    filtered = (
        filter_tradingview_records(
            records,
            max_stop_points=50,
        )
    )

    assert len(
        filtered
    ) == 1

    assert (
        filtered[
            0
        ].stop_points
        == 20.75
    )


def test_filter_time_range():
    records = [
        parse_tradingview_parity_line(
            SAMPLE_LONG
        ),

        parse_tradingview_parity_line(
            SAMPLE_SHORT
        ),
    ]

    start = datetime.fromtimestamp(
        1_789_354_000,
        tz=timezone.utc,
    )

    filtered = (
        filter_tradingview_records(
            records,
            start_time=start,
        )
    )

    assert len(
        filtered
    ) == 1

    assert (
        filtered[
            0
        ].signal.direction
        == "SHORT"
    )


def test_load_file(
    tmp_path,
):
    path = (
        tmp_path
        / "tv_logs.txt"
    )

    path.write_text(
        (
            SAMPLE_LONG
            + "\n"
            + SAMPLE_SHORT
            + "\n"
        ),
        encoding="utf-8",
    )

    records = (
        load_tradingview_parity_logs(
            path
        )
    )

    assert len(
        records
    ) == 2


def test_records_to_signals():
    records = [
        parse_tradingview_parity_line(
            SAMPLE_LONG
        )
    ]

    signals = (
        records_to_signals(
            records
        )
    )

    assert len(
        signals
    ) == 1

    assert (
        signals[
            0
        ].entry_price
        == 29346
    )


def test_invalid_line_rejected():
    with pytest.raises(
        ValueError
    ):
        parse_tradingview_parity_line(
            "THIS IS NOT PARITY"
        )