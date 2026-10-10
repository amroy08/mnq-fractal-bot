from collections.abc import Sequence
from dataclasses import dataclass

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.models.setup import Setup
from mnq_fractal_bot.strategy.cisd import (
    find_cisd_level,
)
from mnq_fractal_bot.strategy.entry_zones import (
    set_c3_entry_zone,
)


@dataclass(frozen=True)
class PostC2Result:
    setup: Setup

    # True means the old post-C2 setup was
    # replaced by a fresh cascading C2 setup.
    replacement_required: bool = False


# ==========================================================
# CASCADE / REPLACEMENT
# ==========================================================


def build_replacement_setup(
    old_setup: Setup,
    candles: Sequence[Candle],
    current_index: int,
) -> Setup:
    """
    Match Pine's post-C2 cascade behavior.

    When price breaks the old C2 extreme:

        old C2 becomes new C1
        current bar becomes new C2
        new CISD search begins immediately

    Direction remains the same.
    """

    if not 0 <= current_index < len(
        candles
    ):
        raise IndexError(
            "Current index is outside "
            "candle history."
        )

    if old_setup.c2_extreme is None:
        raise ValueError(
            "Replacement requires "
            "old C2 extreme."
        )

    current = candles[
        current_index
    ]

    # ======================================================
    # OLD C2 BECOMES NEW C1
    #
    # Python stores:
    #
    #     c2_extreme
    #     c2_mid
    #
    # so we can recover the opposite wick.
    #
    # Bullish old C2:
    #     c2_extreme = low
    #     new C1 liquidity = old C2 high
    #
    # Bearish old C2:
    #     c2_extreme = high
    #     new C1 liquidity = old C2 low
    # ======================================================

    old_c2_opposite = None

    if old_setup.c2_mid is not None:
        old_c2_opposite = (
            2.0 * old_setup.c2_mid
            - old_setup.c2_extreme
        )

    # The old C2 is the HTF candle immediately
    # after the original swept C1.
    new_swept_htf_index = None

    if (
        old_setup.swept_htf_index
        is not None
    ):
        new_swept_htf_index = (
            old_setup.swept_htf_index
            + 1
        )

    # ======================================================
    # BULLISH CASCADE
    # ======================================================

    if old_setup.is_bullish:
        replacement = Setup(
            is_bullish=True,

            is_confirmed=(
                current.close
                > old_setup.c2_extreme
            ),

            is_post_c2=False,

            sweep_price=(
                old_setup.c2_extreme
            ),

            sweep_bar_index=(
                current_index
            ),

            swept_htf_index=(
                new_swept_htf_index
            ),

            htf_count=1,

            tracked_extreme=(
                current.low
            ),

            extreme_bar_index=(
                current_index
            ),

            liq_c1_price=(
                old_c2_opposite
            ),
        )

        bias = -1

    # ======================================================
    # BEARISH CASCADE
    # ======================================================

    else:
        replacement = Setup(
            is_bullish=False,

            is_confirmed=(
                current.close
                < old_setup.c2_extreme
            ),

            is_post_c2=False,

            sweep_price=(
                old_setup.c2_extreme
            ),

            sweep_bar_index=(
                current_index
            ),

            swept_htf_index=(
                new_swept_htf_index
            ),

            htf_count=1,

            tracked_extreme=(
                current.high
            ),

            extreme_bar_index=(
                current_index
            ),

            liq_c1_price=(
                old_c2_opposite
            ),
        )

        bias = 1

    # ======================================================
    # INITIALIZE NEW CISD
    #
    # Pine immediately calls FindCISDLevel()
    # from the new C2 extreme.
    # ======================================================

    cisd = find_cisd_level(
        candles=candles,
        extreme_index=current_index,
        bias=bias,
    )

    if cisd is not None:
        replacement.cisd_level = (
            cisd.price
        )

        replacement.cisd_start_index = (
            cisd.start_index
        )

        replacement.has_cisd = True

    return replacement


# ==========================================================
# POST-C2 UPDATE
# ==========================================================


def update_post_c2_setup(
    setup: Setup,
    candles: Sequence[Candle],
    current_index: int,
) -> PostC2Result:

    if not 0 <= current_index < len(
        candles
    ):
        raise IndexError(
            "Current index is outside "
            "candle history."
        )

    current = candles[
        current_index
    ]

    if not setup.is_post_c2:
        return PostC2Result(
            setup=setup,
        )

    if setup.c2_extreme is None:
        return PostC2Result(
            setup=setup,
        )

    # ======================================================
    # BULLISH
    #
    # Old C2 extreme = C2 low
    # ======================================================

    if setup.is_bullish:

        if (
            current.low
            < setup.c2_extreme
        ):
            # Pine:
            #
            # If CISD had already triggered,
            # the old setup becomes invalid.
            #
            # BUT Pine ALSO immediately starts
            # a new cascading bullish setup.
            if setup.cisd_triggered:
                setup.is_invalid = True

            replacement = (
                build_replacement_setup(
                    old_setup=setup,
                    candles=candles,
                    current_index=current_index,
                )
            )

            return PostC2Result(
                setup=replacement,
                replacement_required=True,
            )

        # ----------------------------------------------
        # CISD may trigger during C3
        # ----------------------------------------------

        if (
            setup.has_cisd
            and not setup.cisd_triggered
            and setup.cisd_level
            is not None
            and current.close
            > setup.cisd_level
        ):
            setup.cisd_triggered = True

            setup.cisd_end_index = (
                current_index
            )

            set_c3_entry_zone(
                setup=setup,
                candles=candles,
            )

    # ======================================================
    # BEARISH
    #
    # Old C2 extreme = C2 high
    # ======================================================

    else:

        if (
            current.high
            > setup.c2_extreme
        ):
            if setup.cisd_triggered:
                setup.is_invalid = True

            replacement = (
                build_replacement_setup(
                    old_setup=setup,
                    candles=candles,
                    current_index=current_index,
                )
            )

            return PostC2Result(
                setup=replacement,
                replacement_required=True,
            )

        # ----------------------------------------------
        # CISD may trigger during C3
        # ----------------------------------------------

        if (
            setup.has_cisd
            and not setup.cisd_triggered
            and setup.cisd_level
            is not None
            and current.close
            < setup.cisd_level
        ):
            setup.cisd_triggered = True

            setup.cisd_end_index = (
                current_index
            )

            set_c3_entry_zone(
                setup=setup,
                candles=candles,
            )

    return PostC2Result(
        setup=setup,
    )