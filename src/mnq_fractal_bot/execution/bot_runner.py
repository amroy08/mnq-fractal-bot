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


@dataclass(frozen=True)
class BotSnapshot:
    engine: EngineSnapshot

    events: tuple[BrokerEvent, ...]

    order_submitted: bool

    pending_order: PendingOrder | None
    position: OpenPosition | None

    closed_trade_count: int

    # Number of unique Fractal trade-ready
    # signals recorded so far.
    audit_count: int


class BotRunner:
    """
    Connect:

        Market candle
            ↓
        FractalEngine
            ↓
        TradePlan
            ↓
        PaperBroker

    PAPER ONLY.

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
        self.engine = FractalEngine(
            lower_timeframe=lower_timeframe,
            tick_size=tick_size,
            sl_buffer_ticks=sl_buffer_ticks,
        )

        self.broker = PaperBroker(
            point_value=point_value,
        )

        # ==================================================
        # SIGNAL AUDIT HISTORY
        # ==================================================

        self.signal_audits: list[
            SignalAudit
        ] = []

        # Prevent the same signal from being
        # written to the audit log on every candle.
        self.audited_signal_ids: set[
            str
        ] = set()

    # ==================================================
    # SIGNAL ID
    # ==================================================

    def _build_signal_id(
        self,
        setup: Setup,
        plan: TradePlan,
    ) -> str:
        """
        Create a stable ID for one Fractal entry idea.

        C3 and C4 are considered different entry
        opportunities.
        """

        direction = (
            "L"
            if setup.is_bullish
            else "S"
        )

        swept_htf = (
            str(setup.swept_htf_index)
            if setup.swept_htf_index is not None
            else "na"
        )

        sweep_bar = (
            str(setup.sweep_bar_index)
            if setup.sweep_bar_index is not None
            else "na"
        )

        if plan.entry_name == "C4 ENTRY ZONE":
            zone = "C4"
            zone_time = setup.c4_start_time

        else:
            zone = "C3"
            zone_time = setup.c3_start_time

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
        if plan.entry_name == "C4 ENTRY ZONE":
            return setup.c4_end_time

        if plan.entry_name != "C3 ENTRY ZONE":
            return None

        if setup.c3_end_time is not None:
            return setup.c3_end_time

        if setup.c3_start_time is None:
            return None

        if self.engine.higher_timeframe == "1h":
            return (
                setup.c3_start_time
                + timedelta(hours=1)
            )

        if self.engine.higher_timeframe == "4h":
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
        setup = snapshot.selected_setup
        plan = snapshot.trade_plan

        if setup is None:
            return None, None, None

        if plan is None:
            return setup, None, None

        if not plan.bot_trade_ready:
            return setup, plan, None

        signal_id = self._build_signal_id(
            setup=setup,
            plan=plan,
        )

        return (
            setup,
            plan,
            signal_id,
        )

    # ==================================================
    # AUDIT
    # ==================================================

    def _record_signal_audit(
        self,
        setup: Setup,
        plan: TradePlan,
        signal_id: str,
        created_at: datetime,
    ) -> bool:
        """
        Record each unique BOT TRADE READY
        signal exactly once.

        Returns True if a new audit was added.
        """

        if signal_id in self.audited_signal_ids:
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
    # MAIN BOT LOOP
    # ==================================================

    def on_candle(
        self,
        candle: Candle,
    ) -> BotSnapshot:
        events: list[BrokerEvent] = []

        # ==================================================
        # 1. PROCESS EXISTING PAPER ORDER / POSITION
        # ==================================================

        broker_event = self.broker.on_candle(
            candle
        )

        if broker_event is not None:
            events.append(
                broker_event
            )

        # ==================================================
        # 2. PROCESS CANDLE THROUGH FRACTAL MODEL
        # ==================================================

        engine_snapshot = self.engine.on_candle(
            candle
        )

        (
            selected_setup,
            trade_plan,
            active_signal_id,
        ) = self._get_active_signal(
            engine_snapshot
        )

        # ==================================================
        # 3. RECORD UNIQUE TRADE-READY SIGNAL
        # ==================================================

        if (
            selected_setup is not None
            and trade_plan is not None
            and active_signal_id is not None
        ):
            self._record_signal_audit(
                setup=selected_setup,
                plan=trade_plan,
                signal_id=active_signal_id,
                created_at=candle.timestamp,
            )

        # ==================================================
        # 4. CANCEL STALE PENDING ORDER
        # ==================================================

        if (
            self.broker.position is None
            and self.broker.pending_order is not None
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

        # ==================================================
        # 5. SUBMIT NEW PAPER ORDER
        # ==================================================

        order_submitted = False

        if (
            selected_setup is not None
            and trade_plan is not None
            and active_signal_id is not None
            and self.broker.position is None
            and self.broker.pending_order is None
        ):
            expires_at = (
                self._get_order_expiry(
                    setup=selected_setup,
                    plan=trade_plan,
                )
            )

            if (
                expires_at is None
                or candle.timestamp < expires_at
            ):
                order_submitted = (
                    self.broker
                    .submit_trade_plan(
                        plan=trade_plan,
                        signal_id=active_signal_id,
                        expires_at=expires_at,
                    )
                )

        # ==================================================
        # 6. RETURN SNAPSHOT
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
        )