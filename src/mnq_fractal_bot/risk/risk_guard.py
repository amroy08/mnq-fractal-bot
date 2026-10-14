from dataclasses import dataclass
from datetime import datetime, date


@dataclass(frozen=True)
class RiskGuardConfig:
    max_daily_loss: float | None = 500.0       # Max loss allowed in a single trading day ($)
    max_total_drawdown: float | None = 1500.0  # Max trailing drawdown from peak balance ($)
    max_consecutive_losses: int | None = 3    # Circuit breaker on consecutive losing trades
    max_contracts: int = 1                     # Position size cap (contracts)
    excluded_hours_utc: tuple[int, ...] = ()   # Hours (UTC 0-23) during which new orders are blocked


@dataclass(frozen=True)
class RiskCheckResult:
    allowed: bool
    reason: str


class RiskGuard:
    """
    Capital preservation & prop-firm evaluation guardrails.
    Operates in paper simulation to prevent blowups, enforcing:
    1. Daily loss circuit breaker
    2. Trailing peak drawdown lock
    3. Consecutive loss cool-off
    """

    def __init__(
        self,
        config: RiskGuardConfig | None = None,
        starting_balance: float = 25000.0,
    ):
        self.config = config if config is not None else RiskGuardConfig()
        self.starting_balance = starting_balance
        self.current_balance = starting_balance
        self.peak_balance = starting_balance

        self.current_day: date | None = None
        self.daily_pnl = 0.0
        self.consecutive_losses = 0

    def on_trade_closed(self, pnl: float, exit_time: datetime) -> None:
        trade_date = exit_time.date()

        # Reset daily tracking on day change
        if self.current_day != trade_date:
            self.current_day = trade_date
            self.daily_pnl = 0.0
            self.consecutive_losses = 0

        self.daily_pnl += pnl
        self.current_balance += pnl

        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance

        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def check_new_order(self, current_time: datetime) -> RiskCheckResult:
        current_date = current_time.date()
        if self.current_day != current_date:
            effective_daily_pnl = 0.0
            effective_consecutive_losses = 0
        else:
            effective_daily_pnl = self.daily_pnl
            effective_consecutive_losses = self.consecutive_losses

        # 1. Daily Loss Check
        if (
            self.config.max_daily_loss is not None
            and effective_daily_pnl <= -self.config.max_daily_loss
        ):
            return RiskCheckResult(
                allowed=False,
                reason=f"DAILY_LOSS_LIMIT_REACHED: Daily PnL ${effective_daily_pnl:.2f} exceeds limit -${self.config.max_daily_loss:.2f}",
            )

        # 2. Trailing Drawdown Check
        current_drawdown = self.peak_balance - self.current_balance
        if (
            self.config.max_total_drawdown is not None
            and current_drawdown >= self.config.max_total_drawdown
        ):
            return RiskCheckResult(
                allowed=False,
                reason=f"MAX_DRAWDOWN_LIMIT_REACHED: Drawdown ${current_drawdown:.2f} exceeds limit ${self.config.max_total_drawdown:.2f}",
            )

        # 3. Consecutive Loss Circuit Breaker
        if (
            self.config.max_consecutive_losses is not None
            and effective_consecutive_losses >= self.config.max_consecutive_losses
        ):
            return RiskCheckResult(
                allowed=False,
                reason=f"CONSECUTIVE_LOSS_LIMIT_REACHED: {effective_consecutive_losses} consecutive losses",
            )

        # 4. Session Hours Filter
        if current_time.hour in self.config.excluded_hours_utc:
            return RiskCheckResult(
                allowed=False,
                reason=f"SESSION_HOUR_FILTER: {current_time.hour:02d}:00 UTC is an excluded chop hour",
            )

        return RiskCheckResult(allowed=True, reason="ALLOWED")
