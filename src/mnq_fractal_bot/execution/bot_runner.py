from dataclasses import dataclass
from datetime import datetime, timedelta

from mnq_fractal_bot.backtest.audit import (
    SignalAudit,
    build_signal_audit,
)

from mnq_fractal_bot.execution.paper_broker import (
    BrokerEvent,
    OpenPosition,
    PaperBroker,
    PendingOrder,
)

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.models.setup import Setup

from mnq_fractal_bot.strategy.fractal_engine import (
    EngineSnapshot,
    FractalEngine,
)

from mnq_fractal_bot.strategy.trade_plan import (
    TradePlan,
)


# ======================================================
# PERMANENT BROKER EVENT RECORD
# ======================================================

@dataclass(frozen=True)
class RecordedBrokerEvent:
    timestamp: datetime

    event_type: str

    signal_id: str | None = None

    price: float | None = None
    gross_pnl: float | None = None


# ======================================================
# BOT SNAPSHOT
# ======================================================

@dataclass(frozen=True)
class BotSnapshot:
    engine: EngineSnapshot

    # Events produced on THIS candle only.
    events: tuple[BrokerEvent, ...]

    order_submitted: bool

    pending_order: PendingOrder | None
    position: OpenPosition | None

    closed_trade_count: int

    # Total unique Fractal signals audited.
    audit_count: int

    # Total broker events recorded
    # across the whole run.
    broker_event_count: int


class BotRunner:
    """
    Complete local PAPER trading pipeline:

        Candle
          ↓
        FractalEngine
          ↓
        TradePlan
          ↓
        PaperBroker
          ↓
        Audit + Broker Event History

    No Tradovate connection.
    No live orders.
    """

    def __init__(
        self,
        lower_timeframe: str = "5m",
        tick_size: float = 0.25,
        sl_buffer_ticks: int = 2,
        point_value: float = 2.0,
    ):
        # ==================================================
        # FRACTAL ENGINE
        # ==================================================

        self.engine = FractalEngine(
            lower_timeframe=lower_timeframe,
            tick_size=tick_size,
            sl_buffer_ticks=sl_buffer_ticks,
        )

        # ==================================================
        # PAPER BROKER
        # ==================================================

        self.broker = PaperBroker(
            point_value=point_value,
        )

        # ==================================================
        # SIGNAL AUDIT HISTORY
        # ==================================================

        self.signal_audits: list[
            SignalAudit
        ] = []

        self.audited_signal_ids: set[
            str
        ] = set()

        # ==================================================
        # BROKER EVENT HISTORY
        #
        # This permanently records:
        #
        # ORDER_SUBMITTED
        # ENTRY_FILLED
        # ORDER_CANCELLED
        # ORDER_EXPIRED
        # POSITION_TARGET
        # POSITION_STOPPED
        # ==================================================

        self.broker_event_history: list[
            RecordedBrokerEvent
        ] = []

    # ==================================================
    # SIGNAL ID
    # ==================================================

    def _build_signal_id(
        self,
        setup: Setup,
        plan: TradePlan,
    ) -> str:
        """
        Stable identifier for one Fractal entry idea.

        A C3 entry and C4 entry are treated as
        different opportunities.
        """

        direction = (
            "L"
            if setup.is_bullish
            else "S"
        )

        swept_htf = (
            str(
                setup.swept_htf_index
            )
            if setup.swept_htf_index
            is not None
            else "na"
        )

        sweep_bar = (
            str(
                setup.sweep_bar_index
            )
            if setup.sweep_bar_index
            is not None
            else "na"
        )

        if (
            plan.entry_name
            == "C4 ENTRY ZONE"
        ):
            zone = "C4"

            zone_time = (
                setup.c4_start_time
            )

        else:
            zone = "C3"

            zone_time = (
                setup.c3_start_time
            )

        time_text = (
            zone_time.isoformat()
            if zone_time is not None
            else "na"
        )

        return (
            f"{direction}:"
            f"{swept_htf}:"
            f"{sweep_bar}:"
            f"{zone}:"
            f"{time_text}"
        )

    # ==================================================
    # ORDER EXPIRY
    # ==================================================

    def _get_order_expiry(
        self,
        setup: Setup,
        plan: TradePlan,
    ) -> datetime | None:
        # --------------------------------------------------
        # C4
        # --------------------------------------------------

        if (
            plan.entry_name
            == "C4 ENTRY ZONE"
        ):
            return (
                setup.c4_end_time
            )

        # --------------------------------------------------
        # C3
        # --------------------------------------------------

        if (
            plan.entry_name
            != "C3 ENTRY ZONE"
        ):
            return None

        if (
            setup.c3_end_time
            is not None
        ):
            return (
                setup.c3_end_time
            )

        if (
            setup.c3_start_time
            is None
        ):
            return None

        if (
            self.engine.higher_timeframe
            == "1h"
        ):
            return (
                setup.c3_start_time
                + timedelta(hours=1)
            )

        if (
            self.engine.higher_timeframe
            == "4h"
        ):
            return (
                setup.c3_start_time
                + timedelta(hours=4)
            )

        return None

    # ==================================================
    # CURRENT SIGNAL
    # ==================================================

    def _get_active_signal(
        self,
        snapshot: EngineSnapshot,
    ) -> tuple[
        Setup | None,
        TradePlan | None,
        str | None,
    ]:
        setup = (
            snapshot.selected_setup
        )

        plan = (
            snapshot.trade_plan
        )

        if setup is None:
            return (
                None,
                None,
                None,
            )

        if plan is None:
            return (
                setup,
                None,
                None,
            )

        # Model may be READY visually,
        # but bot automation requires
        # a valid target as well.
        if not plan.bot_trade_ready:
            return (
                setup,
                plan,
                None,
            )

        signal_id = (
            self._build_signal_id(
                setup=setup,
                plan=plan,
            )
        )

        return (
            setup,
            plan,
            signal_id,
        )

    # ==================================================
    # SIGNAL AUDIT
    # ==================================================

    def _record_signal_audit(
        self,
        setup: Setup,
        plan: TradePlan,
        signal_id: str,
        created_at: datetime,
    ) -> bool:
        """
        Store each unique BOT TRADE READY
        Fractal signal exactly once.
        """

        if (
            signal_id
            in self.audited_signal_ids
        ):
            return False

        audit = build_signal_audit(
            setup=setup,
            plan=plan,
            signal_id=signal_id,
            created_at=created_at,
        )

        self.signal_audits.append(
            audit
        )

        self.audited_signal_ids.add(
            signal_id
        )

        return True

    # ==================================================
    # BROKER EVENT AUDIT
    # ==================================================

    def _record_broker_event(
        self,
        event: BrokerEvent,
        timestamp: datetime,
    ) -> None:
        """
        Convert an in-memory BrokerEvent into
        a permanent historical record.
        """

        if timestamp.tzinfo is None:
            raise ValueError(
                "Broker event timestamp "
                "must include a timezone."
            )

        record = RecordedBrokerEvent(
            timestamp=timestamp,

            event_type=(
                event.event_type
            ),

            signal_id=(
                event.signal_id
            ),

            price=(
                event.price
            ),

            gross_pnl=(
                event.gross_pnl
            ),
        )

        self.broker_event_history.append(
            record
        )

    # ==================================================
    # MAIN BOT LOOP
    # ==================================================

    def on_candle(
        self,
        candle: Candle,
    ) -> BotSnapshot:
        # Events generated on this candle.
        events: list[
            BrokerEvent
        ] = []

        # ==================================================
        # 1. PROCESS EXISTING ORDER / POSITION
        #
        # IMPORTANT:
        #
        # This happens BEFORE processing the candle
        # through the strategy.
        #
        # Therefore a signal discovered from THIS
        # candle cannot magically fill earlier
        # inside the same candle.
        # ==================================================

        broker_event = (
            self.broker.on_candle(
                candle
            )
        )

        if broker_event is not None:
            events.append(
                broker_event
            )

            self._record_broker_event(
                event=broker_event,
                timestamp=candle.timestamp,
            )

        # ==================================================
        # 2. PROCESS FRACTAL MODEL
        # ==================================================

        engine_snapshot = (
            self.engine.on_candle(
                candle
            )
        )

        (
            selected_setup,
            trade_plan,
            active_signal_id,
        ) = self._get_active_signal(
            engine_snapshot
        )

        # ==================================================
        # 3. RECORD UNIQUE FRACTAL SIGNAL
        # ==================================================

        if (
            selected_setup is not None
            and trade_plan is not None
            and active_signal_id
            is not None
        ):
            self._record_signal_audit(
                setup=selected_setup,
                plan=trade_plan,
                signal_id=(
                    active_signal_id
                ),
                created_at=(
                    candle.timestamp
                ),
            )

        # ==================================================
        # 4. CANCEL STALE PENDING ORDER
        # ==================================================

        if (
            self.broker.position is None
            and self.broker.pending_order
            is not None
        ):
            existing_signal_id = (
                self.broker
                .pending_order
                .signal_id
            )

            if (
                active_signal_id
                != existing_signal_id
            ):
                cancel_event = (
                    self.broker
                    .cancel_pending_order()
                )

                if cancel_event is not None:
                    events.append(
                        cancel_event
                    )

                    self._record_broker_event(
                        event=cancel_event,
                        timestamp=(
                            candle.timestamp
                        ),
                    )

        # ==================================================
        # 5. SUBMIT NEW PAPER ORDER
        # ==================================================

        order_submitted = False

        if (
            selected_setup is not None
            and trade_plan is not None
            and active_signal_id
            is not None
            and self.broker.position is None
            and self.broker.pending_order
            is None
        ):
            expires_at = (
                self._get_order_expiry(
                    setup=selected_setup,
                    plan=trade_plan,
                )
            )

            # Do not submit an already-expired
            # setup window.
            if (
                expires_at is None
                or candle.timestamp
                < expires_at
            ):
                order_submitted = (
                    self.broker
                    .submit_trade_plan(
                        plan=trade_plan,
                        signal_id=(
                            active_signal_id
                        ),
                        expires_at=(
                            expires_at
                        ),
                    )
                )

                # PaperBroker returns True rather
                # than a BrokerEvent when submission
                # succeeds, so create one here.
                if order_submitted:
                    submitted_event = (
                        BrokerEvent(
                            event_type=(
                                "ORDER_SUBMITTED"
                            ),
                            signal_id=(
                                active_signal_id
                            ),
                            price=(
                                trade_plan.entry_price
                            ),
                        )
                    )

                    events.append(
                        submitted_event
                    )

                    self._record_broker_event(
                        event=(
                            submitted_event
                        ),
                        timestamp=(
                            candle.timestamp
                        ),
                    )

        # ==================================================
        # 6. SNAPSHOT
        # ==================================================

        return BotSnapshot(
            engine=engine_snapshot,

            events=tuple(
                events
            ),

            order_submitted=(
                order_submitted
            ),

            pending_order=(
                self.broker.pending_order
            ),

            position=(
                self.broker.position
            ),

            closed_trade_count=len(
                self.broker.closed_trades
            ),

            audit_count=len(
                self.signal_audits
            ),

            broker_event_count=len(
                self.broker_event_history
            ),
        )