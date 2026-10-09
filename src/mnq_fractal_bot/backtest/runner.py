from collections.abc import Sequence
from dataclasses import dataclass

from mnq_fractal_bot.backtest.audit import (
    SignalAudit,
)

from mnq_fractal_bot.backtest.cost_report import (
    ExecutionCostSummary,
    build_execution_cost_summary,
)

from mnq_fractal_bot.backtest.report import (
    BacktestStats,
    TradeLogRow,
    build_backtest_stats,
    build_trade_log,
)

from mnq_fractal_bot.execution.bot_runner import (
    BotRunner,
    BotSnapshot,
    RecordedBrokerEvent,
)

from mnq_fractal_bot.execution.costs import (
    ExecutionCostConfig,
)

from mnq_fractal_bot.execution.paper_broker import (
    ClosedTrade,
)

from mnq_fractal_bot.models.candle import Candle

from mnq_fractal_bot.risk.trade_filter import (
    TradeFilterConfig,
)


@dataclass(frozen=True)
class BacktestResult:
    candle_count: int

    trades: tuple[
        ClosedTrade,
        ...
    ]

    trade_log: tuple[
        TradeLogRow,
        ...
    ]

    signal_audits: tuple[
        SignalAudit,
        ...
    ]

    broker_events: tuple[
        RecordedBrokerEvent,
        ...
    ]

    stats: BacktestStats

    # Gross P&L converted into estimated
    # net P&L after execution costs.
    execution_cost_summary: (
        ExecutionCostSummary
    )

    final_snapshot: BotSnapshot | None


class BacktestRunner:
    def __init__(
        self,
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
                "Starting balance must be "
                "greater than zero."
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
    # VALIDATE DATA
    # ==================================================

    def _validate_candles(
        self,
        candles: Sequence[Candle],
    ) -> None:
        for index in range(
            1,
            len(candles),
        ):
            previous = (
                candles[index - 1]
            )

            current = (
                candles[index]
            )

            if (
                current.timestamp
                <= previous.timestamp
            ):
                raise ValueError(
                    "Candles must be in strictly "
                    "increasing timestamp order."
                )

    # ==================================================
    # RUN
    # ==================================================

    def run(
        self,
        candles: Sequence[Candle],
    ) -> BacktestResult:
        candles = list(
            candles
        )

        self._validate_candles(
            candles
        )

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
        )

        final_snapshot = None

        # ==================================================
        # FEED ALL CANDLES
        # ==================================================

        for candle in candles:
            final_snapshot = (
                bot.on_candle(
                    candle
                )
            )

        # ==================================================
        # COLLECT RAW RESULTS
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
        # ORIGINAL GROSS STATISTICS
        # ==================================================

        stats = build_backtest_stats(
            trades=trades,

            starting_balance=(
                self.starting_balance
            ),
        )

        trade_log = build_trade_log(
            trades=trades,

            starting_balance=(
                self.starting_balance
            ),
        )

        # ==================================================
        # EXECUTION COSTS
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
        # RESULT
        # ==================================================

        return BacktestResult(
            candle_count=len(
                candles
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