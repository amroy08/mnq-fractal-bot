from collections.abc import Sequence
from dataclasses import dataclass

from mnq_fractal_bot.backtest.audit import (
    SignalAudit,
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

    final_snapshot: BotSnapshot | None


class BacktestRunner:
    def __init__(
        self,
        lower_timeframe: str = "5m",
        tick_size: float = 0.25,
        sl_buffer_ticks: int = 2,
        point_value: float = 2.0,
        starting_balance: float = 25_000.0,
        trade_filter_config: TradeFilterConfig | None = None,
    ):
        if starting_balance <= 0:
            raise ValueError(
                "Starting balance must be greater than zero."
            )

        self.lower_timeframe = lower_timeframe
        self.tick_size = tick_size
        self.sl_buffer_ticks = sl_buffer_ticks
        self.point_value = point_value
        self.starting_balance = starting_balance

        self.trade_filter_config = (
            trade_filter_config
            if trade_filter_config is not None
            else TradeFilterConfig()
        )

    def _validate_candles(
        self,
        candles: Sequence[Candle],
    ) -> None:
        for index in range(
            1,
            len(candles),
        ):
            previous = candles[index - 1]
            current = candles[index]

            if (
                current.timestamp
                <= previous.timestamp
            ):
                raise ValueError(
                    "Candles must be in strictly "
                    "increasing timestamp order."
                )

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

        for candle in candles:
            final_snapshot = (
                bot.on_candle(
                    candle
                )
            )

        trades = tuple(
            bot.broker.closed_trades
        )

        signal_audits = tuple(
            bot.signal_audits
        )

        broker_events = tuple(
            bot.broker_event_history
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

            final_snapshot=(
                final_snapshot
            ),
        )