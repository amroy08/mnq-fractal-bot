from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from mnq_fractal_bot.backtest.report import (
    build_backtest_stats,
    build_trade_log,
)

from mnq_fractal_bot.execution.paper_broker import (
    ClosedTrade,
)


NOW = datetime(
    2026,
    10,
    9,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_trade(
    number,
    pnl,
):
    direction = (
        "LONG"
        if number % 2
        else "SHORT"
    )

    entry_price = 100

    if direction == "LONG":
        points = pnl / 2
        exit_price = (
            entry_price
            + points
        )

        stop_price = 90
        target_price = 120

    else:
        points = pnl / 2

        exit_price = (
            entry_price
            - points
        )

        stop_price = 110
        target_price = 80

    return ClosedTrade(
        signal_id=f"trade-{number}",

        direction=direction,

        entry_price=entry_price,
        exit_price=exit_price,

        stop_price=stop_price,
        target_price=target_price,

        quantity=1,

        entry_time=(
            NOW
            + timedelta(
                minutes=number * 10
            )
        ),

        exit_time=(
            NOW
            + timedelta(
                minutes=number * 10 + 5
            )
        ),

        exit_reason=(
            "TARGET"
            if pnl > 0
            else "STOPPED"
        ),

        points=points,
        gross_pnl=pnl,
    )


def test_empty_backtest_stats():
    stats = build_backtest_stats(
        trades=[],
        starting_balance=25_000,
    )

    assert stats.total_trades == 0

    assert stats.wins == 0
    assert stats.losses == 0

    assert stats.win_rate_pct == 0

    assert stats.gross_pnl == 0

    assert stats.max_drawdown == 0

    assert stats.ending_balance == 25_000


def test_backtest_performance_metrics():
    trades = [
        make_trade(1, 20),
        make_trade(2, -10),
        make_trade(3, -30),
        make_trade(4, 40),
    ]

    stats = build_backtest_stats(
        trades=trades,
        starting_balance=1000,
    )

    assert stats.total_trades == 4

    assert stats.wins == 2
    assert stats.losses == 2

    assert stats.win_rate_pct == 50

    assert stats.gross_profit == 60
    assert stats.gross_loss == -40

    assert stats.gross_pnl == 20

    assert stats.average_trade == 5

    assert stats.average_win == 30
    assert stats.average_loss == -20

    assert stats.profit_factor == 1.5

    assert stats.ending_balance == 1020


def test_max_drawdown_is_calculated():
    trades = [
        make_trade(1, 20),
        make_trade(2, -10),
        make_trade(3, -30),
        make_trade(4, 40),
    ]

    stats = build_backtest_stats(
        trades=trades,
        starting_balance=1000,
    )

    # Equity:
    #
    # Start = 1000
    # +20   = 1020 peak
    # -10   = 1010
    # -30   = 980
    #
    # Drawdown:
    #
    # 1020 -> 980 = $40

    assert stats.max_drawdown == 40

    assert stats.max_drawdown_pct == pytest.approx(
        (40 / 1020) * 100
    )


def test_trade_log_tracks_running_equity():
    trades = [
        make_trade(1, 20),
        make_trade(2, -10),
    ]

    log = build_trade_log(
        trades=trades,
        starting_balance=1000,
    )

    assert len(log) == 2

    assert (
        log[0].trade_number
        == 1
    )

    assert (
        log[0].running_pnl
        == 20
    )

    assert (
        log[0].equity
        == 1020
    )

    assert (
        log[1].running_pnl
        == 10
    )

    assert (
        log[1].equity
        == 1010
    )


def test_invalid_starting_balance_is_rejected():
    with pytest.raises(ValueError):
        build_backtest_stats(
            trades=[],
            starting_balance=0,
        )