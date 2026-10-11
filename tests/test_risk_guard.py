from datetime import datetime, timezone
import pytest

from mnq_fractal_bot.risk.risk_guard import RiskGuard, RiskGuardConfig


def test_risk_guard_allows_initially():
    guard = RiskGuard(RiskGuardConfig(max_daily_loss=500.0))
    now = datetime(2026, 10, 11, 14, 0, tzinfo=timezone.utc)
    res = guard.check_new_order(now)
    assert res.allowed is True
    assert res.reason == "ALLOWED"


def test_risk_guard_blocks_on_daily_loss():
    guard = RiskGuard(RiskGuardConfig(max_daily_loss=500.0))
    t1 = datetime(2026, 10, 11, 14, 0, tzinfo=timezone.utc)
    guard.on_trade_closed(-550.0, t1)

    t2 = datetime(2026, 10, 11, 15, 0, tzinfo=timezone.utc)
    res = guard.check_new_order(t2)
    assert res.allowed is False
    assert "DAILY_LOSS_LIMIT_REACHED" in res.reason

    # On the next day, daily loss resets
    next_day = datetime(2026, 10, 12, 9, 30, tzinfo=timezone.utc)
    res_next = guard.check_new_order(next_day)
    assert res_next.allowed is True


def test_risk_guard_blocks_on_max_trailing_drawdown():
    guard = RiskGuard(
        RiskGuardConfig(max_daily_loss=None, max_total_drawdown=1000.0, max_consecutive_losses=None),
        starting_balance=25000.0,
    )
    # Win $500 -> peak $25,500
    guard.on_trade_closed(500.0, datetime(2026, 10, 11, 10, 0, tzinfo=timezone.utc))
    assert guard.peak_balance == 25500.0

    # Lose $1100 -> balance $24,400 (drawdown from peak $25,500 is $1,100 > $1,000)
    guard.on_trade_closed(-1100.0, datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc))

    res = guard.check_new_order(datetime(2026, 10, 11, 13, 0, tzinfo=timezone.utc))
    assert res.allowed is False
    assert "MAX_DRAWDOWN_LIMIT_REACHED" in res.reason


def test_risk_guard_consecutive_loss_breaker():
    guard = RiskGuard(RiskGuardConfig(max_daily_loss=None, max_total_drawdown=None, max_consecutive_losses=2))
    t = datetime(2026, 10, 11, 10, 0, tzinfo=timezone.utc)
    guard.on_trade_closed(-50.0, t)
    assert guard.check_new_order(t).allowed is True

    guard.on_trade_closed(-50.0, t)
    # 2 consecutive losses reached
    res = guard.check_new_order(t)
    assert res.allowed is False
    assert "CONSECUTIVE_LOSS_LIMIT_REACHED" in res.reason

    # Reset on win
    guard.on_trade_closed(100.0, t)
    assert guard.check_new_order(t).allowed is True
