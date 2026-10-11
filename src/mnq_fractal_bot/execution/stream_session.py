from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterator, Sequence

from mnq_fractal_bot.execution.bot_runner import BotRunner, BotSnapshot
from mnq_fractal_bot.models.candle import Candle


@dataclass(frozen=True)
class StreamEvent:
    candle: Candle
    snapshot: BotSnapshot
    is_live_step: bool


class PaperStreamSession:
    """
    Simulated streaming session for forward paper testing.

    Feeds candles sequentially (simulating 5m bar close delivery in real time),
    enforces warmup phase with suppressed execution, then opens the trading
    gate for live execution evaluation.
    """

    def __init__(
        self,
        bot_runner: BotRunner,
        warmup_candles: int = 0,
        on_event: Callable[[StreamEvent], None] | None = None,
    ):
        self.bot_runner = bot_runner
        self.warmup_candles = warmup_candles
        self.on_event = on_event
        self.candles_processed = 0

        # Enforce initial trading gate state
        if self.warmup_candles > 0:
            self.bot_runner.set_trading_enabled(False)
        else:
            self.bot_runner.set_trading_enabled(True)

    def process_candle(self, candle: Candle) -> StreamEvent:
        if candle.timestamp.tzinfo is None:
            raise ValueError("Candle timestamp must include timezone.")

        # Transition from warmup to active forward execution
        if (
            self.candles_processed == self.warmup_candles
            and self.warmup_candles > 0
        ):
            self.bot_runner.set_trading_enabled(True)

        is_live = self.candles_processed >= self.warmup_candles
        snapshot = self.bot_runner.on_candle(candle)
        self.candles_processed += 1

        event = StreamEvent(
            candle=candle,
            snapshot=snapshot,
            is_live_step=is_live,
        )

        if self.on_event is not None:
            self.on_event(event)

        return event

    def stream_all(
        self,
        candle_stream: Iterator[Candle] | Sequence[Candle],
    ) -> list[StreamEvent]:
        events = []
        for candle in candle_stream:
            events.append(self.process_candle(candle))
        return events
