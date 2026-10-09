from collections.abc import Sequence
from dataclasses import dataclass

from mnq_fractal_bot.backtest.report import (
    BacktestStats,
    TradeLogRow,
    build_backtest_stats,
    build_trade_log,
)

from mnq_fractal_bot.execution.bot_runner import (
    BotRunner,
    BotSnapshot,
)

from mnq_fractal_bot.execution.paper_broker import (
    ClosedTrade,
)

from mnq_fractal_bot.models.candle import Candle


@dataclass(frozen=True)
class BacktestResult:
    candle_count: int

    trades: tuple[ClosedTrade, ...]

    trade_log: tuple[
        TradeLogRow,
        ...
    ]

    stats: BacktestStats

    final_snapshot: BotSnapshot | None


class BacktestRunner:
    def __init__(
        self,
        lower_timeframe: str = "5m",
        tick_size: float = 0.25,
        sl_buffer_ticks: int = 2,
        point_value: float = 2.0,
        starting_balance: float = 25_000.0,
    ):
        if starting_balance <= 0:
            raise ValueError(
                "Starting balance must be greater than zero."
            )

        self.lower_timeframe = (
            lower_timeframe
        )

        self.tick_size = tick_size

        self.sl_buffer_ticks = (
            sl_buffer_ticks
        )

        self.point_value = (
            point_value
        )

        self.starting_balance = (
            starting_balance
        )

    # ==================================================
    # VALIDATE DATA ORDER
    # ==================================================

    def _validate_candles(
        self,
        candles: Sequence[Candle],
    ) -> None:
        """
        Backtests MUST run chronologically.

        We deliberately do NOT automatically sort
        the data because silently fixing bad market
        data can hide data-quality problems.
        """

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

        # Fresh bot for every backtest.
        #
        # This prevents previous backtest state
        # leaking into a new run.
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
        )

        final_snapshot = None

        # ==================================================
        # FEED MARKET DATA ONE CANDLE AT A TIME
        # ==================================================

        for candle in candles:
            final_snapshot = (
                bot.on_candle(
                    candle
                )
            )

        trades = tuple(
            bot.broker.closed_trades
        )

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

        return BacktestResult(
            candle_count=len(candles),

            trades=trades,

            trade_log=trade_log,

            stats=stats,

            final_snapshot=(
                final_snapshot
            ),
        )