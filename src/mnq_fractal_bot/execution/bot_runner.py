from dataclasses import dataclass
from datetime import datetime, timedelta

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
        opportunities for duplicate protection.
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
        """
        C4:
            use its known C4 end time.

        C3:
            use known C3 end when available.

            During a live C3, C3 end may not yet
            be stored, so calculate it from the
            C3 start + current HTF duration.
        """

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
    # MAIN BOT LOOP
    # ==================================================

    def on_candle(
        self,
        candle: Candle,
    ) -> BotSnapshot:
        events: list[BrokerEvent] = []

        # ==================================================
        # 1. PROCESS ORDERS THAT ALREADY EXISTED
        #    BEFORE THIS CANDLE
        #
        # This is deliberately BEFORE the engine.
        #
        # Why?
        #
        # A setup discovered from THIS candle's close
        # must not fill earlier inside THIS SAME candle.
        #
        # That would introduce look-ahead bias.
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

        # ==================================================
        # 2. PROCESS THIS CANDLE THROUGH FRACTAL MODEL
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
        # 3. CANCEL A STALE PENDING ORDER
        #
        # Existing position is NOT cancelled.
        #
        # Once entered, V1 manages it using its
        # original SL / TP.
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
        # 4. SUBMIT NEW PAPER ORDER
        #
        # This happens AFTER processing the candle.
        #
        # Therefore the new order becomes eligible
        # for filling from the NEXT candle onward.
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

            # Do not submit an order whose
            # entry window has already ended.
            if (
                expires_at is None
                or candle.timestamp < expires_at
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

        # ==================================================
        # 5. SNAPSHOT
        # ==================================================

        return BotSnapshot(
            engine=engine_snapshot,
            events=tuple(events),
            order_submitted=order_submitted,
            pending_order=(
                self.broker.pending_order
            ),
            position=(
                self.broker.position
            ),
            closed_trade_count=len(
                self.broker.closed_trades
            ),
        )