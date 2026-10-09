from dataclasses import dataclass
from datetime import datetime, timedelta

from mnq_fractal_bot.data.htf_builder import DevelopingHTFBuilder
from mnq_fractal_bot.data.timeframes import get_higher_timeframe
from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.models.setup import Setup

from mnq_fractal_bot.strategy.c2_tracker import update_c2_setup

from mnq_fractal_bot.strategy.c3_c4 import (
    start_c4_phase,
    update_c4_invalidation,
)

from mnq_fractal_bot.strategy.cisd import find_cisd_level

from mnq_fractal_bot.strategy.entry_zones import (
    start_post_c2_phase,
)

from mnq_fractal_bot.strategy.liquidity import (
    set_formation_liquidity,
)

from mnq_fractal_bot.strategy.post_c2 import (
    update_post_c2_setup,
)

from mnq_fractal_bot.strategy.setup_builder import (
    create_setup_candidates,
)

from mnq_fractal_bot.strategy.setup_selection import (
    select_setup,
)

from mnq_fractal_bot.strategy.trade_plan import (
    TradePlan,
    build_trade_plan,
)


@dataclass(frozen=True)
class EngineSnapshot:
    bar_index: int

    lower_timeframe: str
    higher_timeframe: str

    developing_htf: Candle | None
    previous_completed_htf: Candle | None

    bearish_setup: Setup | None
    bullish_setup: Setup | None

    completed_setups: tuple[Setup, ...]

    # Setup currently chosen by the same
    # priority concept as the Pine builder.
    selected_setup: Setup | None

    # True when bullish and bearish setups
    # have equal priority.
    both_sides: bool

    # Entry / SL / TP / READY output.
    trade_plan: TradePlan | None


class FractalEngine:
    def __init__(
        self,
        lower_timeframe: str,
        tick_size: float = 0.25,
        sl_buffer_ticks: int = 2,
    ):
        self.lower_timeframe = (
            lower_timeframe
        )

        self.higher_timeframe = (
            get_higher_timeframe(
                lower_timeframe
            )
        )

        if self.higher_timeframe not in {
            "1h",
            "4h",
        }:
            raise ValueError(
                "FractalEngine currently supports "
                "5m→1h and 15m→4h."
            )

        if tick_size <= 0:
            raise ValueError(
                "Tick size must be greater than zero."
            )

        if sl_buffer_ticks < 0:
            raise ValueError(
                "SL buffer ticks cannot be negative."
            )

        self.tick_size = tick_size

        self.sl_buffer_ticks = (
            sl_buffer_ticks
        )

        self.htf_builder = (
            DevelopingHTFBuilder(
                self.higher_timeframe
            )
        )

        # All lower-timeframe candles.
        self.ltf_candles: list[Candle] = []

        # Completed HTF candles.
        self.completed_htf_candles: list[
            Candle
        ] = []

        # Live Fractal setups.
        self.live_bearish: Setup | None = None
        self.live_bullish: Setup | None = None

        # C3 completed / C4 historical setups.
        self.completed_setups: list[
            Setup
        ] = []

    # ==================================================
    # HTF HELPERS
    # ==================================================

    def _get_htf_end_time(
        self,
        start_time: datetime,
    ) -> datetime:
        if self.higher_timeframe == "1h":
            return (
                start_time
                + timedelta(hours=1)
            )

        if self.higher_timeframe == "4h":
            return (
                start_time
                + timedelta(hours=4)
            )

        raise ValueError(
            f"Unsupported HTF: "
            f"{self.higher_timeframe}"
        )

    # ==================================================
    # CISD
    # ==================================================

    def _initialize_cisd(
        self,
        setup: Setup,
        current_index: int,
    ) -> Setup:
        bias = (
            -1
            if setup.is_bullish
            else 1
        )

        cisd = find_cisd_level(
            candles=self.ltf_candles,
            extreme_index=current_index,
            bias=bias,
        )

        if cisd is not None:
            setup.cisd_level = (
                cisd.price
            )

            setup.cisd_start_index = (
                cisd.start_index
            )

            setup.has_cisd = True

        return setup

    # ==================================================
    # HTF TRANSITIONS
    # ==================================================

    def _transition_setup_at_htf_boundary(
        self,
        setup: Setup,
        completed_htf: Candle,
        current_candle: Candle,
    ) -> Setup | None:
        setup.htf_count += 1

        # --------------------------------------------------
        # C2 CLOSED -> C3
        # --------------------------------------------------

        if not setup.is_post_c2:
            return start_post_c2_phase(
                setup=setup,
                completed_c2=completed_htf,
                c3_open=current_candle.open,
                c3_start_time=current_candle.timestamp,
                candles=self.ltf_candles,
            )

        # --------------------------------------------------
        # C3 CLOSED -> C4
        # --------------------------------------------------

        if (
            not setup.cisd_triggered
            or setup.is_invalid
        ):
            return None

        c4_end_time = (
            self._get_htf_end_time(
                current_candle.timestamp
            )
        )

        setup = start_c4_phase(
            setup=setup,
            completed_c3=completed_htf,
            c4_open=current_candle.open,
            c4_start_time=(
                current_candle.timestamp
            ),
            c4_end_time=c4_end_time,
        )

        self.completed_setups.append(
            setup
        )

        return None

    def _handle_htf_transition(
        self,
        completed_htf: Candle,
        current_candle: Candle,
    ) -> None:
        if self.live_bearish is not None:
            self.live_bearish = (
                self._transition_setup_at_htf_boundary(
                    setup=self.live_bearish,
                    completed_htf=completed_htf,
                    current_candle=current_candle,
                )
            )

        if self.live_bullish is not None:
            self.live_bullish = (
                self._transition_setup_at_htf_boundary(
                    setup=self.live_bullish,
                    completed_htf=completed_htf,
                    current_candle=current_candle,
                )
            )

    # ==================================================
    # LIVE SETUP UPDATES
    # ==================================================

    def _update_one_live_setup(
        self,
        setup: Setup,
        current_index: int,
    ) -> Setup | None:
        # --------------------------------------------------
        # C2
        # --------------------------------------------------

        if not setup.is_post_c2:
            return update_c2_setup(
                setup=setup,
                candles=self.ltf_candles,
                current_index=current_index,
            )

        # --------------------------------------------------
        # C3 / POST-C2
        # --------------------------------------------------

        result = update_post_c2_setup(
            setup=setup,
            candles=self.ltf_candles,
            current_index=current_index,
        )

        if result.replacement_required:
            return None

        return result.setup

    def _update_existing_setups(
        self,
        current_index: int,
    ) -> None:
        if self.live_bearish is not None:
            self.live_bearish = (
                self._update_one_live_setup(
                    setup=self.live_bearish,
                    current_index=current_index,
                )
            )

        if self.live_bullish is not None:
            self.live_bullish = (
                self._update_one_live_setup(
                    setup=self.live_bullish,
                    current_index=current_index,
                )
            )

    # ==================================================
    # C4
    # ==================================================

    def _update_completed_setups(
        self,
        current_candle: Candle,
    ) -> None:
        for setup in self.completed_setups:
            if setup.c4_zone_set:
                update_c4_invalidation(
                    setup=setup,
                    current_candle=current_candle,
                )

    # ==================================================
    # NEW SWEEP SETUPS
    # ==================================================

    def _prepare_new_setup(
        self,
        setup: Setup,
        previous_htf: Candle,
        older_htf: Candle | None,
        current_index: int,
    ) -> Setup:
        # Add the setup's own C1 / C0
        # formation liquidity.
        setup = set_formation_liquidity(
            setup=setup,
            c1=previous_htf,
            c0=older_htf,
        )

        # Find initial CISD.
        setup = self._initialize_cisd(
            setup=setup,
            current_index=current_index,
        )

        return setup

    def _create_new_setups(
        self,
        current_candle: Candle,
        current_index: int,
    ) -> None:
        if not self.completed_htf_candles:
            return

        previous_htf = (
            self.completed_htf_candles[-1]
        )

        older_htf = None

        if (
            len(
                self.completed_htf_candles
            )
            >= 2
        ):
            older_htf = (
                self.completed_htf_candles[-2]
            )

        previous_htf_index = (
            len(
                self.completed_htf_candles
            )
            - 1
        )

        candidates = create_setup_candidates(
            previous_htf=previous_htf,
            current_candle=current_candle,
            bar_index=current_index,
            previous_htf_index=previous_htf_index,
        )

        # --------------------------------------------------
        # BEARISH
        # --------------------------------------------------

        if (
            self.live_bearish is None
            and candidates.bearish
            is not None
        ):
            self.live_bearish = (
                self._prepare_new_setup(
                    setup=(
                        candidates.bearish
                    ),
                    previous_htf=previous_htf,
                    older_htf=older_htf,
                    current_index=current_index,
                )
            )

        # --------------------------------------------------
        # BULLISH
        # --------------------------------------------------

        if (
            self.live_bullish is None
            and candidates.bullish
            is not None
        ):
            self.live_bullish = (
                self._prepare_new_setup(
                    setup=(
                        candidates.bullish
                    ),
                    previous_htf=previous_htf,
                    older_htf=older_htf,
                    current_index=current_index,
                )
            )

    # ==================================================
    # OUTPUT / TRADE PLAN
    # ==================================================

    def _build_trade_output(
        self,
        current_time: datetime,
    ) -> tuple[
        Setup | None,
        bool,
        TradePlan | None,
    ]:
        selection = select_setup(
            live_bullish=(
                self.live_bullish
            ),
            live_bearish=(
                self.live_bearish
            ),
            completed_setups=(
                self.completed_setups
            ),
            current_time=current_time,
        )

        trade_plan = None

        if selection.setup is not None:
            trade_plan = build_trade_plan(
                setup=selection.setup,
                tick_size=self.tick_size,
                sl_buffer_ticks=(
                    self.sl_buffer_ticks
                ),
            )

        return (
            selection.setup,
            selection.both_sides,
            trade_plan,
        )

    # ==================================================
    # MAIN
    # ==================================================

    def on_candle(
        self,
        candle: Candle,
    ) -> EngineSnapshot:
        # --------------------------------------------------
        # 1. STORE LOWER-TIMEFRAME CANDLE
        # --------------------------------------------------

        self.ltf_candles.append(
            candle
        )

        current_index = (
            len(self.ltf_candles)
            - 1
        )

        # --------------------------------------------------
        # 2. DEVELOP HTF CANDLE
        # --------------------------------------------------

        completed_htf, developing_htf = (
            self.htf_builder.update(
                candle
            )
        )

        # --------------------------------------------------
        # 3. HTF BOUNDARY
        # --------------------------------------------------

        if completed_htf is not None:
            self.completed_htf_candles.append(
                completed_htf
            )

            self._handle_htf_transition(
                completed_htf=completed_htf,
                current_candle=candle,
            )

        # --------------------------------------------------
        # 4. UPDATE LIVE C2 / C3 SETUPS
        # --------------------------------------------------

        self._update_existing_setups(
            current_index=current_index,
        )

        # --------------------------------------------------
        # 5. UPDATE HISTORICAL C4 SETUPS
        # --------------------------------------------------

        self._update_completed_setups(
            current_candle=candle,
        )

        # --------------------------------------------------
        # 6. CHECK NEW SWEEPS
        # --------------------------------------------------

        self._create_new_setups(
            current_candle=candle,
            current_index=current_index,
        )

        # --------------------------------------------------
        # 7. CHOOSE MODEL + BUILD TRADE PLAN
        # --------------------------------------------------

        (
            selected_setup,
            both_sides,
            trade_plan,
        ) = self._build_trade_output(
            current_time=candle.timestamp,
        )

        previous_completed_htf = None

        if self.completed_htf_candles:
            previous_completed_htf = (
                self.completed_htf_candles[-1]
            )

        # --------------------------------------------------
        # 8. SNAPSHOT
        # --------------------------------------------------

        return EngineSnapshot(
            bar_index=current_index,
            lower_timeframe=(
                self.lower_timeframe
            ),
            higher_timeframe=(
                self.higher_timeframe
            ),
            developing_htf=(
                developing_htf
            ),
            previous_completed_htf=(
                previous_completed_htf
            ),
            bearish_setup=(
                self.live_bearish
            ),
            bullish_setup=(
                self.live_bullish
            ),
            completed_setups=tuple(
                self.completed_setups
            ),
            selected_setup=(
                selected_setup
            ),
            both_sides=(
                both_sides
            ),
            trade_plan=(
                trade_plan
            ),
        )