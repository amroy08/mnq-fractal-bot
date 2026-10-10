from dataclasses import dataclass

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.models.setup import Setup


@dataclass(frozen=True)
class ValidTargets:
    c1: float | None
    c0: float | None

    @property
    def has_valid_target(self) -> bool:
        return (
            self.c1 is not None
            or self.c0 is not None
        )

    @property
    def preferred_target(self) -> float | None:
        if self.c1 is not None:
            return self.c1

        return self.c0


def set_formation_liquidity(
    setup: Setup,
    c1: Candle,
    c0: Candle | None = None,
) -> Setup:
    """
    Store the Fractal Model's C1/C0 formation liquidity.

    Bearish:
        C1 = C1 low
        C0 = older low only when lower than C1 low

    Bullish:
        C1 = C1 high
        C0 = older high only when higher than C1 high
    """

    # Reset first so stale values cannot survive.
    setup.liq_c1_price = None
    setup.liq_c0_price = None

    if setup.is_bullish:
        # Bullish target is liquidity above price.
        # If previous candle has an equal low with older candle, the swept level
        # originated from the older candle, so its higher extreme is the true formation swing.
        if (
            c0 is not None
            and c1.low == c0.low
            and c0.high > c1.high
        ):
            setup.liq_c1_price = c0.high
        else:
            setup.liq_c1_price = c1.high

            if (
                c0 is not None
                and c0.high > c1.high
            ):
                setup.liq_c0_price = c0.high

    else:
        # Bearish target is liquidity below price.
        # If previous candle has an equal high with older candle, the swept level
        # originated from the older candle, so its lower extreme is the true formation swing.
        if (
            c0 is not None
            and c1.high == c0.high
            and c0.low < c1.low
        ):
            setup.liq_c1_price = c0.low
        else:
            setup.liq_c1_price = c1.low

            if (
                c0 is not None
                and c0.low < c1.low
            ):
                setup.liq_c0_price = c0.low

    return setup


def get_valid_targets(
    setup: Setup,
    entry_price: float,
) -> ValidTargets:
    """
    Filter C1/C0 liquidity by trade direction.

    LONG:
        TP must be above entry.

    SHORT:
        TP must be below entry.
    """

    valid_c1 = None
    valid_c0 = None

    if setup.is_bullish:
        if (
            setup.liq_c1_price is not None
            and setup.liq_c1_price > entry_price
        ):
            valid_c1 = setup.liq_c1_price

        if (
            setup.liq_c0_price is not None
            and setup.liq_c0_price > entry_price
        ):
            valid_c0 = setup.liq_c0_price

    else:
        if (
            setup.liq_c1_price is not None
            and setup.liq_c1_price < entry_price
        ):
            valid_c1 = setup.liq_c1_price

        if (
            setup.liq_c0_price is not None
            and setup.liq_c0_price < entry_price
        ):
            valid_c0 = setup.liq_c0_price

    return ValidTargets(
        c1=valid_c1,
        c0=valid_c0,
    )