from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from mnq_fractal_bot.backtest.audit import (
    SignalAudit,
)

from mnq_fractal_bot.execution.bot_runner import (
    RecordedBrokerEvent,
)


@dataclass(frozen=True)
class SignalOutcome:
    # ==================================================
    # SIGNAL
    # ==================================================

    signal_id: str
    created_at: datetime

    direction: str

    sweep_price: float | None
    cisd_level: float | None
    c2_extreme: float | None

    entry_name: str | None

    entry_price: float | None
    stop_price: float | None

    tp_c1: float | None
    tp_c0: float | None

    target_price: float | None

    # ==================================================
    # ORDER
    # ==================================================

    order_submitted: bool
    order_submitted_at: datetime | None

    # ==================================================
    # FILL
    # ==================================================

    entry_filled: bool
    entry_time: datetime | None

    # ==================================================
    # FINAL RESULT
    #
    # Possible values:
    #
    # TARGET
    # STOPPED
    # EXPIRED
    # CANCELLED
    # OPEN_POSITION
    # PENDING_ORDER
    # NOT_SUBMITTED
    # ==================================================

    final_status: str

    exit_time: datetime | None
    exit_price: float | None

    gross_pnl: float | None


FINAL_EVENT_TYPES = {
    "POSITION_TARGET",
    "POSITION_STOPPED",
    "ORDER_EXPIRED",
    "ORDER_CANCELLED",
}


def build_signal_outcomes(
    audits: Sequence[SignalAudit],
    broker_events: Sequence[RecordedBrokerEvent],
) -> tuple[SignalOutcome, ...]:
    # ==================================================
    # GROUP BROKER EVENTS BY SIGNAL ID
    # ==================================================

    events_by_signal: dict[
        str,
        list[RecordedBrokerEvent],
    ] = defaultdict(list)

    for event in broker_events:
        if event.signal_id is None:
            continue

        events_by_signal[
            event.signal_id
        ].append(
            event
        )

    # Keep event history chronological.
    for events in events_by_signal.values():
        events.sort(
            key=lambda event: event.timestamp
        )

    outcomes: list[
        SignalOutcome
    ] = []

    # ==================================================
    # BUILD ONE OUTCOME PER AUDITED SIGNAL
    # ==================================================

    for audit in audits:
        events = events_by_signal.get(
            audit.signal_id,
            [],
        )

        submitted_event = next(
            (
                event
                for event in events
                if (
                    event.event_type
                    == "ORDER_SUBMITTED"
                )
            ),
            None,
        )

        entry_event = next(
            (
                event
                for event in events
                if (
                    event.event_type
                    == "ENTRY_FILLED"
                )
            ),
            None,
        )

        final_event = None

        for event in events:
            if (
                event.event_type
                in FINAL_EVENT_TYPES
            ):
                final_event = event

        # ==================================================
        # FINAL STATUS
        # ==================================================

        if final_event is not None:
            if (
                final_event.event_type
                == "POSITION_TARGET"
            ):
                final_status = (
                    "TARGET"
                )

            elif (
                final_event.event_type
                == "POSITION_STOPPED"
            ):
                final_status = (
                    "STOPPED"
                )

            elif (
                final_event.event_type
                == "ORDER_EXPIRED"
            ):
                final_status = (
                    "EXPIRED"
                )

            else:
                final_status = (
                    "CANCELLED"
                )

        elif entry_event is not None:
            # Dataset ended while trade
            # was still open.
            final_status = (
                "OPEN_POSITION"
            )

        elif submitted_event is not None:
            # Dataset ended while limit order
            # was still waiting.
            final_status = (
                "PENDING_ORDER"
            )

        else:
            # Valid Fractal signal existed,
            # but another order/position may have
            # prevented this one from being submitted.
            final_status = (
                "NOT_SUBMITTED"
            )

        # ==================================================
        # EXIT DATA
        # ==================================================

        exit_time = None
        exit_price = None
        gross_pnl = None

        if final_event is not None:
            exit_time = (
                final_event.timestamp
            )

            exit_price = (
                final_event.price
            )

            gross_pnl = (
                final_event.gross_pnl
            )

        outcomes.append(
            SignalOutcome(
                signal_id=(
                    audit.signal_id
                ),

                created_at=(
                    audit.created_at
                ),

                direction=(
                    audit.direction
                ),

                sweep_price=(
                    audit.sweep_price
                ),

                cisd_level=(
                    audit.cisd_level
                ),

                c2_extreme=(
                    audit.c2_extreme
                ),

                entry_name=(
                    audit.entry_name
                ),

                entry_price=(
                    audit.entry_price
                ),

                stop_price=(
                    audit.stop_price
                ),

                tp_c1=(
                    audit.tp_c1
                ),

                tp_c0=(
                    audit.tp_c0
                ),

                target_price=(
                    audit.preferred_target
                ),

                order_submitted=(
                    submitted_event
                    is not None
                ),

                order_submitted_at=(
                    submitted_event.timestamp
                    if submitted_event
                    is not None
                    else None
                ),

                entry_filled=(
                    entry_event
                    is not None
                ),

                entry_time=(
                    entry_event.timestamp
                    if entry_event
                    is not None
                    else None
                ),

                final_status=(
                    final_status
                ),

                exit_time=(
                    exit_time
                ),

                exit_price=(
                    exit_price
                ),

                gross_pnl=(
                    gross_pnl
                ),
            )
        )

    return tuple(
        outcomes
    )