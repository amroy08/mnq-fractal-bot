import csv
from datetime import datetime
from pathlib import Path

from mnq_fractal_bot.backtest.parity import (
    ParitySignal,
)


# ==========================================================
# DATETIME
# ==========================================================


def _parse_datetime(
    value: str,
) -> datetime:
    value = value.strip()

    if not value:
        raise ValueError(
            "Timestamp cannot be empty."
        )

    # Allow:
    #
    # 2026-10-01T14:00:00+00:00
    #
    # and:
    #
    # 2026-10-01T14:00:00Z

    if value.endswith("Z"):
        value = (
            value[:-1]
            + "+00:00"
        )

    timestamp = (
        datetime.fromisoformat(
            value
        )
    )

    if timestamp.tzinfo is None:
        raise ValueError(
            "Parity timestamps must "
            "include timezone information."
        )

    return timestamp


# ==========================================================
# FLOAT
# ==========================================================


def _parse_float(
    value: str,
    field_name: str,
) -> float:
    value = value.strip()

    if not value:
        raise ValueError(
            f"{field_name} cannot be empty."
        )

    return float(
        value
    )


# ==========================================================
# DIRECTION
# ==========================================================


def _parse_direction(
    value: str,
) -> str:
    value = (
        value.strip()
        .upper()
    )

    # Normal text format.
    if value in {
        "LONG",
        "SHORT",
    }:
        return value

    # TradingView parity plots will use:
    #
    # +1 = LONG
    # -1 = SHORT
    if value in {
        "1",
        "1.0",
        "+1",
        "+1.0",
    }:
        return "LONG"

    if value in {
        "-1",
        "-1.0",
    }:
        return "SHORT"

    raise ValueError(
        "Unsupported direction value: "
        f"{value}"
    )


# ==========================================================
# ENTRY ZONE
# ==========================================================


def _parse_entry_name(
    value: str,
) -> str:
    value = (
        value.strip()
        .upper()
    )

    # Python audit format.
    if value in {
        "C3 ENTRY ZONE",
        "C4 ENTRY ZONE",
    }:
        return value

    # Simpler CSV format.
    if value in {
        "C3",
        "3",
        "3.0",
    }:
        return "C3 ENTRY ZONE"

    if value in {
        "C4",
        "4",
        "4.0",
    }:
        return "C4 ENTRY ZONE"

    raise ValueError(
        "Unsupported entry zone value: "
        f"{value}"
    )


# ==========================================================
# PYTHON AUDIT CSV
# ==========================================================


def load_python_audit_signals(
    csv_path: str | Path,
) -> list[ParitySignal]:
    """
    Load signals from our Python
    fractal_signal_audit CSV.

    Expected columns:

        created_at
        direction
        entry_name
        entry_price
        stop_price
        preferred_target
    """

    csv_path = Path(
        csv_path
    )

    signals: list[
        ParitySignal
    ] = []

    with csv_path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(
            file
        )

        required_columns = {
            "created_at",
            "direction",
            "entry_name",
            "entry_price",
            "stop_price",
            "preferred_target",
        }

        actual_columns = set(
            reader.fieldnames
            or []
        )

        missing = (
            required_columns
            - actual_columns
        )

        if missing:
            raise ValueError(
                "Python audit CSV is "
                "missing columns: "
                + ", ".join(
                    sorted(
                        missing
                    )
                )
            )

        for row_number, row in enumerate(
            reader,
            start=2,
        ):
            try:
                signal = (
                    ParitySignal(
                        timestamp=(
                            _parse_datetime(
                                row[
                                    "created_at"
                                ]
                            )
                        ),

                        direction=(
                            _parse_direction(
                                row[
                                    "direction"
                                ]
                            )
                        ),

                        entry_name=(
                            _parse_entry_name(
                                row[
                                    "entry_name"
                                ]
                            )
                        ),

                        entry_price=(
                            _parse_float(
                                row[
                                    "entry_price"
                                ],
                                "entry_price",
                            )
                        ),

                        stop_price=(
                            _parse_float(
                                row[
                                    "stop_price"
                                ],
                                "stop_price",
                            )
                        ),

                        target_price=(
                            _parse_float(
                                row[
                                    "preferred_target"
                                ],
                                "preferred_target",
                            )
                        ),
                    )
                )

            except Exception as exc:
                raise ValueError(
                    "Invalid Python audit "
                    f"row {row_number}: "
                    f"{exc}"
                ) from exc

            signals.append(
                signal
            )

    return signals


# ==========================================================
# TRADINGVIEW PARITY CSV
# ==========================================================


def load_tradingview_parity_signals(
    csv_path: str | Path,
) -> list[ParitySignal]:
    """
    Load the compact parity CSV that
    we will export from TradingView.

    Expected columns:

        timestamp
        direction
        entry_zone
        entry_price
        stop_price
        target_price

    Direction can be:

        LONG / SHORT

    or:

        1  = LONG
        -1 = SHORT

    Entry zone can be:

        C3 / C4

    or:

        3 / 4
    """

    csv_path = Path(
        csv_path
    )

    signals: list[
        ParitySignal
    ] = []

    with csv_path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(
            file
        )

        required_columns = {
            "timestamp",
            "direction",
            "entry_zone",
            "entry_price",
            "stop_price",
            "target_price",
        }

        actual_columns = set(
            reader.fieldnames
            or []
        )

        missing = (
            required_columns
            - actual_columns
        )

        if missing:
            raise ValueError(
                "TradingView parity CSV is "
                "missing columns: "
                + ", ".join(
                    sorted(
                        missing
                    )
                )
            )

        for row_number, row in enumerate(
            reader,
            start=2,
        ):
            # --------------------------------------------------
            # TradingView chart exports can contain one row
            # for every candle.
            #
            # Blank parity rows mean:
            #
            # "No signal on this candle."
            #
            # Skip them.
            # --------------------------------------------------

            direction_value = (
                row.get(
                    "direction",
                    ""
                )
                or ""
            )

            if not direction_value.strip():
                continue

            try:
                signal = (
                    ParitySignal(
                        timestamp=(
                            _parse_datetime(
                                row[
                                    "timestamp"
                                ]
                            )
                        ),

                        direction=(
                            _parse_direction(
                                row[
                                    "direction"
                                ]
                            )
                        ),

                        entry_name=(
                            _parse_entry_name(
                                row[
                                    "entry_zone"
                                ]
                            )
                        ),

                        entry_price=(
                            _parse_float(
                                row[
                                    "entry_price"
                                ],
                                "entry_price",
                            )
                        ),

                        stop_price=(
                            _parse_float(
                                row[
                                    "stop_price"
                                ],
                                "stop_price",
                            )
                        ),

                        target_price=(
                            _parse_float(
                                row[
                                    "target_price"
                                ],
                                "target_price",
                            )
                        ),
                    )
                )

            except Exception as exc:
                raise ValueError(
                    "Invalid TradingView parity "
                    f"row {row_number}: "
                    f"{exc}"
                ) from exc

            signals.append(
                signal
            )

    return signals