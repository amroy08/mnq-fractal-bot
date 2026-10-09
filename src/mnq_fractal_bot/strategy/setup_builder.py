from dataclasses import dataclass

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.models.setup import Setup
from mnq_fractal_bot.strategy.sweep import detect_sweep


@dataclass(frozen=True)
class SetupCandidates:
    bearish: Setup | None = None
    bullish: Setup | None = None


def create_setup_candidates(
    previous_htf: Candle,
    current_candle: Candle,
    bar_index: int,
    previous_htf_index: int,
) -> SetupCandidates:
    sweep = detect_sweep(
        previous_htf=previous_htf,
        current_candle=current_candle,
    )

    bearish_setup = None
    bullish_setup = None

    # --------------------------------------------------
    # BEARISH
    # Current candle sweeps above previous HTF high.
    # --------------------------------------------------
    if sweep.bearish_breached:
        bearish_setup = Setup(
            is_bullish=False,
            is_confirmed=sweep.bearish_confirmed,
            sweep_price=previous_htf.high,
            sweep_bar_index=bar_index,
            swept_htf_index=previous_htf_index,
            htf_count=1,
            tracked_extreme=current_candle.high,
            extreme_bar_index=bar_index,
            liq_c1_price=previous_htf.low,
        )

    # --------------------------------------------------
    # BULLISH
    # Current candle sweeps below previous HTF low.
    # --------------------------------------------------
    if sweep.bullish_breached:
        bullish_setup = Setup(
            is_bullish=True,
            is_confirmed=sweep.bullish_confirmed,
            sweep_price=previous_htf.low,
            sweep_bar_index=bar_index,
            swept_htf_index=previous_htf_index,
            htf_count=1,
            tracked_extreme=current_candle.low,
            extreme_bar_index=bar_index,
            liq_c1_price=previous_htf.high,
        )

    return SetupCandidates(
        bearish=bearish_setup,
        bullish=bullish_setup,
    )