from datetime import (
    datetime,
    timedelta,
    timezone,
)

from types import SimpleNamespace

from mnq_fractal_bot.execution.bot_runner import (
    BotRunner,
)

from mnq_fractal_bot.models.candle import (
    Candle,
)


START = datetime(
    2026,
    1,
    1,
    0,
    0,
    tzinfo=timezone.utc,
)


def make_candle(
    minutes: int = 0,
) -> Candle:
    return Candle(
        timestamp=(
            START
            + timedelta(
                minutes=minutes
            )
        ),

        open=100,
        high=101,
        low=99,
        close=100,

        volume=100,
    )


class FakeEngine:
    def __init__(self):
        self.calls = 0

        self.higher_timeframe = (
            "1h"
        )

    def on_candle(
        self,
        candle,
    ):
        self.calls += 1

        return SimpleNamespace(
            selected_setup=None,
            trade_plan=None,
        )


class FakeBroker:
    def __init__(self):
        self.calls = 0

        self.pending_order = None
        self.position = None

        self.closed_trades = []

    def on_candle(
        self,
        candle,
    ):
        self.calls += 1

        return None

    def cancel_pending_order(
        self,
    ):
        return None

    def submit_trade_plan(
        self,
        plan,
        signal_id,
        expires_at,
    ):
        raise AssertionError(
            "Order should not "
            "be submitted."
        )


def test_warmup_runs_engine_but_not_broker():
    bot = BotRunner(
        trading_enabled=False,
    )

    engine = FakeEngine()
    broker = FakeBroker()

    bot.engine = engine
    bot.broker = broker

    snapshot = bot.on_candle(
        make_candle()
    )

    assert engine.calls == 1

    assert broker.calls == 0

    assert (
        snapshot.order_submitted
        is False
    )

    assert (
        snapshot.closed_trade_count
        == 0
    )

    assert (
        snapshot.audit_count
        == 0
    )

    assert (
        snapshot.broker_event_count
        == 0
    )


def test_enabling_trading_starts_broker():
    bot = BotRunner(
        trading_enabled=False,
    )

    engine = FakeEngine()
    broker = FakeBroker()

    bot.engine = engine
    bot.broker = broker

    # Warm-up candle.
    bot.on_candle(
        make_candle(
            minutes=0
        )
    )

    assert engine.calls == 1
    assert broker.calls == 0

    # Validation begins.
    bot.set_trading_enabled(
        True
    )

    bot.on_candle(
        make_candle(
            minutes=5
        )
    )

    # Engine never reset.
    assert engine.calls == 2

    # Broker begins only now.
    assert broker.calls == 1


def test_default_behavior_keeps_trading_enabled():
    bot = BotRunner()

    engine = FakeEngine()
    broker = FakeBroker()

    bot.engine = engine
    bot.broker = broker

    bot.on_candle(
        make_candle()
    )

    assert (
        bot.trading_enabled
        is True
    )

    assert engine.calls == 1
    assert broker.calls == 1


def test_warmup_signal_is_suppressed_after_enable():
    bot = BotRunner(
        trading_enabled=False,
    )

    engine = FakeEngine()
    broker = FakeBroker()

    bot.engine = engine
    bot.broker = broker

    fake_setup = object()
    fake_plan = object()

    def fake_active_signal(
        snapshot,
    ):
        return (
            fake_setup,
            fake_plan,
            "warmup-signal-1",
        )

    bot._get_active_signal = (
        fake_active_signal
    )

    # Signal exists during warm-up.
    bot.on_candle(
        make_candle(
            minutes=0
        )
    )

    assert (
        "warmup-signal-1"
        in bot.suppressed_signal_ids
    )

    assert len(
        bot.signal_audits
    ) == 0

    # Turn trading on.
    bot.set_trading_enabled(
        True
    )

    # Same signal is still active.
    #
    # It must NOT suddenly become
    # a validation trade.
    snapshot = bot.on_candle(
        make_candle(
            minutes=5
        )
    )

    assert (
        snapshot.order_submitted
        is False
    )

    assert len(
        bot.signal_audits
    ) == 0