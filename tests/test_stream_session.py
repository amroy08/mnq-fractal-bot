from datetime import datetime, timedelta, timezone

from mnq_fractal_bot.execution.bot_runner import BotRunner
from mnq_fractal_bot.execution.stream_session import PaperStreamSession
from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.risk.trade_filter import TradeFilterConfig


def make_candle(ts: datetime, price: float = 100.0) -> Candle:
    return Candle(
        timestamp=ts,
        open=price,
        high=price + 2.0,
        low=price - 2.0,
        close=price,
        volume=10,
    )


def test_stream_session_warmup_gate():
    runner = BotRunner(
        trade_filter_config=TradeFilterConfig(allow_c3=True, allow_c4=False),
        trading_enabled=False,
    )

    session = PaperStreamSession(
        bot_runner=runner,
        warmup_candles=5,
    )

    start = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)
    candles = [
        make_candle(start + timedelta(minutes=5 * i))
        for i in range(10)
    ]

    events = session.stream_all(candles)

    assert len(events) == 10
    # First 5 were warmup
    assert events[0].is_live_step is False
    assert events[4].is_live_step is False
    # Next 5 were live
    assert events[5].is_live_step is True
    assert events[9].is_live_step is True
    assert session.candles_processed == 10


def test_stream_session_callback():
    runner = BotRunner()
    received = []

    session = PaperStreamSession(
        bot_runner=runner,
        warmup_candles=0,
        on_event=lambda ev: received.append(ev.candle.timestamp),
    )

    start = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)
    candles = [
        make_candle(start + timedelta(minutes=5 * i))
        for i in range(3)
    ]

    session.stream_all(candles)
    assert len(received) == 3
    assert received[0] == candles[0].timestamp
