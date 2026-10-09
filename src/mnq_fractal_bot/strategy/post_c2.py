from collections.abc import Sequence
from dataclasses import dataclass

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.models.setup import Setup
from mnq_fractal_bot.strategy.entry_zones import (
    set_c3_entry_zone,
)


@dataclass(frozen=True)
class PostC2Result:
    setup: Setup

    # True means:
    # C2 extreme was broken BEFORE CISD confirmation.
    # The Pine model replaces/cascades into a new setup.
    replacement_required: bool = False


def update_post_c2_setup(
    setup: Setup,
    candles: Sequence[Candle],
    current_index: int,
) -> PostC2Result:
    if not 0 <= current_index < len(candles):
        raise IndexError(
            "Current index is outside candle history."
        )

    current = candles[current_index]

    if not setup.is_post_c2:
        return PostC2Result(
            setup=setup,
        )

    if setup.c2_extreme is None:
        return PostC2Result(
            setup=setup,
        )

    # ==================================================
    # BULLISH SETUP
    # C2 extreme = C2 low
    # ==================================================
    if setup.is_bullish:
        if current.low < setup.c2_extreme:

            # CISD already confirmed:
            # breaking C2 low invalidates setup.
            if setup.cisd_triggered:
                setup.is_invalid = True

                return PostC2Result(
                    setup=setup,
                )

            # CISD not confirmed yet:
            # Pine replaces this setup with a new one.
            return PostC2Result(
                setup=setup,
                replacement_required=True,
            )

        # CISD can still trigger during C3.
        if (
            setup.has_cisd
            and not setup.cisd_triggered
            and setup.cisd_level is not None
            and current.close > setup.cisd_level
        ):
            setup.cisd_triggered = True
            setup.cisd_end_index = current_index

            set_c3_entry_zone(
                setup=setup,
                candles=candles,
            )

    # ==================================================
    # BEARISH SETUP
    # C2 extreme = C2 high
    # ==================================================
    else:
        if current.high > setup.c2_extreme:

            # CISD already confirmed:
            # breaking C2 high invalidates setup.
            if setup.cisd_triggered:
                setup.is_invalid = True

                return PostC2Result(
                    setup=setup,
                )

            # CISD not confirmed:
            # Pine starts replacement setup.
            return PostC2Result(
                setup=setup,
                replacement_required=True,
            )

        # CISD can still trigger during C3.
        if (
            setup.has_cisd
            and not setup.cisd_triggered
            and setup.cisd_level is not None
            and current.close < setup.cisd_level
        ):
            setup.cisd_triggered = True
            setup.cisd_end_index = current_index

            set_c3_entry_zone(
                setup=setup,
                candles=candles,
            )

    return PostC2Result(
        setup=setup,
    )