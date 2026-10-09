from collections.abc import Sequence
from dataclasses import dataclass

from mnq_fractal_bot.execution.paper_broker import (
    ClosedTrade,
)


@dataclass(frozen=True)
class BacktestStats:
    total_trades: int

    wins: int
    losses: int
    breakeven: int

    win_rate_pct: float

    gross_profit: float
    gross_loss: float
    gross_pnl: float

    average_trade: float
    average_win: float
    average_loss: float

    profit_factor: float | None

    max_drawdown: float
    max_drawdown_pct: float

    starting_balance: float
    ending_balance: float


@dataclass(frozen=True)
class TradeLogRow:
    trade_number: int

    signal_id: str
    direction: str

    entry_time: object
    exit_time: object

    entry_price: float
    exit_price: float

    stop_price: float
    target_price: float

    exit_reason: str

    points: float
    gross_pnl: float

    running_pnl: float
    equity: float


def build_backtest_stats(
    trades: Sequence[ClosedTrade],
    starting_balance: float = 25_000.0,
) -> BacktestStats:
    if starting_balance <= 0:
        raise ValueError(
            "Starting balance must be greater than zero."
        )

    total_trades = len(trades)

    winning_trades = [
        trade
        for trade in trades
        if trade.gross_pnl > 0
    ]

    losing_trades = [
        trade
        for trade in trades
        if trade.gross_pnl < 0
    ]

    breakeven_trades = [
        trade
        for trade in trades
        if trade.gross_pnl == 0
    ]

    wins = len(winning_trades)
    losses = len(losing_trades)
    breakeven = len(breakeven_trades)

    # ==================================================
    # WIN RATE
    # ==================================================

    if total_trades > 0:
        win_rate_pct = (
            wins
            / total_trades
        ) * 100.0
    else:
        win_rate_pct = 0.0

    # ==================================================
    # P&L
    # ==================================================

    gross_profit = sum(
        trade.gross_pnl
        for trade in winning_trades
    )

    gross_loss = sum(
        trade.gross_pnl
        for trade in losing_trades
    )

    gross_pnl = sum(
        trade.gross_pnl
        for trade in trades
    )

    # ==================================================
    # AVERAGES
    # ==================================================

    average_trade = (
        gross_pnl / total_trades
        if total_trades > 0
        else 0.0
    )

    average_win = (
        gross_profit / wins
        if wins > 0
        else 0.0
    )

    average_loss = (
        gross_loss / losses
        if losses > 0
        else 0.0
    )

    # ==================================================
    # PROFIT FACTOR
    #
    # Gross winning dollars
    # ---------------------
    # Gross losing dollars
    #
    # Example:
    #
    # +$60 wins
    # -$40 losses
    #
    # Profit factor = 1.50
    # ==================================================

    profit_factor = None

    if gross_loss < 0:
        profit_factor = (
            gross_profit
            / abs(gross_loss)
        )

    # ==================================================
    # REALIZED EQUITY + MAX DRAWDOWN
    #
    # This is CLOSED-TRADE drawdown.
    #
    # We are NOT yet calculating intratrade
    # unrealized drawdown.
    # ==================================================

    equity = starting_balance
    peak_equity = starting_balance

    max_drawdown = 0.0
    max_drawdown_pct = 0.0

    for trade in trades:
        equity += trade.gross_pnl

        if equity > peak_equity:
            peak_equity = equity

        drawdown = (
            peak_equity
            - equity
        )

        if drawdown > max_drawdown:
            max_drawdown = drawdown

        if peak_equity > 0:
            drawdown_pct = (
                drawdown
                / peak_equity
            ) * 100.0
        else:
            drawdown_pct = 0.0

        if drawdown_pct > max_drawdown_pct:
            max_drawdown_pct = (
                drawdown_pct
            )

    ending_balance = (
        starting_balance
        + gross_pnl
    )

    return BacktestStats(
        total_trades=total_trades,

        wins=wins,
        losses=losses,
        breakeven=breakeven,

        win_rate_pct=win_rate_pct,

        gross_profit=gross_profit,
        gross_loss=gross_loss,
        gross_pnl=gross_pnl,

        average_trade=average_trade,
        average_win=average_win,
        average_loss=average_loss,

        profit_factor=profit_factor,

        max_drawdown=max_drawdown,
        max_drawdown_pct=max_drawdown_pct,

        starting_balance=starting_balance,
        ending_balance=ending_balance,
    )


def build_trade_log(
    trades: Sequence[ClosedTrade],
    starting_balance: float = 25_000.0,
) -> tuple[TradeLogRow, ...]:
    if starting_balance <= 0:
        raise ValueError(
            "Starting balance must be greater than zero."
        )

    running_pnl = 0.0

    rows: list[TradeLogRow] = []

    for index, trade in enumerate(
        trades,
        start=1,
    ):
        running_pnl += (
            trade.gross_pnl
        )

        equity = (
            starting_balance
            + running_pnl
        )

        rows.append(
            TradeLogRow(
                trade_number=index,

                signal_id=trade.signal_id,
                direction=trade.direction,

                entry_time=trade.entry_time,
                exit_time=trade.exit_time,

                entry_price=trade.entry_price,
                exit_price=trade.exit_price,

                stop_price=trade.stop_price,
                target_price=trade.target_price,

                exit_reason=trade.exit_reason,

                points=trade.points,
                gross_pnl=trade.gross_pnl,

                running_pnl=running_pnl,
                equity=equity,
            )
        )

    return tuple(rows)