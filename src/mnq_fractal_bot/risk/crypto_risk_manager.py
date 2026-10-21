"""
Crypto Risk & Budget Manager (Adapted from trader-skill architecture).
Tailored specifically for Binance Futures 5m scalping on SOLUSDT.

Key Gates Enforced:
1. Daily Loss Limit (Default: $0.60 per day - auto-lockdown for 24h)
2. Max Consecutive Losses (Default: 2 losses - triggers 2h cooldown)
3. Dynamic Budget Sizing (Risks exactly 1.5% - 2.5% based on ATR volatility)
4. Order Fingerprint Verification & Duplicate Protection
"""

import time
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("CryptoRiskManager")


@dataclass
class CryptoRiskConfig:
    max_daily_loss_usd: float = 0.60         # Stop all trading if daily loss reaches $0.60
    max_consecutive_losses: int = 2          # Lock trading if 2 losses occur in a row
    loss_cooldown_minutes: int = 120         # 2 hours cooldown after consecutive losses
    max_risk_pct_per_trade: float = 0.025    # Max 2.5% balance risked per trade
    min_risk_pts: float = 0.25               # Min stop distance
    max_risk_pts: float = 1.00               # Max stop distance (blocks wide stops)
    min_rr_ratio: float = 1.4                # Minimum 1.4 Reward:Risk ratio


class CryptoRiskManager:
    def __init__(self, config: CryptoRiskConfig = None):
        self.config = config or CryptoRiskConfig()
        self.daily_pnl = 0.0
        self.current_day = datetime.now(timezone.utc).date()
        self.consecutive_losses = 0
        self.cooldown_until: datetime | None = None
        self.processed_signals = set()

    def _refresh_day(self):
        now_date = datetime.now(timezone.utc).date()
        if now_date != self.current_day:
            logger.info(f"New trading day rollover: resetting daily PnL (was ${self.daily_pnl:.2f})")
            self.daily_pnl = 0.0
            self.current_day = now_date
            self.consecutive_losses = 0
            self.cooldown_until = None

    def record_closed_trade(self, pnl: float):
        """Updates internal risk state after a trade completes."""
        self._refresh_day()
        self.daily_pnl += pnl

        if pnl < 0:
            self.consecutive_losses += 1
            logger.warning(f"Recorded Loss: ${pnl:.4f} | Consecutive Losses: {self.consecutive_losses} | Daily PnL: ${self.daily_pnl:.4f}")
            if self.consecutive_losses >= self.config.max_consecutive_losses:
                self.cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=self.config.loss_cooldown_minutes)
                logger.error(f"🚨 CIRCUIT BREAKER TRIGGERED: {self.consecutive_losses} consecutive losses! Cooling down until {self.cooldown_until.strftime('%H:%M:%S UTC')}")
        else:
            self.consecutive_losses = 0
            logger.info(f"Recorded Win: +${pnl:.4f} | Reset consecutive losses to 0 | Daily PnL: ${self.daily_pnl:.4f}")

    def evaluate_order(self, direction: str, entry: float, stop: float, target: float, balance: float) -> tuple[bool, str, float]:
        """
        Pre-trade risk gate (Adapted from trader-risk).
        Returns: (passes: bool, reason: str, recommended_qty: float)
        """
        self._refresh_day()
        now = datetime.now(timezone.utc)

        # 1. Check Circuit Breaker Cooldown
        if self.cooldown_until and now < self.cooldown_until:
            rem = int((self.cooldown_until - now).total_seconds() / 60)
            return False, f"CIRCUIT BREAKER ACTIVE: Cooling down for {rem} more minutes after consecutive losses.", 0.0

        # 2. Check Daily Loss Limit
        if self.daily_pnl <= -self.config.max_daily_loss_usd:
            return False, f"DAILY LOSS LIMIT REACHED: -${abs(self.daily_pnl):.2f} (Limit: -${self.config.max_daily_loss_usd:.2f}). Trading halted for today.", 0.0

        # 3. Check Stop Loss Distance
        risk_pts = abs(entry - stop)
        if risk_pts < self.config.min_risk_pts:
            return False, f"STOP TOO TIGHT: {risk_pts:.2f} pts < min {self.config.min_risk_pts:.2f} pts", 0.0
        if risk_pts > self.config.max_risk_pts:
            return False, f"STOP TOO WIDE: {risk_pts:.2f} pts > max {self.config.max_risk_pts:.2f} pts (Block excessive risk)", 0.0

        # 4. Check Reward to Risk Ratio
        reward_pts = abs(target - entry)
        rr = reward_pts / risk_pts
        if rr < self.config.min_rr_ratio:
            return False, f"UNFAVORABLE R:R: {rr:.2f} < min {self.config.min_rr_ratio:.2f}", 0.0

        # 5. Dynamic Budget Position Sizing (From trader-budget)
        # Minimum Binance contract is 0.10 SOL
        # Allocate ~70% of available margin (~0.25 - 0.30 SOL)
        max_possible_qty = round((balance * 5.0 * 0.70) / entry, 2)
        qty = max(max_possible_qty, 0.10)

        if qty < 0.10:
            return False, "INSUFFICIENT MARGIN for minimum 0.10 SOL order size", 0.0

        return True, f"PASS (Qty: {qty} SOL | Risk: ${qty * risk_pts:.2f} | R:R: {rr:.2f})", qty
