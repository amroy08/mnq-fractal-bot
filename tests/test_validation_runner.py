from datetime import (
    datetime,
    timedelta,
    timezone,
)

from types import SimpleNamespace

from mnq_fractal_bot.backtest.validation_runner import (
    ChronologicalValidationRunner,
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


def make_candles(
    count: int,
):
    candles = []

    for index in range(
        count
    ):
        candles.append(
            Candle(
                timestamp=(
                    START
                    + timedelta(
                        minutes=(
                            index * 5
                        )
                    )
                ),

                open=100,
                high=101,
                low=99,
                close=100,

                volume=100,
            )
        )

    return candles


class FakeBroker:
    def __init__(
        self,
    ):
        self.closed_trades = []


class FakeBotRunner:
    instances = []

    def __init__(
        self,
        **kwargs,
    ):
        self.kwargs = kwargs

        self.trading_enabled = (
            kwargs.get(
                "trading_enabled",
                True,
            )
        )

        self.calls = []

        self.enable_calls = []

        self.broker = FakeBroker()

        self.signal_audits = []

        self.broker_event_history = []

        FakeBotRunner.instances.append(
            self
        )

    def set_trading_enabled(
        self,
        enabled: bool,
    ):
        self.trading_enabled = (
            enabled
        )

        self.enable_calls.append(
            enabled
        )

    def on_candle(
        self,
        candle,
    ):
        self.calls.append(
            (
                candle.timestamp,
                self.trading_enabled,
            )
        )

        return SimpleNamespace(
            timestamp=(
                candle.timestamp
            )
        )


def test_70_30_validation_gate(
    monkeypatch,
):
    FakeBotRunner.instances.clear()

    monkeypatch.setattr(
        (
            "mnq_fractal_bot.backtest."
            "validation_runner.BotRunner"
        ),
        FakeBotRunner,
    )

    runner = (
        ChronologicalValidationRunner(
            validation_fraction=0.30,
        )
    )

    result = runner.run(
        make_candles(
            10
        )
    )

    bot = (
        FakeBotRunner.instances[
            0
        ]
    )

    assert len(
        bot.calls
    ) == 10

    warmup_calls = (
        bot.calls[
            :7
        ]
    )

    validation_calls = (
        bot.calls[
            7:
        ]
    )

    assert all(
        enabled is False
        for _, enabled
        in warmup_calls
    )

    assert all(
        enabled is True
        for _, enabled
        in validation_calls
    )

    assert (
        result.backtest
        .candle_count
        == 3
    )


def test_runner_uses_one_bot_instance(
    monkeypatch,
):
    FakeBotRunner.instances.clear()

    monkeypatch.setattr(
        (
            "mnq_fractal_bot.backtest."
            "validation_runner.BotRunner"
        ),
        FakeBotRunner,
    )

    runner = (
        ChronologicalValidationRunner(
            validation_fraction=0.30,
        )
    )

    runner.run(
        make_candles(
            20
        )
    )

    assert len(
        FakeBotRunner.instances
    ) == 1


def test_trading_starts_disabled(
    monkeypatch,
):
    FakeBotRunner.instances.clear()

    monkeypatch.setattr(
        (
            "mnq_fractal_bot.backtest."
            "validation_runner.BotRunner"
        ),
        FakeBotRunner,
    )

    runner = (
        ChronologicalValidationRunner()
    )

    runner.run(
        make_candles(
            10
        )
    )

    bot = (
        FakeBotRunner.instances[
            0
        ]
    )

    assert (
        bot.kwargs[
            "trading_enabled"
        ]
        is False
    )

    assert (
        bot.enable_calls
        == [True]
    )


def test_custom_80_20_split(
    monkeypatch,
):
    FakeBotRunner.instances.clear()

    monkeypatch.setattr(
        (
            "mnq_fractal_bot.backtest."
            "validation_runner.BotRunner"
        ),
        FakeBotRunner,
    )

    runner = (
        ChronologicalValidationRunner(
            validation_fraction=0.20,
        )
    )

    result = runner.run(
        make_candles(
            100
        )
    )

    assert len(
        result.split
        .warmup_candles
    ) == 80

    assert len(
        result.split
        .validation_candles
    ) == 20

    assert (
        result.backtest
        .candle_count
        == 20
    )


def test_empty_validation_trade_results(
    monkeypatch,
):
    FakeBotRunner.instances.clear()

    monkeypatch.setattr(
        (
            "mnq_fractal_bot.backtest."
            "validation_runner.BotRunner"
        ),
        FakeBotRunner,
    )

    runner = (
        ChronologicalValidationRunner(
            starting_balance=25_000,
        )
    )

    result = runner.run(
        make_candles(
            10
        )
    )

    assert (
        result.backtest
        .stats
        .total_trades
        == 0
    )

    assert (
        result.backtest
        .execution_cost_summary
        .net_pnl
        == 0
    )

    assert (
        result.backtest
        .execution_cost_summary
        .net_ending_balance
        == 25_000
    )