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
from mnq_fractal_bot.risk.risk_guard import (
    RiskGuard,
    RiskGuardConfig,
)
from mnq_fractal_bot.risk.trade_filter import (
    TradeFilterConfig,
    evaluate_trade_plan,
)
from mnq_fractal_bot.strategy.fractal_engine import (
    EngineSnapshot,
    FractalEngine,
)
from mnq_fractal_bot.strategy.trade_plan import TradePlan


@dataclass(frozen=True)
class RecordedBrokerEvent:
    timestamp: datetime
    event_type: str

    signal_id: str | None = None

    price: float | None = None
    gross_pnl: float | None = None


@dataclass(frozen=True)
class BotSnapshot:
    engine: EngineSnapshot

    events: tuple[
        BrokerEvent,
        ...
    ]

    order_submitted: bool

    pending_order: PendingOrder | None
    position: OpenPosition | None

    closed_trade_count: int

    audit_count: int
    broker_event_count: int


class BotRunner:
    def __init__(
        self,
        lower_timeframe: str = "5m",
        tick_size: float = 0.25,
        sl_buffer_ticks: int = 2,
        point_value: float = 2.0,
        max_hold_minutes: float | None = None,
        trade_filter_config: (
            TradeFilterConfig | None
        ) = None,
        risk_guard_config: (
            RiskGuardConfig | None
        ) = None,
        trading_enabled: bool = True,
    ):
        self.engine = FractalEngine(
            lower_timeframe=(
                lower_timeframe
            ),

            tick_size=(
                tick_size
            ),

            sl_buffer_ticks=(
                sl_buffer_ticks
            ),
        )

        self.broker = PaperBroker(
            point_value=(
                point_value
            ),
            max_hold_minutes=(
                max_hold_minutes
            ),
        )

        self.trade_filter_config = (
            trade_filter_config
            if trade_filter_config
            is not None
            else TradeFilterConfig()
        )

        self.risk_guard = (
            RiskGuard(config=risk_guard_config)
            if risk_guard_config is not None
            else None
        )

        # Normal backtests:
        # True
        #
        # Chronological validation warm-up:
        # False
        self.trading_enabled = (
            trading_enabled
        )

        self.signal_audits: list[
            SignalAudit
        ] = []

        self.audited_signal_ids: set[
            str
        ] = set()

        self.broker_event_history: list[
            RecordedBrokerEvent
        ] = []

        # Any signal that became ready during
        # warm-up belongs to the warm-up period.
        #
        # We remember it so it cannot suddenly
        # become a validation trade after the
        # trading gate is opened.
        self.suppressed_signal_ids: set[
            str
        ] = set()

    # ==================================================
    # TRADING GATE
    # ==================================================

    def set_trading_enabled(
        self,
        enabled: bool,
    ) -> None:
        """
        Enable or disable broker activity.

        IMPORTANT:

        The FractalEngine continues running
        regardless of this setting.

        Validation flow:

            trading_enabled=False

            feed warm-up candles

            set_trading_enabled(True)

            feed validation candles
        """

        self.trading_enabled = (
            enabled
        )

    # ==================================================
    # SIGNAL ID
    # ==================================================

    def _build_signal_id(
        self,
        setup: Setup,
        plan: TradePlan,
    ) -> str:
        direction = (
            "L"
            if setup.is_bullish
            else "S"
        )

        swept_htf = (
            str(
                setup.swept_htf_index
            )
            if (
                setup.swept_htf_index
                is not None
            )
            else "na"
        )

        sweep_bar = (
            str(
                setup.sweep_bar_index
            )
            if (
                setup.sweep_bar_index
                is not None
            )
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
        if (
            plan.entry_name
            == "C4 ENTRY ZONE"
        ):
            return (
                setup.c4_end_time
            )

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
                + timedelta(
                    hours=1
                )
            )

        if (
            self.engine.higher_timeframe
            == "4h"
        ):
            return (
                setup.c3_start_time
                + timedelta(
                    hours=4
                )
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

        if (
            not plan.bot_trade_ready
        ):
            return (
                setup,
                plan,
                None,
            )

        # ==================================================
        # EXECUTION FILTER
        # ==================================================

        decision = (
            evaluate_trade_plan(
                plan=plan,

                config=(
                    self.trade_filter_config
                ),
            )
        )

        if not decision.allowed:
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
        if (
            signal_id
            in self.audited_signal_ids
        ):
            return False

        audit = (
            build_signal_audit(
                setup=setup,
                plan=plan,
                signal_id=signal_id,
                created_at=created_at,
            )
        )

        self.signal_audits.append(
            audit
        )

        self.audited_signal_ids.add(
            signal_id
        )

        return True

    # ==================================================
    # BROKER EVENT HISTORY
    # ==================================================

    def _record_broker_event(
        self,
        event: BrokerEvent,
        timestamp: datetime,
    ) -> None:
        if (
            timestamp.tzinfo
            is None
        ):
            raise ValueError(
                "Broker event timestamp "
                "must include a timezone."
            )

        record = (
            RecordedBrokerEvent(
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
        )

        self.broker_event_history.append(
            record
        )

    # ==================================================
    # MAIN LOOP
    # ==================================================

    def on_candle(
        self,
        candle: Candle,
    ) -> BotSnapshot:
        events: list[
            BrokerEvent
        ] = []

        # ==================================================
        # 1. EXISTING ORDER / POSITION
        #
        # During warm-up:
        #
        # Broker does NOTHING.
        #
        # Engine still runs below.
        # ==================================================

        if self.trading_enabled:
            broker_event = (
                self.broker.on_candle(
                    candle
                )
            )

            if (
                broker_event
                is not None
            ):
                events.append(
                    broker_event
                )

                self._record_broker_event(
                    event=broker_event,

                    timestamp=(
                        candle.timestamp
                    ),
                )

                if (
                    self.risk_guard is not None
                    and broker_event.gross_pnl is not None
                ):
                    self.risk_guard.on_trade_closed(
                        pnl=broker_event.gross_pnl,
                        exit_time=candle.timestamp,
                    )

        # ==================================================
        # 2. FRACTAL MODEL
        #
        # ALWAYS RUNS.
        #
        # This is what allows the first 70%
        # to warm up the model.
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
        # 3. WARM-UP SIGNAL SUPPRESSION
        # ==================================================

        if (
            not self.trading_enabled
            and active_signal_id
            is not None
        ):
            self.suppressed_signal_ids.add(
                active_signal_id
            )

        # A signal that already became ready
        # during warm-up must NOT become a
        # validation trade.
        if (
            self.trading_enabled
            and active_signal_id
            in self.suppressed_signal_ids
        ):
            active_signal_id = None

        # ==================================================
        # 4. AUDIT ALLOWED SIGNALS
        #
        # No warm-up audits.
        # ==================================================

        if (
            self.trading_enabled
            and selected_setup
            is not None
            and trade_plan
            is not None
            and active_signal_id
            is not None
        ):
            self._record_signal_audit(
                setup=(
                    selected_setup
                ),

                plan=(
                    trade_plan
                ),

                signal_id=(
                    active_signal_id
                ),

                created_at=(
                    candle.timestamp
                ),
            )

        # ==================================================
        # 5. CANCEL STALE ORDER
        # ==================================================

        if (
            self.trading_enabled

            and self.broker.position
            is None

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

                if (
                    cancel_event
                    is not None
                ):
                    events.append(
                        cancel_event
                    )

                    self._record_broker_event(
                        event=(
                            cancel_event
                        ),

                        timestamp=(
                            candle.timestamp
                        ),
                    )

        # ==================================================
        # 6. SUBMIT PAPER ORDER
        # ==================================================

        order_submitted = False

        if (
            self.trading_enabled

            and selected_setup
            is not None

            and trade_plan
            is not None

            and active_signal_id
            is not None

            and self.broker.position
            is None

            and self.broker.pending_order
            is None
        ):
            expires_at = (
                self._get_order_expiry(
                    setup=(
                        selected_setup
                    ),

                    plan=(
                        trade_plan
                    ),
                )
            )

            # ==============================================
            # RISK GUARD LOCK (PROP-FIRM / DRAWDOWN SHIELD)
            # ==============================================
            risk_ok = True
            if self.risk_guard is not None:
                risk_check = self.risk_guard.check_new_order(candle.timestamp)
                if not risk_check.allowed:
                    risk_ok = False

            if risk_ok and (
                expires_at is None
                or (
                    candle.timestamp
                    < expires_at
                )
            ):
                order_submitted = (
                    self.broker
                    .submit_trade_plan(
                        plan=(
                            trade_plan
                        ),

                        signal_id=(
                            active_signal_id
                        ),

                        expires_at=(
                            expires_at
                        ),
                    )
                )

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
                                trade_plan
                                .entry_price
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
        # 7. SNAPSHOT
        # ==================================================

        return BotSnapshot(
            engine=(
                engine_snapshot
            ),

            events=tuple(
                events
            ),

            order_submitted=(
                order_submitted
            ),

            pending_order=(
                self.broker
                .pending_order
            ),

            position=(
                self.broker
                .position
            ),

            closed_trade_count=len(
                self.broker
                .closed_trades
            ),

            audit_count=len(
                self.signal_audits
            ),

            broker_event_count=len(
                self.broker_event_history
            ),
        )