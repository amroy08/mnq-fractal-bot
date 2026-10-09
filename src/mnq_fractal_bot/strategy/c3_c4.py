from datetime import datetime

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.models.setup import Setup


def update_c3_invalidation(
    setup: Setup,
    current_candle: Candle,
) -> Setup:
    """
    Check whether price invalidates the setup during C3.

    Bearish:
        price above C2 high invalidates.

    Bullish:
        price below C2 low invalidates.
    """

    if setup.is_invalid:
        return setup

    if not setup.is_post_c2:
        return setup

    if setup.c2_extreme is None:
        return setup

    if setup.is_bullish:
        if current_candle.low < setup.c2_extreme:
            setup.is_invalid = True

    else:
        if current_candle.high > setup.c2_extreme:
            setup.is_invalid = True

    return setup


def start_c4_phase(
    setup: Setup,
    completed_c3: Candle,
    c4_open: float,
    c4_start_time: datetime,
    c4_end_time: datetime,
) -> Setup:
    """
    C3 has completed and C4 is beginning.

    Store:
    - C3 midpoint
    - C3 extreme
    - C4 open
    - C4 time window
    - C4 entry zone
    """

    if setup.is_invalid:
        return setup

    if not setup.is_post_c2:
        return setup

    if not setup.cisd_triggered:
        return setup

    # C3 has now finished.
    setup.c3_end_time = c4_start_time

    # C3 midpoint.
    setup.c3_mid = (
        completed_c3.high
        + completed_c3.low
    ) / 2.0

    # Pine uses:
    # bullish -> C3 low
    # bearish -> C3 high
    setup.c3_extreme = (
        completed_c3.low
        if setup.is_bullish
        else completed_c3.high
    )

    # Start C4.
    setup.c4_open = c4_open
    setup.c4_start_time = c4_start_time
    setup.c4_end_time = c4_end_time

    # C4 entry zone:
    # between C3 midpoint and C4 open.
    setup.c4_zone_bottom = min(
        setup.c3_mid,
        c4_open,
    )

    setup.c4_zone_top = max(
        setup.c3_mid,
        c4_open,
    )

    setup.c4_zone_set = True
    setup.c4_invalid = False

    return setup


def update_c4_invalidation(
    setup: Setup,
    current_candle: Candle,
) -> Setup:
    """
    Invalidate the C4 entry zone when price
    crosses beyond the C3 extreme.

    Bullish:
        below C3 low.

    Bearish:
        above C3 high.
    """

    if setup.is_invalid:
        return setup

    if not setup.c4_zone_set:
        return setup

    if setup.c4_invalid:
        return setup

    if setup.c3_extreme is None:
        return setup

    if setup.is_bullish:
        if current_candle.low < setup.c3_extreme:
            setup.c4_invalid = True

    else:
        if current_candle.high > setup.c3_extreme:
            setup.c4_invalid = True

    return setup