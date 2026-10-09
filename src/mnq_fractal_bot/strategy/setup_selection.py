from dataclasses import dataclass
from datetime import datetime
from collections.abc import Sequence

from mnq_fractal_bot.models.setup import Setup


@dataclass(frozen=True)
class SetupSelection:
    setup: Setup | None
    both_sides: bool = False


def setup_score(
    setup: Setup,
) -> int:
    """
    Match the Beginner Builder priority.

    3 = CISD confirmed
    2 = sweep confirmed
    1 = sweep exists / building
    """

    if setup.cisd_triggered:
        return 3

    if setup.is_confirmed:
        return 2

    return 1


def select_setup(
    live_bullish: Setup | None,
    live_bearish: Setup | None,
    completed_setups: Sequence[Setup],
    current_time: datetime,
) -> SetupSelection:
    # ==================================================
    # BOTH LIVE
    # ==================================================

    if (
        live_bullish is not None
        and live_bearish is not None
    ):
        bullish_score = setup_score(
            live_bullish
        )

        bearish_score = setup_score(
            live_bearish
        )

        if bullish_score > bearish_score:
            return SetupSelection(
                setup=live_bullish,
            )

        if bearish_score > bullish_score:
            return SetupSelection(
                setup=live_bearish,
            )

        # Same stage on both sides.
        return SetupSelection(
            setup=None,
            both_sides=True,
        )

    # ==================================================
    # ONLY BULLISH
    # ==================================================

    if live_bullish is not None:
        return SetupSelection(
            setup=live_bullish,
        )

    # ==================================================
    # ONLY BEARISH
    # ==================================================

    if live_bearish is not None:
        return SetupSelection(
            setup=live_bearish,
        )

    # ==================================================
    # NO LIVE SETUP
    #
    # Check newest historical setup whose
    # C3/C4 entry window is still active.
    # ==================================================

    for setup in reversed(
        completed_setups
    ):
        if setup.is_invalid:
            continue

        c3_active = (
            setup.c3_zone_set
            and (
                setup.c3_end_time is None
                or current_time
                < setup.c3_end_time
            )
        )

        c4_active = (
            setup.c4_zone_set
            and not setup.c4_invalid
            and (
                setup.c4_end_time is None
                or current_time
                < setup.c4_end_time
            )
        )

        if c3_active or c4_active:
            return SetupSelection(
                setup=setup,
            )

    return SetupSelection(
        setup=None,
    )