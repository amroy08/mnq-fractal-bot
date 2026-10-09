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
from mnq_fractal_bot.strategy.entry_zones import start_post_c2_phase
from mnq_fractal_bot.strategy.post_c2 import update_post_c2_setup
from mnq_fractal_bot.strategy.setup_builder import (
    create_setup_candidates,
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


class FractalEngine:
    def __init__(
        self,
        lower_timeframe: str,
    ):
        self.lower_timeframe = lower_timeframe

        self.higher_timeframe = (
            get_higher_timeframe(
                lower_timeframe
            )
        )

        # For now we are focusing on:
        #
        # 5m  -> 1H
        # 15m -> 4H
        if self.higher_timeframe not in {
            "1h",
            "4h",
        }:
            raise ValueError(
                "FractalEngine currently supports "
                "5m→1h and 15m→4h."
            )

        self.htf_builder = DevelopingHTFBuilder(
            self.higher_timeframe
        )

        # All incoming lower-timeframe candles.
        self.ltf_candles: list[Candle] = []

        # Completed 1H / 4H candles.
        self.completed_htf_candles: list[Candle] = []

        # Pine equivalents:
        #
        # live_bearish
        # live_bullish
        self.live_bearish: Setup | None = None
        self.live_bullish: Setup | None = None

        # Pine moves completed C3 setups into
        # its historical setup collection.
        self.completed_setups: list[Setup] = []

    # ==================================================
    # HTF HELPERS
    # ==================================================

    def _get_htf_end_time(
        self,
        start_time: datetime,
    ) -> datetime:
        if self.higher_timeframe == "1h":
            return start_time + timedelta(hours=1)

        if self.higher_timeframe == "4h":
            return start_time + timedelta(hours=4)

        raise ValueError(
            f"Unsupported HTF: {self.higher_timeframe}"
        )

    # ==================================================
    # CISD INITIALIZATION
    # ==================================================

    def _initialize_cisd(
        self,
        setup: Setup,
        current_index: int,
    ) -> Setup:
        """
        A new Fractal sweep setup immediately
        searches backwards for its CISD level.
        """

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
            setup.cisd_level = cisd.price
            setup.cisd_start_index = (
                cisd.start_index
            )

            setup.has_cisd = True

        return setup

    # ==================================================
    # HTF BOUNDARY TRANSITIONS
    # ==================================================

    def _transition_setup_at_htf_boundary(
        self,
        setup: Setup,
        completed_htf: Candle,
        current_candle: Candle,
    ) -> Setup | None:
        """
        Called when a new HTF candle starts.

        Two possible transitions:

        C2 closes -> C3 starts

        or

        C3 closes -> C4 starts
        """

        setup.htf_count += 1

        # --------------------------------------------------
        # C2 JUST CLOSED
        # --------------------------------------------------
        if not setup.is_post_c2:
            result = start_post_c2_phase(
                setup=setup,
                completed_c2=completed_htf,
                c3_open=current_candle.open,
                c3_start_time=current_candle.timestamp,
                candles=self.ltf_candles,
            )

            return result

        # --------------------------------------------------
        # C3 JUST CLOSED
        # --------------------------------------------------
        if setup.is_post_c2:
            # Pine removes the setup when C3 finishes
            # without CISD confirmation.
            if (
                not setup.cisd_triggered
                or setup.is_invalid
            ):
                return None

            c4_end_time = self._get_htf_end_time(
                current_candle.timestamp
            )

            setup = start_c4_phase(
                setup=setup,
                completed_c3=completed_htf,
                c4_open=current_candle.open,
                c4_start_time=current_candle.timestamp,
                c4_end_time=c4_end_time,
            )

            self.completed_setups.append(
                setup
            )

            # Once moved to history/C4,
            # it is no longer a live C2/C3 setup.
            return None

        return setup

    def _handle_htf_transition(
        self,
        completed_htf: Candle,
        current_candle: Candle,
    ) -> None:
        """
        Handle C2 -> C3 and C3 -> C4
        for both directions.
        """

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
    ) -> tuple[Setup | None, bool]:
        """
        Returns:

        setup
        replacement_required
        """

        # --------------------------------------------------
        # C2
        # --------------------------------------------------
        if not setup.is_post_c2:
            setup = update_c2_setup(
                setup=setup,
                candles=self.ltf_candles,
                current_index=current_index,
            )

            return setup, False

        # --------------------------------------------------
        # C3 / POST-C2
        # --------------------------------------------------
        post_c2_result = update_post_c2_setup(
            setup=setup,
            candles=self.ltf_candles,
            current_index=current_index,
        )

        if post_c2_result.replacement_required:
            # Remove current setup.
            #
            # Later in the SAME on_candle() call,
            # _create_new_setups() can create the
            # replacement against the completed C2.
            return None, True

        return (
            post_c2_result.setup,
            False,
        )

    def _update_existing_setups(
        self,
        current_index: int,
    ) -> None:
        """
        Update live C2/C3 setups using the newest
        lower-timeframe candle.
        """

        if self.live_bearish is not None:
            (
                self.live_bearish,
                _,
            ) = self._update_one_live_setup(
                setup=self.live_bearish,
                current_index=current_index,
            )

        if self.live_bullish is not None:
            (
                self.live_bullish,
                _,
            ) = self._update_one_live_setup(
                setup=self.live_bullish,
                current_index=current_index,
            )

    # ==================================================
    # C4 UPDATES
    # ==================================================

    def _update_completed_setups(
        self,
        current_candle: Candle,
    ) -> None:
        """
        Setups that finished C3 can still have an
        active C4 entry zone.

        Update C4 invalidation while price develops.
        """

        for setup in self.completed_setups:
            if setup.c4_zone_set:
                update_c4_invalidation(
                    setup=setup,
                    current_candle=current_candle,
                )

    # ==================================================
    # NEW SWEEPS
    # ==================================================

    def _create_new_setups(
        self,
        current_candle: Candle,
        current_index: int,
    ) -> None:
        """
        Look for fresh sweeps of the latest
        completed HTF candle.
        """

        if not self.completed_htf_candles:
            return

        previous_htf = (
            self.completed_htf_candles[-1]
        )

        previous_htf_index = (
            len(self.completed_htf_candles)
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
            and candidates.bearish is not None
        ):
            self.live_bearish = (
                self._initialize_cisd(
                    setup=candidates.bearish,
                    current_index=current_index,
                )
            )

        # --------------------------------------------------
        # BULLISH
        # --------------------------------------------------
        if (
            self.live_bullish is None
            and candidates.bullish is not None
        ):
            self.live_bullish = (
                self._initialize_cisd(
                    setup=candidates.bullish,
                    current_index=current_index,
                )
            )

    # ==================================================
    # MAIN ENGINE ENTRY POINT
    # ==================================================

    def on_candle(
        self,
        candle: Candle,
    ) -> EngineSnapshot:
        """
        Feed one new 5m / 15m candle
        into the Fractal engine.
        """

        # --------------------------------------------------
        # 1. STORE LTF CANDLE
        # --------------------------------------------------
        self.ltf_candles.append(
            candle
        )

        current_index = (
            len(self.ltf_candles)
            - 1
        )

        # --------------------------------------------------
        # 2. UPDATE HTF CANDLE
        # --------------------------------------------------
        completed_htf, developing_htf = (
            self.htf_builder.update(
                candle
            )
        )

        # --------------------------------------------------
        # 3. NEW HTF PERIOD
        # --------------------------------------------------
        if completed_htf is not None:
            self.completed_htf_candles.append(
                completed_htf
            )

            # IMPORTANT:
            # Transition C2/C3 using the HTF candle
            # that just finished BEFORE processing
            # the new candle as part of C3/C4.
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
        # 5. UPDATE C4 SETUPS
        # --------------------------------------------------
        self._update_completed_setups(
            current_candle=candle,
        )

        # --------------------------------------------------
        # 6. LOOK FOR NEW SWEEPS
        # --------------------------------------------------
        self._create_new_setups(
            current_candle=candle,
            current_index=current_index,
        )

        previous_completed_htf = None

        if self.completed_htf_candles:
            previous_completed_htf = (
                self.completed_htf_candles[-1]
            )

        # --------------------------------------------------
        # 7. RETURN CURRENT STATE
        # --------------------------------------------------
        return EngineSnapshot(
            bar_index=current_index,
            lower_timeframe=self.lower_timeframe,
            higher_timeframe=self.higher_timeframe,
            developing_htf=developing_htf,
            previous_completed_htf=previous_completed_htf,
            bearish_setup=self.live_bearish,
            bullish_setup=self.live_bullish,
            completed_setups=tuple(
                self.completed_setups
            ),
        )