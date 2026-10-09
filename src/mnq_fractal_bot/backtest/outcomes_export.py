import csv
from collections.abc import Sequence
from pathlib import Path

from mnq_fractal_bot.backtest.outcomes import (
    SignalOutcome,
)


DEFAULT_OUTCOMES_PATH = Path(
    "data/fractal_signal_outcomes.csv"
)


def export_signal_outcomes(
    outcomes: Sequence[SignalOutcome],
    output_path: str | Path = DEFAULT_OUTCOMES_PATH,
) -> Path:
    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "signal_id",
        "created_at",
        "direction",

        "sweep_price",
        "cisd_level",
        "c2_extreme",

        "entry_name",
        "entry_price",
        "stop_price",

        "tp_c1",
        "tp_c0",
        "target_price",

        "order_submitted",
        "order_submitted_at",

        "entry_filled",
        "entry_time",

        "final_status",

        "exit_time",
        "exit_price",

        "gross_pnl",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for outcome in outcomes:
            writer.writerow(
                {
                    "signal_id": (
                        outcome.signal_id
                    ),

                    "created_at": (
                        outcome.created_at.isoformat()
                    ),

                    "direction": (
                        outcome.direction
                    ),

                    "sweep_price": (
                        outcome.sweep_price
                    ),

                    "cisd_level": (
                        outcome.cisd_level
                    ),

                    "c2_extreme": (
                        outcome.c2_extreme
                    ),

                    "entry_name": (
                        outcome.entry_name
                    ),

                    "entry_price": (
                        outcome.entry_price
                    ),

                    "stop_price": (
                        outcome.stop_price
                    ),

                    "tp_c1": (
                        outcome.tp_c1
                    ),

                    "tp_c0": (
                        outcome.tp_c0
                    ),

                    "target_price": (
                        outcome.target_price
                    ),

                    "order_submitted": (
                        outcome.order_submitted
                    ),

                    "order_submitted_at": (
                        outcome
                        .order_submitted_at
                        .isoformat()
                        if (
                            outcome.order_submitted_at
                            is not None
                        )
                        else None
                    ),

                    "entry_filled": (
                        outcome.entry_filled
                    ),

                    "entry_time": (
                        outcome.entry_time.isoformat()
                        if outcome.entry_time
                        is not None
                        else None
                    ),

                    "final_status": (
                        outcome.final_status
                    ),

                    "exit_time": (
                        outcome.exit_time.isoformat()
                        if outcome.exit_time
                        is not None
                        else None
                    ),

                    "exit_price": (
                        outcome.exit_price
                    ),

                    "gross_pnl": (
                        outcome.gross_pnl
                    ),
                }
            )

    return output_path