from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

from mnq_fractal_bot.backtest.parity import (
    ParitySignal,
)


@dataclass(frozen=True)
class TradingViewParityRecord:
    signal: ParitySignal

    c3_timestamp: datetime

    stop_points: float


def _parse_number(
    value: str,
) -> float:
    """
    TradingView logs may format numbers like:

        29,346
        1,789,351,200,000

    Remove commas before conversion.
    """

    clean = (
        value
        .strip()
        .replace(",", "")
    )

    return float(
        clean
    )


def _parse_epoch_ms(
    value: str,
) -> datetime:
    milliseconds = int(
        _parse_number(
            value
        )
    )

    return datetime.fromtimestamp(
        milliseconds / 1000,
        tz=timezone.utc,
    )


def _parse_direction(
    value: str,
) -> str:
    numeric = (
        _parse_number(
            value
        )
    )

    if numeric == 1:
        return "LONG"

    if numeric == -1:
        return "SHORT"

    raise ValueError(
        "Unsupported TradingView "
        f"direction: {value}"
    )


def parse_tradingview_parity_line(
    line: str,
) -> TradingViewParityRecord:
    line = line.strip()

    if not line.startswith(
        "PARITY|"
    ):
        raise ValueError(
            "TradingView parity line must "
            "start with PARITY|"
        )

    fields: dict[
        str,
        str,
    ] = {}

    parts = line.split(
        "|"
    )

    for part in parts[
        1:
    ]:
        if "=" not in part:
            continue

        key, value = (
            part.split(
                "=",
                1,
            )
        )

        fields[
            key.strip()
        ] = value.strip()

    required = {
        "time",
        "c3time",
        "direction",
        "zone",
        "entry",
        "stop",
        "target",
        "stopPoints",
    }

    missing = (
        required
        - set(
            fields
        )
    )

    if missing:
        raise ValueError(
            "TradingView parity line "
            "is missing fields: "
            + ", ".join(
                sorted(
                    missing
                )
            )
        )

    zone = int(
        _parse_number(
            fields[
                "zone"
            ]
        )
    )

    if zone == 3:
        entry_name = (
            "C3 ENTRY ZONE"
        )

    elif zone == 4:
        entry_name = (
            "C4 ENTRY ZONE"
        )

    else:
        raise ValueError(
            "Unsupported TradingView "
            f"entry zone: {zone}"
        )

    signal = ParitySignal(
        timestamp=(
            _parse_epoch_ms(
                fields[
                    "time"
                ]
            )
        ),

        direction=(
            _parse_direction(
                fields[
                    "direction"
                ]
            )
        ),

        entry_name=(
            entry_name
        ),

        entry_price=(
            _parse_number(
                fields[
                    "entry"
                ]
            )
        ),

        stop_price=(
            _parse_number(
                fields[
                    "stop"
                ]
            )
        ),

        target_price=(
            _parse_number(
                fields[
                    "target"
                ]
            )
        ),
    )

    return TradingViewParityRecord(
        signal=signal,

        c3_timestamp=(
            _parse_epoch_ms(
                fields[
                    "c3time"
                ]
            )
        ),

        stop_points=(
            _parse_number(
                fields[
                    "stopPoints"
                ]
            )
        ),
    )


def load_tradingview_parity_logs(
    path: str | Path,
) -> list[
    TradingViewParityRecord
]:
    path = Path(
        path
    )

    records: list[
        TradingViewParityRecord
    ] = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line_number, line in enumerate(
            file,
            start=1,
        ):
            line = (
                line.strip()
            )

            if not line:
                continue

            try:
                record = (
                    parse_tradingview_parity_line(
                        line
                    )
                )

            except Exception as exc:
                raise ValueError(
                    "Invalid TradingView parity "
                    f"log line {line_number}: "
                    f"{exc}"
                ) from exc

            records.append(
                record
            )

    return records


def filter_tradingview_records(
    records: list[
        TradingViewParityRecord
    ],
    max_stop_points: float | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[
    TradingViewParityRecord
]:
    filtered = []

    for record in records:

        if (
            max_stop_points
            is not None
            and record.stop_points
            > max_stop_points
        ):
            continue

        timestamp = (
            record.signal.timestamp
        )

        if (
            start_time
            is not None
            and timestamp
            < start_time
        ):
            continue

        if (
            end_time
            is not None
            and timestamp
            > end_time
        ):
            continue

        filtered.append(
            record
        )

    return filtered


def records_to_signals(
    records: list[
        TradingViewParityRecord
    ],
) -> list[
    ParitySignal
]:
    return [
        record.signal
        for record in records
    ]