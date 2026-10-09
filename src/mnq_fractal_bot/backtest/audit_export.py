import csv
from collections.abc import Sequence
from pathlib import Path

from mnq_fractal_bot.backtest.audit import (
    SignalAudit,
)


DEFAULT_AUDIT_PATH = Path(
    "data/fractal_signal_audit.csv"
)


def export_signal_audits(
    audits: Sequence[SignalAudit],
    output_path: str | Path = DEFAULT_AUDIT_PATH,
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

        "c3_zone_set",
        "c3_zone_bottom",
        "c3_zone_top",
        "c3_start_time",

        "c4_zone_set",
        "c4_invalid",
        "c4_zone_bottom",
        "c4_zone_top",
        "c4_start_time",

        "entry_name",
        "entry_price",
        "stop_price",

        "tp_c1",
        "tp_c0",
        "preferred_target",

        "model_ready",
        "bot_trade_ready",
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

        for audit in audits:
            writer.writerow(
                {
                    "signal_id": (
                        audit.signal_id
                    ),

                    "created_at": (
                        audit.created_at.isoformat()
                    ),

                    "direction": (
                        audit.direction
                    ),

                    "sweep_price": (
                        audit.sweep_price
                    ),

                    "cisd_level": (
                        audit.cisd_level
                    ),

                    "c2_extreme": (
                        audit.c2_extreme
                    ),

                    "c3_zone_set": (
                        audit.c3_zone_set
                    ),

                    "c3_zone_bottom": (
                        audit.c3_zone_bottom
                    ),

                    "c3_zone_top": (
                        audit.c3_zone_top
                    ),

                    "c3_start_time": (
                        audit.c3_start_time.isoformat()
                        if audit.c3_start_time
                        is not None
                        else None
                    ),

                    "c4_zone_set": (
                        audit.c4_zone_set
                    ),

                    "c4_invalid": (
                        audit.c4_invalid
                    ),

                    "c4_zone_bottom": (
                        audit.c4_zone_bottom
                    ),

                    "c4_zone_top": (
                        audit.c4_zone_top
                    ),

                    "c4_start_time": (
                        audit.c4_start_time.isoformat()
                        if audit.c4_start_time
                        is not None
                        else None
                    ),

                    "entry_name": (
                        audit.entry_name
                    ),

                    "entry_price": (
                        audit.entry_price
                    ),

                    "stop_price": (
                        audit.stop_price
                    ),

                    "tp_c1": (
                        audit.tp_c1
                    ),

                    "tp_c0": (
                        audit.tp_c0
                    ),

                    "preferred_target": (
                        audit.preferred_target
                    ),

                    "model_ready": (
                        audit.model_ready
                    ),

                    "bot_trade_ready": (
                        audit.bot_trade_ready
                    ),
                }
            )

    return output_path