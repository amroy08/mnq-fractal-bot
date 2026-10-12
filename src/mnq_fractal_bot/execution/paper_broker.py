from dataclasses import dataclass
from datetime import datetime

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.strategy.trade_plan import TradePlan


MNQ_POINT_VALUE = 2.0


@dataclass(frozen=True)
class PendingOrder:
    signal_id: str

    direction: str

    entry_price: float
    stop_price: float
    target_price: float

    quantity: int = 1

    expires_at: datetime | None = None


@dataclass(frozen=True)
class OpenPosition:
    signal_id: str

    direction: str

    entry_price: float
    stop_price: float
    target_price: float

    quantity: int

    entry_time: datetime


@dataclass(frozen=True)
class ClosedTrade:
    signal_id: str

    direction: str

    entry_price: float
    exit_price: float

    stop_price: float
    target_price: float

    quantity: int

    entry_time: datetime
    exit_time: datetime

    exit_reason: str

    points: float
    gross_pnl: float


@dataclass(frozen=True)
class BrokerEvent:
    event_type: str

    signal_id: str | None = None

    price: float | None = None

    gross_pnl: float | None = None


class PaperBroker:
    def __init__(
        self,
        point_value: float = MNQ_POINT_VALUE,
        max_hold_minutes: float | None = None,
    ):
        if point_value <= 0:
            raise ValueError(
                "Point value must be greater than zero."
            )

        self.point_value = point_value
        self.max_hold_minutes = max_hold_minutes

        # V1 = exactly one MNQ.
        self.quantity = 1

        self.pending_order: PendingOrder | None = None

        self.position: OpenPosition | None = None

        self.closed_trades: list[ClosedTrade] = []

        # Prevent the exact same Fractal signal
        # from being submitted repeatedly.
        self.seen_signal_ids: set[str] = set()

    # ==================================================
    # SUBMIT TRADE PLAN
    # ==================================================

    def submit_trade_plan(
        self,
        plan: TradePlan,
        signal_id: str,
        expires_at: datetime | None = None,
    ) -> bool:
        """
        Convert a BOT TRADE READY TradePlan
        into a pending paper order.

        Returns True when accepted.
        """

        if not signal_id:
            raise ValueError(
                "Signal ID cannot be empty."
            )

        # Do not trade merely because MODEL READY.
        #
        # Paper automation requires:
        #
        # Entry
        # Stop
        # Valid TP
        if not plan.bot_trade_ready:
            return False

        if signal_id in self.seen_signal_ids:
            return False

        # V1 = one trade/order at a time.
        if self.pending_order is not None:
            return False

        if self.position is not None:
            return False

        if plan.entry_price is None:
            return False

        if plan.stop_price is None:
            return False

        if plan.preferred_target is None:
            return False

        direction = plan.direction

        if direction not in {
            "LONG",
            "SHORT",
        }:
            raise ValueError(
                f"Unsupported direction: {direction}"
            )

        entry = plan.entry_price
        stop = plan.stop_price
        target = plan.preferred_target

        # --------------------------------------------------
        # SAFETY CHECKS
        # --------------------------------------------------

        if direction == "LONG":
            if stop >= entry:
                raise ValueError(
                    "LONG stop must be below entry."
                )

            if target <= entry:
                raise ValueError(
                    "LONG target must be above entry."
                )

        else:
            if stop <= entry:
                raise ValueError(
                    "SHORT stop must be above entry."
                )

            if target >= entry:
                raise ValueError(
                    "SHORT target must be below entry."
                )

        self.pending_order = PendingOrder(
            signal_id=signal_id,
            direction=direction,
            entry_price=entry,
            stop_price=stop,
            target_price=target,
            quantity=self.quantity,
            expires_at=expires_at,
        )

        self.seen_signal_ids.add(
            signal_id
        )

        return True

    # ==================================================
    # CANCEL
    # ==================================================

    def cancel_pending_order(
        self,
    ) -> BrokerEvent | None:
        if self.pending_order is None:
            return None

        signal_id = (
            self.pending_order.signal_id
        )

        self.pending_order = None

        return BrokerEvent(
            event_type="ORDER_CANCELLED",
            signal_id=signal_id,
        )

    # ==================================================
    # ENTRY
    # ==================================================

    def _try_fill_entry(
        self,
        candle: Candle,
    ) -> BrokerEvent | None:
        if self.pending_order is None:
            return None

        order = self.pending_order

        # --------------------------------------------------
        # EXPIRE BEFORE TRYING TO FILL
        # --------------------------------------------------

        if (
            order.expires_at is not None
            and candle.timestamp >= order.expires_at
        ):
            self.pending_order = None

            return BrokerEvent(
                event_type="ORDER_EXPIRED",
                signal_id=order.signal_id,
            )

        # A limit-style paper entry is considered
        # touched when entry is inside the candle range.
        entry_touched = (
            candle.low
            <= order.entry_price
            <= candle.high
        )

        if not entry_touched:
            return None

        self.position = OpenPosition(
            signal_id=order.signal_id,
            direction=order.direction,
            entry_price=order.entry_price,
            stop_price=order.stop_price,
            target_price=order.target_price,
            quantity=order.quantity,
            entry_time=candle.timestamp,
        )

        self.pending_order = None

        return BrokerEvent(
            event_type="ENTRY_FILLED",
            signal_id=order.signal_id,
            price=order.entry_price,
        )

    # ==================================================
    # EXIT
    # ==================================================

    def _close_position(
        self,
        candle: Candle,
        exit_price: float,
        exit_reason: str,
    ) -> BrokerEvent:
        if self.position is None:
            raise RuntimeError(
                "Cannot close position: no open position."
            )

        position = self.position

        if position.direction == "LONG":
            points = (
                exit_price
                - position.entry_price
            )

        else:
            points = (
                position.entry_price
                - exit_price
            )

        gross_pnl = (
            points
            * self.point_value
            * position.quantity
        )

        trade = ClosedTrade(
            signal_id=position.signal_id,
            direction=position.direction,
            entry_price=position.entry_price,
            exit_price=exit_price,
            stop_price=position.stop_price,
            target_price=position.target_price,
            quantity=position.quantity,
            entry_time=position.entry_time,
            exit_time=candle.timestamp,
            exit_reason=exit_reason,
            points=points,
            gross_pnl=gross_pnl,
        )

        self.closed_trades.append(
            trade
        )

        self.position = None

        return BrokerEvent(
            event_type=f"POSITION_{exit_reason}",
            signal_id=trade.signal_id,
            price=exit_price,
            gross_pnl=gross_pnl,
        )

    def _check_position_exit(
        self,
        candle: Candle,
    ) -> BrokerEvent | None:
        if self.position is None:
            return None

        position = self.position

        # ==================================================
        # LONG
        # ==================================================

        if position.direction == "LONG":
            stop_hit = (
                candle.low
                <= position.stop_price
            )

            target_hit = (
                candle.high
                >= position.target_price
            )

        # ==================================================
        # SHORT
        # ==================================================

        else:
            stop_hit = (
                candle.high
                >= position.stop_price
            )

            target_hit = (
                candle.low
                <= position.target_price
            )

        # --------------------------------------------------
        # OHLC AMBIGUITY
        #
        # If BOTH SL and TP exist inside the same
        # historical candle, OHLC bars cannot tell us
        # which price was touched first.
        #
        # Use the conservative assumption:
        #
        # STOP wins.
        # --------------------------------------------------

        if stop_hit:
            return self._close_position(
                candle=candle,
                exit_price=position.stop_price,
                exit_reason="STOPPED",
            )

        if target_hit:
            return self._close_position(
                candle=candle,
                exit_price=position.target_price,
                exit_reason="TARGET",
            )

        # --------------------------------------------------
        # TIME-STOP / STALE POSITION TIMEOUT
        # --------------------------------------------------
        if self.max_hold_minutes is not None:
            hold_minutes = (
                candle.timestamp - position.entry_time
            ).total_seconds() / 60.0
            if hold_minutes >= self.max_hold_minutes:
                return self._close_position(
                    candle=candle,
                    exit_price=candle.close,
                    exit_reason="TIME_STOP",
                )

        return None

    # ==================================================
    # PROCESS NEW CANDLE
    # ==================================================

    def on_candle(
        self,
        candle: Candle,
    ) -> BrokerEvent | None:
        """
        Process one new market candle.

        IMPORTANT:

        If an entry fills on this candle,
        we do NOT also evaluate SL/TP on
        that exact candle.

        With OHLC data we do not know the
        intrabar sequence after the fill.

        Exit checking begins on the NEXT candle.
        """

        # Existing trade gets priority.
        if self.position is not None:
            return self._check_position_exit(
                candle
            )

        # Otherwise try to fill pending order.
        if self.pending_order is not None:
            return self._try_fill_entry(
                candle
            )

        return None