from collections.abc import Sequence
from dataclasses import dataclass

from mnq_fractal_bot.backtest.cost_report import (
    build_execution_cost_summary,
)

from mnq_fractal_bot.backtest.report import (
    build_backtest_stats,
    build_trade_log,
)

from mnq_fractal_bot.backtest.runner import (
    BacktestResult,
)

from mnq_fractal_bot.backtest.validation import (
    ChronologicalSplit,
    split_chronologically,
)

from mnq_fractal_bot.execution.bot_runner import (
    BotRunner,
)

from mnq_fractal_bot.execution.costs import (
    ExecutionCostConfig,
)

from mnq_fractal_bot.models.candle import (
    Candle,
)

from mnq_fractal_bot.risk.trade_filter import (
    TradeFilterConfig,
)


@dataclass(frozen=True)
class ChronologicalValidationResult:
    split: ChronologicalSplit

    backtest: BacktestResult


class ChronologicalValidationRunner:
    def __init__(
        self,
        validation_fraction: float = 0.30,
        lower_timeframe: str = "5m",
        tick_size: float = 0.25,
        sl_buffer_ticks: int = 2,
        point_value: float = 2.0,
        starting_balance: float = 25_000.0,
        trade_filter_config: (
            TradeFilterConfig | None
        ) = None,
        execution_cost_config: (
            ExecutionCostConfig | None
        ) = None,
    ):
        if starting_balance <= 0:
            raise ValueError(
                "starting_balance must be "
                "greater than zero."
            )

        self.validation_fraction = (
            validation_fraction
        )

        self.lower_timeframe = (
            lower_timeframe
        )

        self.tick_size = (
            tick_size
        )

        self.sl_buffer_ticks = (
            sl_buffer_ticks
        )

        self.point_value = (
            point_value
        )

        self.starting_balance = (
            starting_balance
        )

        self.trade_filter_config = (
            trade_filter_config
            if trade_filter_config
            is not None
            else TradeFilterConfig()
        )

        self.execution_cost_config = (
            execution_cost_config
            if execution_cost_config
            is not None
            else ExecutionCostConfig(
                tick_size=tick_size,
                point_value=point_value,
            )
        )

    # ==================================================
    # RUN
    # ==================================================

    def run(
        self,
        candles: Sequence[Candle],
    ) -> ChronologicalValidationResult:

        # ==================================================
        # 1. CHRONOLOGICAL SPLIT
        # ==================================================

        split = (
            split_chronologically(
                candles=candles,

                validation_fraction=(
                    self.validation_fraction
                ),
            )
        )

        # ==================================================
        # 2. CREATE ONE BOT ONLY
        #
        # Trading begins disabled.
        #
        # IMPORTANT:
        # We do NOT create a second engine when
        # validation begins.
        # ==================================================

        bot = BotRunner(
            lower_timeframe=(
                self.lower_timeframe
            ),

            tick_size=(
                self.tick_size
            ),

            sl_buffer_ticks=(
                self.sl_buffer_ticks
            ),

            point_value=(
                self.point_value
            ),

            trade_filter_config=(
                self.trade_filter_config
            ),

            trading_enabled=False,
        )

        final_snapshot = None

        # ==================================================
        # 3. WARM-UP PERIOD
        #
        # FractalEngine:
        #     ON
        #
        # Broker:
        #     OFF
        #
        # Signal audit:
        #     OFF
        #
        # Orders:
        #     OFF
        # ==================================================

        for candle in (
            split.warmup_candles
        ):
            final_snapshot = (
                bot.on_candle(
                    candle
                )
            )

        # ==================================================
        # 4. ENABLE VALIDATION TRADING
        #
        # Same BotRunner.
        # Same FractalEngine.
        # Same historical state.
        # ==================================================

        bot.set_trading_enabled(
            True
        )

        # ==================================================
        # 5. VALIDATION PERIOD
        # ==================================================

        for candle in (
            split.validation_candles
        ):
            final_snapshot = (
                bot.on_candle(
                    candle
                )
            )

        # ==================================================
        # 6. VALIDATION TRADES ONLY
        #
        # Warm-up was broker-disabled,
        # therefore all trades here belong
        # to the validation period.
        # ==================================================

        trades = tuple(
            bot.broker.closed_trades
        )

        signal_audits = tuple(
            bot.signal_audits
        )

        broker_events = tuple(
            bot.broker_event_history
        )

        # ==================================================
        # 7. GROSS STATISTICS
        # ==================================================

        stats = (
            build_backtest_stats(
                trades=trades,

                starting_balance=(
                    self.starting_balance
                ),
            )
        )

        trade_log = (
            build_trade_log(
                trades=trades,

                starting_balance=(
                    self.starting_balance
                ),
            )
        )

        # ==================================================
        # 8. EXECUTION COSTS
        # ==================================================

        execution_cost_summary = (
            build_execution_cost_summary(
                trades=trades,

                config=(
                    self.execution_cost_config
                ),

                starting_balance=(
                    self.starting_balance
                ),

                quantity=1,
            )
        )

        # ==================================================
        # 9. NORMAL BACKTEST RESULT
        #
        # candle_count intentionally represents
        # ONLY the validation period.
        # ==================================================

        backtest = BacktestResult(
            candle_count=len(
                split.validation_candles
            ),

            trades=trades,

            trade_log=trade_log,

            signal_audits=(
                signal_audits
            ),

            broker_events=(
                broker_events
            ),

            stats=stats,

            execution_cost_summary=(
                execution_cost_summary
            ),

            final_snapshot=(
                final_snapshot
            ),
        )

        # ==================================================
        # 10. FINAL VALIDATION RESULT
        # ==================================================

        return ChronologicalValidationResult(
            split=split,

            backtest=backtest,
        )