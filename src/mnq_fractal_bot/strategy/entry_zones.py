from collections.abc import Sequence
from datetime import datetime

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.models.setup import Setup


# ==========================================================
# CISD BODY RANGE
# ==========================================================


def get_cisd_body_range(
    candles: Sequence[Candle],
    cisd_start_index: int,
    extreme_index: int,
) -> tuple[float, float, float]:
    """
    Match Pine:

        GetCisdBodyRange(
            cisd_start_idx,
            extreme_bar_idx
        )

    IMPORTANT:
    Uses candle BODIES only:

        body high = max(open, close)
        body low  = min(open, close)

    Wicks are intentionally ignored.
    """

    start = min(
        cisd_start_index,
        extreme_index,
    )

    end = max(
        cisd_start_index,
        extreme_index,
    )

    selected = candles[
        start : end + 1
    ]

    if not selected:
        raise ValueError(
            "No candles available for "
            "CISD body range."
        )

    body_high = max(
        max(
            candle.open,
            candle.close,
        )
        for candle in selected
    )

    body_low = min(
        min(
            candle.open,
            candle.close,
        )
        for candle in selected
    )

    body_mid = (
        body_high
        + body_low
    ) / 2.0

    return (
        body_low,
        body_high,
        body_mid,
    )


# ==========================================================
# C3 ENTRY ZONE
# ==========================================================


def set_c3_entry_zone(
    setup: Setup,
    candles: Sequence[Candle],
) -> Setup:
    """
    Create the C3 entry zone exactly once.

    Pine equivalent:

        TrySetEntryZoneC3()

    Pine requires:

        not setup.ez_c3_set

    Therefore once Python has created the C3
    zone, it MUST NOT recalculate or overwrite it.
    """

    # ======================================================
    # PINE:
    #
    # not setup.ez_c3_set
    #
    # This was previously missing in Python.
    # ======================================================

    if setup.c3_zone_set:
        return setup

    if setup.is_invalid:
        return setup

    if not setup.is_post_c2:
        return setup

    if not setup.cisd_triggered:
        return setup

    if setup.c2_mid is None:
        return setup

    if setup.c3_open is None:
        return setup

    if setup.cisd_start_index is None:
        return setup

    if setup.extreme_bar_index is None:
        return setup

    # ======================================================
    # CISD BODY RANGE
    # ======================================================

    (
        body_low,
        body_high,
        body_mid,
    ) = get_cisd_body_range(
        candles=candles,

        cisd_start_index=(
            setup.cisd_start_index
        ),

        extreme_index=(
            setup.extreme_bar_index
        ),
    )

    c2_mid = (
        setup.c2_mid
    )

    # ======================================================
    # PINE:
    #
    # bool inside =
    #     c2m >= body_lo and
    #     c2m <= body_hi
    # ======================================================

    inside_body = (
        body_low
        <= c2_mid
        <= body_high
    )

    # ======================================================
    # PINE:
    #
    # y2 =
    #     inside
    #     ? body_mid
    #     : setup.c3_open
    # ======================================================

    second_price = (
        body_mid
        if inside_body
        else setup.c3_open
    )

    # ======================================================
    # FREEZE C3 ZONE
    # ======================================================

    setup.c3_zone_bottom = min(
        c2_mid,
        second_price,
    )

    setup.c3_zone_top = max(
        c2_mid,
        second_price,
    )

    setup.c3_zone_set = True

    return setup


# ==========================================================
# START POST-C2 / C3 PHASE
# ==========================================================


def start_post_c2_phase(
    setup: Setup,
    completed_c2: Candle,
    c3_open: float,
    c3_start_time: datetime,
    candles: Sequence[Candle],
) -> Setup | None:
    """
    Handle the Pine transition:

        C2 closes
            ↓
        sweep confirmation
            ↓
        post-C2 begins
            ↓
        C3 begins
    """

    # ======================================================
    # CONFIRM C2 SWEEP
    # ======================================================

    if setup.is_bullish:
        c2_confirmed = (
            completed_c2.close
            > setup.sweep_price
        )

    else:
        c2_confirmed = (
            completed_c2.close
            < setup.sweep_price
        )

    # Pine removes the setup when C2 fails
    # to confirm the sweep.
    if not c2_confirmed:
        return None

    setup.is_post_c2 = True
    setup.is_confirmed = True

    # ======================================================
    # SAVE C2 STRUCTURE
    # ======================================================

    setup.c2_extreme = (
        completed_c2.low
        if setup.is_bullish
        else completed_c2.high
    )

    setup.c2_mid = (
        completed_c2.high
        + completed_c2.low
    ) / 2.0

    # ======================================================
    # START C3
    # ======================================================

    setup.c3_open = (
        c3_open
    )

    setup.c3_start_time = (
        c3_start_time
    )

    # ======================================================
    # CISD MAY ALREADY HAVE TRIGGERED DURING C2
    #
    # Pine calls TrySetEntryZoneC3 here.
    # That function itself checks whether
    # CISD is triggered.
    # ======================================================

    if setup.cisd_triggered:
        set_c3_entry_zone(
            setup=setup,
            candles=candles,
        )

    return setup