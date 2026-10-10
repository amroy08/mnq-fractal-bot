from pathlib import Path

import pytest

from mnq_fractal_bot.backtest.parity_csv import (
    load_python_audit_signals,
    load_tradingview_parity_signals,
)


def write_file(
    path: Path,
    content: str,
):
    path.write_text(
        content,
        encoding="utf-8",
    )


def test_load_python_audit(
    tmp_path,
):
    path = (
        tmp_path
        / "python_audit.csv"
    )

    write_file(
        path,
        (
            "created_at,direction,"
            "entry_name,entry_price,"
            "stop_price,preferred_target\n"
            "2026-10-01T14:00:00+00:00,"
            "LONG,C3 ENTRY ZONE,"
            "30000.25,29975.00,30075.50\n"
        ),
    )

    signals = (
        load_python_audit_signals(
            path
        )
    )

    assert len(
        signals
    ) == 1

    signal = signals[
        0
    ]

    assert (
        signal.direction
        == "LONG"
    )

    assert (
        signal.entry_name
        == "C3 ENTRY ZONE"
    )

    assert (
        signal.entry_price
        == 30000.25
    )

    assert (
        signal.stop_price
        == 29975.00
    )

    assert (
        signal.target_price
        == 30075.50
    )


def test_load_tradingview_text_values(
    tmp_path,
):
    path = (
        tmp_path
        / "tv.csv"
    )

    write_file(
        path,
        (
            "timestamp,direction,"
            "entry_zone,entry_price,"
            "stop_price,target_price\n"
            "2026-10-01T14:00:00+00:00,"
            "SHORT,C3,"
            "30000,30025,29925\n"
        ),
    )

    signals = (
        load_tradingview_parity_signals(
            path
        )
    )

    assert len(
        signals
    ) == 1

    assert (
        signals[0].direction
        == "SHORT"
    )

    assert (
        signals[0].entry_name
        == "C3 ENTRY ZONE"
    )


def test_load_tradingview_numeric_values(
    tmp_path,
):
    path = (
        tmp_path
        / "tv.csv"
    )

    write_file(
        path,
        (
            "timestamp,direction,"
            "entry_zone,entry_price,"
            "stop_price,target_price\n"
            "2026-10-01T14:00:00+00:00,"
            "1,3,"
            "30000,29975,30075\n"
        ),
    )

    signals = (
        load_tradingview_parity_signals(
            path
        )
    )

    assert (
        signals[0].direction
        == "LONG"
    )

    assert (
        signals[0].entry_name
        == "C3 ENTRY ZONE"
    )


def test_blank_tradingview_rows_are_skipped(
    tmp_path,
):
    path = (
        tmp_path
        / "tv.csv"
    )

    write_file(
        path,
        (
            "timestamp,direction,"
            "entry_zone,entry_price,"
            "stop_price,target_price\n"
            "2026-10-01T13:55:00+00:00,"
            ",,,,,\n"
            "2026-10-01T14:00:00+00:00,"
            "1,3,30000,29975,30075\n"
        ),
    )

    signals = (
        load_tradingview_parity_signals(
            path
        )
    )

    assert len(
        signals
    ) == 1


def test_missing_python_column_rejected(
    tmp_path,
):
    path = (
        tmp_path
        / "bad.csv"
    )

    write_file(
        path,
        (
            "created_at,direction\n"
            "2026-10-01T14:00:00+00:00,"
            "LONG\n"
        ),
    )

    with pytest.raises(
        ValueError
    ):
        load_python_audit_signals(
            path
        )


def test_missing_tradingview_column_rejected(
    tmp_path,
):
    path = (
        tmp_path
        / "bad_tv.csv"
    )

    write_file(
        path,
        (
            "timestamp,direction\n"
            "2026-10-01T14:00:00+00:00,"
            "1\n"
        ),
    )

    with pytest.raises(
        ValueError
    ):
        load_tradingview_parity_signals(
            path
        )


def test_timezone_required(
    tmp_path,
):
    path = (
        tmp_path
        / "tv.csv"
    )

    write_file(
        path,
        (
            "timestamp,direction,"
            "entry_zone,entry_price,"
            "stop_price,target_price\n"
            "2026-10-01T14:00:00,"
            "1,3,30000,29975,30075\n"
        ),
    )

    with pytest.raises(
        ValueError
    ):
        load_tradingview_parity_signals(
            path
        )