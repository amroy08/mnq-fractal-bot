from dataclasses import dataclass
from datetime import datetime


@dataclass
class Setup:
    # --------------------------------------------------
    # Direction / status
    # --------------------------------------------------
    is_bullish: bool
    is_confirmed: bool = False
    is_post_c2: bool = False
    is_invalid: bool = False

    # --------------------------------------------------
    # Sweep
    # --------------------------------------------------
    sweep_price: float | None = None
    sweep_bar_index: int | None = None
    swept_htf_index: int | None = None
    htf_count: int = 0

    # --------------------------------------------------
    # C2
    # --------------------------------------------------
    c2_extreme: float | None = None
    c2_mid: float | None = None

    tracked_extreme: float | None = None
    extreme_bar_index: int | None = None

    # --------------------------------------------------
    # CISD
    # --------------------------------------------------
    has_cisd: bool = False
    cisd_triggered: bool = False

    cisd_level: float | None = None
    cisd_start_index: int | None = None
    cisd_end_index: int | None = None

    # --------------------------------------------------
    # C3
    # --------------------------------------------------
    c3_open: float | None = None

    c3_zone_set: bool = False
    c3_zone_bottom: float | None = None
    c3_zone_top: float | None = None

    c3_start_time: datetime | None = None
    c3_end_time: datetime | None = None

    # --------------------------------------------------
    # C4
    # --------------------------------------------------
    c3_mid: float | None = None
    c3_extreme: float | None = None

    c4_open: float | None = None

    c4_zone_set: bool = False
    c4_invalid: bool = False

    c4_zone_bottom: float | None = None
    c4_zone_top: float | None = None

    c4_start_time: datetime | None = None
    c4_end_time: datetime | None = None

    # --------------------------------------------------
    # Formation liquidity
    # --------------------------------------------------
    liq_c1_price: float | None = None
    liq_c0_price: float | None = None

    # --------------------------------------------------
    # SMT
    # --------------------------------------------------
    has_smt: bool = False
    smt_symbol: str | None = None