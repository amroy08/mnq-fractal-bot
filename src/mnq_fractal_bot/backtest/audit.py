from dataclasses import dataclass
from datetime import datetime

from mnq_fractal_bot.models.setup import Setup
from mnq_fractal_bot.strategy.trade_plan import TradePlan


@dataclass(frozen=True)
class SignalAudit:
    signal_id: str
    created_at: datetime

    direction: str

    # ==================================================
    # FRACTAL STRUCTURE
    # ==================================================

    sweep_price: float | None
    cisd_level: float | None

    c2_extreme: float | None

    # ==================================================
    # C3
    # ==================================================

    c3_zone_set: bool
    c3_zone_bottom: float | None
    c3_zone_top: float | None
    c3_start_time: datetime | None

    # ==================================================
    # C4
    # ==================================================

    c4_zone_set: bool
    c4_invalid: bool

    c4_zone_bottom: float | None
    c4_zone_top: float | None
    c4_start_time: datetime | None

    # ==================================================
    # TRADE PLAN
    # ==================================================

    entry_name: str | None

    entry_price: float | None
    stop_price: float | None

    tp_c1: float | None
    tp_c0: float | None
    preferred_target: float | None

    model_ready: bool
    bot_trade_ready: bool


def build_signal_audit(
    setup: Setup,
    plan: TradePlan,
    signal_id: str,
    created_at: datetime,
) -> SignalAudit:
    if not signal_id:
        raise ValueError(
            "Signal ID cannot be empty."
        )

    if created_at.tzinfo is None:
        raise ValueError(
            "Audit timestamp must include a timezone."
        )

    return SignalAudit(
        signal_id=signal_id,
        created_at=created_at,

        direction=plan.direction,

        sweep_price=setup.sweep_price,
        cisd_level=setup.cisd_level,

        c2_extreme=setup.c2_extreme,

        c3_zone_set=setup.c3_zone_set,
        c3_zone_bottom=setup.c3_zone_bottom,
        c3_zone_top=setup.c3_zone_top,
        c3_start_time=setup.c3_start_time,

        c4_zone_set=setup.c4_zone_set,
        c4_invalid=setup.c4_invalid,
        c4_zone_bottom=setup.c4_zone_bottom,
        c4_zone_top=setup.c4_zone_top,
        c4_start_time=setup.c4_start_time,

        entry_name=plan.entry_name,

        entry_price=plan.entry_price,
        stop_price=plan.stop_price,

        tp_c1=plan.tp_c1,
        tp_c0=plan.tp_c0,
        preferred_target=plan.preferred_target,

        model_ready=plan.model_ready,
        bot_trade_ready=plan.bot_trade_ready,
    )