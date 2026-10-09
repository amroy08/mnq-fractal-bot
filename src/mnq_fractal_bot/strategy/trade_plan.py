from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from mnq_fractal_bot.models.setup import Setup
from mnq_fractal_bot.strategy.liquidity import (
    get_valid_targets,
)


@dataclass(frozen=True)
class TradePlan:
    direction: str

    entry_name: str | None

    entry_bottom: float | None
    entry_top: float | None
    entry_price: float | None

    stop_price: float | None

    tp_c1: float | None
    tp_c0: float | None
    preferred_target: float | None

    model_ready: bool
    has_valid_target: bool

    # Stricter than model_ready.
    #
    # The TradingView model can say READY
    # without a valid TP.
    #
    # Our automated paper bot will NOT trade
    # unless Entry + SL + valid TP all exist.
    bot_trade_ready: bool


def round_to_tick(
    price: float,
    tick_size: float,
) -> float:
    if tick_size <= 0:
        raise ValueError(
            "Tick size must be greater than zero."
        )

    price_decimal = Decimal(
        str(price)
    )

    tick_decimal = Decimal(
        str(tick_size)
    )

    ticks = (
        price_decimal
        / tick_decimal
    ).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )

    return float(
        ticks * tick_decimal
    )


def build_trade_plan(
    setup: Setup,
    tick_size: float = 0.25,
    sl_buffer_ticks: int = 2,
) -> TradePlan:
    if tick_size <= 0:
        raise ValueError(
            "Tick size must be greater than zero."
        )

    if sl_buffer_ticks < 0:
        raise ValueError(
            "SL buffer ticks cannot be negative."
        )

    direction = (
        "LONG"
        if setup.is_bullish
        else "SHORT"
    )

    entry_name = None
    entry_bottom = None
    entry_top = None

    # ==================================================
    # ENTRY ZONE
    #
    # Pine preference:
    #
    # 1. Valid C4
    # 2. C3
    # ==================================================

    if (
        setup.c4_zone_set
        and not setup.c4_invalid
        and setup.c4_zone_bottom is not None
        and setup.c4_zone_top is not None
    ):
        entry_name = "C4 ENTRY ZONE"

        entry_bottom = (
            setup.c4_zone_bottom
        )

        entry_top = (
            setup.c4_zone_top
        )

    elif (
        setup.c3_zone_set
        and setup.c3_zone_bottom is not None
        and setup.c3_zone_top is not None
    ):
        entry_name = "C3 ENTRY ZONE"

        entry_bottom = (
            setup.c3_zone_bottom
        )

        entry_top = (
            setup.c3_zone_top
        )

    # ==================================================
    # ENTRY MIDPOINT
    # ==================================================

    entry_price = None

    if (
        entry_bottom is not None
        and entry_top is not None
    ):
        raw_entry = (
            entry_bottom
            + entry_top
        ) / 2.0

        entry_price = round_to_tick(
            raw_entry,
            tick_size,
        )

    # ==================================================
    # STOP LOSS
    #
    # Pine:
    #
    # c2_extreme when available,
    # otherwise tracked_extreme.
    # ==================================================

    model_extreme = (
        setup.c2_extreme
        if setup.c2_extreme is not None
        else setup.tracked_extreme
    )

    stop_price = None

    if model_extreme is not None:
        buffer = (
            sl_buffer_ticks
            * tick_size
        )

        if setup.is_bullish:
            raw_stop = (
                model_extreme
                - buffer
            )

        else:
            raw_stop = (
                model_extreme
                + buffer
            )

        stop_price = round_to_tick(
            raw_stop,
            tick_size,
        )

    # ==================================================
    # TARGETS
    # ==================================================

    tp_c1 = None
    tp_c0 = None
    preferred_target = None
    has_valid_target = False

    if entry_price is not None:
        targets = get_valid_targets(
            setup=setup,
            entry_price=entry_price,
        )

        tp_c1 = targets.c1
        tp_c0 = targets.c0

        preferred_target = (
            targets.preferred_target
        )

        has_valid_target = (
            targets.has_valid_target
        )

    # ==================================================
    # FRACTAL MODEL READY
    #
    # The Pine builder requires:
    #
    # setup valid
    # sweep confirmed
    # CISD triggered
    # entry zone available
    # ==================================================

    model_ready = (
        not setup.is_invalid
        and setup.is_confirmed
        and setup.cisd_triggered
        and entry_price is not None
    )

    # ==================================================
    # AUTOMATED PAPER-BOT READY
    #
    # Stricter than the visual Fractal Model.
    # ==================================================

    bot_trade_ready = (
        model_ready
        and stop_price is not None
        and has_valid_target
    )

    return TradePlan(
        direction=direction,
        entry_name=entry_name,
        entry_bottom=entry_bottom,
        entry_top=entry_top,
        entry_price=entry_price,
        stop_price=stop_price,
        tp_c1=tp_c1,
        tp_c0=tp_c0,
        preferred_target=preferred_target,
        model_ready=model_ready,
        has_valid_target=has_valid_target,
        bot_trade_ready=bot_trade_ready,
    )