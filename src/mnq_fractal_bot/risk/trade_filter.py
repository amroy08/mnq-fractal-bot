from dataclasses import dataclass

from mnq_fractal_bot.strategy.trade_plan import (
    TradePlan,
)


@dataclass(frozen=True)
class TradeFilterConfig:
    # Allow C3 entry-zone trades.
    allow_c3: bool = True

    # Allow C4 entry-zone trades.
    allow_c4: bool = True

    # Maximum distance between entry and stop,
    # measured in MNQ points.
    #
    # None = no stop-distance restriction.
    max_stop_points: float | None = None

    def __post_init__(self):
        if (
            self.max_stop_points is not None
            and self.max_stop_points < 0
        ):
            raise ValueError(
                "max_stop_points cannot be negative."
            )


@dataclass(frozen=True)
class TradeFilterDecision:
    allowed: bool

    reason: str

    stop_distance_points: float | None


def evaluate_trade_plan(
    plan: TradePlan,
    config: TradeFilterConfig,
) -> TradeFilterDecision:
    """
    Decide whether a BOT TRADE READY plan
    is allowed through the execution filter.

    This does NOT change the Fractal Model.

    It only controls whether the paper bot
    is permitted to submit the trade.
    """

    # ==================================================
    # BOT MUST ALREADY BE READY
    # ==================================================

    if not plan.bot_trade_ready:
        return TradeFilterDecision(
            allowed=False,
            reason="BOT_NOT_READY",
            stop_distance_points=None,
        )

    # ==================================================
    # ENTRY ZONE FILTER
    # ==================================================

    if plan.entry_name == "C3 ENTRY ZONE":
        if not config.allow_c3:
            return TradeFilterDecision(
                allowed=False,
                reason="C3_DISABLED",
                stop_distance_points=None,
            )

    elif plan.entry_name == "C4 ENTRY ZONE":
        if not config.allow_c4:
            return TradeFilterDecision(
                allowed=False,
                reason="C4_DISABLED",
                stop_distance_points=None,
            )

    else:
        return TradeFilterDecision(
            allowed=False,
            reason="UNKNOWN_ENTRY_ZONE",
            stop_distance_points=None,
        )

    # ==================================================
    # ENTRY + STOP REQUIRED
    # ==================================================

    if (
        plan.entry_price is None
        or plan.stop_price is None
    ):
        return TradeFilterDecision(
            allowed=False,
            reason="MISSING_ENTRY_OR_STOP",
            stop_distance_points=None,
        )

    # ==================================================
    # STOP DISTANCE
    # ==================================================

    stop_distance = abs(
        plan.stop_price
        - plan.entry_price
    )

    # ==================================================
    # MAX STOP FILTER
    # ==================================================

    if (
        config.max_stop_points is not None
        and stop_distance
        > config.max_stop_points
    ):
        return TradeFilterDecision(
            allowed=False,
            reason="MAX_STOP_EXCEEDED",
            stop_distance_points=stop_distance,
        )

    # ==================================================
    # ALLOWED
    # ==================================================

    return TradeFilterDecision(
        allowed=True,
        reason="ALLOWED",
        stop_distance_points=stop_distance,
    )