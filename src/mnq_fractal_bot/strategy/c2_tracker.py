from collections.abc import Sequence

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.models.setup import Setup
from mnq_fractal_bot.strategy.cisd import find_cisd_level


def update_c2_setup(
    setup: Setup,
    candles: Sequence[Candle],
    current_index: int,
) -> Setup:
    if not 0 <= current_index < len(candles):
        raise IndexError(
            "Current index is outside candle history."
        )

    current = candles[current_index]

    # --------------------------------------------------
    # BEARISH SETUP
    # --------------------------------------------------
    if not setup.is_bullish:
        setup.is_confirmed = (
            current.close < setup.sweep_price
        )

        # New C2 higher high
        if (
            setup.tracked_extreme is None
            or current.high > setup.tracked_extreme
        ):
            setup.tracked_extreme = current.high
            setup.extreme_bar_index = current_index

            cisd = find_cisd_level(
                candles=candles,
                extreme_index=current_index,
                bias=1,
            )

            if cisd is not None:
                setup.cisd_level = cisd.price
                setup.cisd_start_index = cisd.start_index
                setup.has_cisd = True

                # New extreme means old CISD trigger is no longer valid.
                setup.cisd_triggered = False
                setup.cisd_end_index = None

        # Body broke below CISD
        if (
            setup.has_cisd
            and setup.cisd_end_index is None
            and setup.cisd_level is not None
            and current.close < setup.cisd_level
        ):
            setup.cisd_end_index = current_index

        # CISD becomes fully valid only after sweep confirmation.
        if (
            setup.is_confirmed
            and setup.has_cisd
            and not setup.cisd_triggered
            and setup.cisd_end_index is not None
        ):
            setup.cisd_triggered = True

    # --------------------------------------------------
    # BULLISH SETUP
    # --------------------------------------------------
    else:
        setup.is_confirmed = (
            current.close > setup.sweep_price
        )

        # New C2 lower low
        if (
            setup.tracked_extreme is None
            or current.low < setup.tracked_extreme
        ):
            setup.tracked_extreme = current.low
            setup.extreme_bar_index = current_index

            cisd = find_cisd_level(
                candles=candles,
                extreme_index=current_index,
                bias=-1,
            )

            if cisd is not None:
                setup.cisd_level = cisd.price
                setup.cisd_start_index = cisd.start_index
                setup.has_cisd = True

                setup.cisd_triggered = False
                setup.cisd_end_index = None

        # Body broke above CISD
        if (
            setup.has_cisd
            and setup.cisd_end_index is None
            and setup.cisd_level is not None
            and current.close > setup.cisd_level
        ):
            setup.cisd_end_index = current_index

        if (
            setup.is_confirmed
            and setup.has_cisd
            and not setup.cisd_triggered
            and setup.cisd_end_index is not None
        ):
            setup.cisd_triggered = True

    return setup