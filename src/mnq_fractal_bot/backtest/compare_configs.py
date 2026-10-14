"""
Backtest Comparison: OLD config vs NEW (5 upgrades)

Downloads 60-day Yahoo MNQ data and runs both configs,
printing a side-by-side comparison of win rate, P&L,
and per-day performance.
"""
import sys
from collections import defaultdict
from pathlib import Path

# Ensure project root is importable
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root / "src"))

from mnq_fractal_bot.data.live_yahoo_fetcher import fetch_live_mnq_candles
from mnq_fractal_bot.data.csv_loader import load_candles_from_csv
from mnq_fractal_bot.execution.bot_runner import BotRunner
from mnq_fractal_bot.execution.paper_broker import MNQ_POINT_VALUE
from mnq_fractal_bot.execution.stream_session import PaperStreamSession
from mnq_fractal_bot.risk.risk_guard import RiskGuardConfig
from mnq_fractal_bot.risk.trade_filter import TradeFilterConfig


def run_backtest(candles, label, **kwargs):
    """Run a backtest with given config and return stats."""
    runner = BotRunner(
        point_value=MNQ_POINT_VALUE,
        **kwargs,
    )

    session = PaperStreamSession(
        bot_runner=runner,
        warmup_candles=500,
        on_event=lambda ev: None,  # silent
    )
    session.stream_all(candles)

    trades = runner.broker.closed_trades
    wins = [t for t in trades if t.gross_pnl > 0]
    losses = [t for t in trades if t.gross_pnl <= 0]
    total_pnl = sum(t.gross_pnl for t in trades)
    win_rate = (len(wins) / len(trades) * 100) if trades else 0.0
    avg_win = (sum(t.gross_pnl for t in wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(t.gross_pnl for t in losses) / len(losses)) if losses else 0.0

    # Per-day breakdown
    daily = defaultdict(float)
    daily_count = defaultdict(int)
    daily_wins = defaultdict(int)
    for t in trades:
        day = t.exit_time.strftime("%Y-%m-%d")
        daily[day] += t.gross_pnl
        daily_count[day] += 1
        if t.gross_pnl > 0:
            daily_wins[day] += 1

    worst_day = min(daily.values()) if daily else 0.0
    best_day = max(daily.values()) if daily else 0.0
    green_days = sum(1 for v in daily.values() if v > 0)
    red_days = sum(1 for v in daily.values() if v <= 0)

    return {
        "label": label,
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "worst_day": worst_day,
        "best_day": best_day,
        "green_days": green_days,
        "red_days": red_days,
        "daily": dict(daily),
        "daily_count": dict(daily_count),
        "daily_wins": dict(daily_wins),
        "trades": trades,
    }


def print_comparison(old, new):
    """Print side-by-side comparison."""
    print()
    print("=" * 72)
    print("  BACKTEST COMPARISON: OLD CONFIG vs NEW (5 UPGRADES)")
    print("=" * 72)
    print()
    print(f"{'Metric':<25} {'OLD (Baseline)':>18} {'NEW (Upgraded)':>18} {'Delta':>12}")
    print("-" * 73)

    rows = [
        ("Total Trades", f"{old['total_trades']}", f"{new['total_trades']}",
         f"{new['total_trades'] - old['total_trades']:+d}"),
        ("Wins", f"{old['wins']}", f"{new['wins']}",
         f"{new['wins'] - old['wins']:+d}"),
        ("Losses", f"{old['losses']}", f"{new['losses']}",
         f"{new['losses'] - old['losses']:+d}"),
        ("Win Rate", f"{old['win_rate']:.1f}%", f"{new['win_rate']:.1f}%",
         f"{new['win_rate'] - old['win_rate']:+.1f}%"),
        ("Net P&L", f"${old['total_pnl']:,.2f}", f"${new['total_pnl']:,.2f}",
         f"${new['total_pnl'] - old['total_pnl']:+,.2f}"),
        ("Avg Win", f"${old['avg_win']:,.2f}", f"${new['avg_win']:,.2f}",
         f"${new['avg_win'] - old['avg_win']:+,.2f}"),
        ("Avg Loss", f"${old['avg_loss']:,.2f}", f"${new['avg_loss']:,.2f}",
         f"${new['avg_loss'] - old['avg_loss']:+,.2f}"),
        ("Best Day", f"${old['best_day']:,.2f}", f"${new['best_day']:,.2f}", ""),
        ("Worst Day", f"${old['worst_day']:,.2f}", f"${new['worst_day']:,.2f}", ""),
        ("Green Days", f"{old['green_days']}", f"{new['green_days']}", ""),
        ("Red Days", f"{old['red_days']}", f"{new['red_days']}", ""),
    ]

    for label, o, n, delta in rows:
        print(f"  {label:<23} {o:>18} {n:>18} {delta:>12}")

    # Print per-day breakdown for BOTH configs
    all_days = sorted(set(list(old["daily"].keys()) + list(new["daily"].keys())))

    print()
    print("=" * 72)
    print("  PER-DAY BREAKDOWN")
    print("=" * 72)
    print(f"  {'Date':<12} {'OLD Trades':>10} {'OLD P&L':>12} {'NEW Trades':>10} {'NEW P&L':>12}")
    print("  " + "-" * 58)

    for day in all_days:
        old_pnl = old["daily"].get(day, 0.0)
        old_cnt = old["daily_count"].get(day, 0)
        new_pnl = new["daily"].get(day, 0.0)
        new_cnt = new["daily_count"].get(day, 0)

        old_sign = "+" if old_pnl > 0 else ""
        new_sign = "+" if new_pnl > 0 else ""

        print(f"  {day:<12} {old_cnt:>10} {old_sign}${old_pnl:>10,.2f} {new_cnt:>10} {new_sign}${new_pnl:>10,.2f}")

    print()


def main():
    print("Downloading 60-day MNQ 5m candles from Yahoo Finance...")
    csv_path = fetch_live_mnq_candles(
        interval="5m",
        range_period="60d",
        output_path=project_root / "data" / "mnq_5m_backtest_comparison.csv",
    )

    candles = load_candles_from_csv(csv_path)
    print(f"Loaded {len(candles):,} candles")
    print(f"   Range: {candles[0].timestamp} -> {candles[-1].timestamp}")
    print()

    # ===================================
    # OLD CONFIG (current production)
    # No risk guard to match original 76-trade baseline
    # ===================================
    print("Running OLD config (baseline - no risk guard)...")
    old_stats = run_backtest(
        candles,
        label="OLD (Baseline)",
        trade_filter_config=TradeFilterConfig(
            allow_c3=True,
            allow_c4=False,
            max_stop_points=50.0,
        ),
        breakeven_trigger_r=1.0,
        # No risk guard - pure strategy performance
    )
    print(f"   -> {old_stats['total_trades']} trades, {old_stats['win_rate']:.1f}% WR, ${old_stats['total_pnl']:,.2f}")

    # ===================================
    # OLD + RISK GUARD (what the bot was
    # actually running with recently)
    # ===================================
    print("Running OLD config + risk guard (recent production)...")
    old_guarded = run_backtest(
        candles,
        label="OLD + Guard",
        trade_filter_config=TradeFilterConfig(
            allow_c3=True,
            allow_c4=False,
            max_stop_points=50.0,
        ),
        breakeven_trigger_r=1.0,
        risk_guard_config=RiskGuardConfig(
            max_daily_loss=150.0,
            max_total_drawdown=1500.0,
            max_consecutive_losses=2,
        ),
    )
    print(f"   -> {old_guarded['total_trades']} trades, {old_guarded['win_rate']:.1f}% WR, ${old_guarded['total_pnl']:,.2f}")

    # ===================================
    # ===================================
    # CONFIG A: NY RTH (US Session Only: 9:30 AM - 4 PM ET)
    # 13:00 - 19:59 UTC
    # ===================================
    print("Running CONFIG A (NY RTH: 9:30 AM - 4 PM ET)...")
    rth_excluded = tuple(h for h in range(24) if h not in range(13, 20))
    rth_stats = run_backtest(
        candles,
        label="NY RTH Only",
        trade_filter_config=TradeFilterConfig(
            allow_c3=True,
            allow_c4=False,
            max_stop_points=35.0,
            min_stop_points=15.0,
            min_rr_ratio=1.2,
        ),
        breakeven_trigger_r=1.0,
        risk_guard_config=RiskGuardConfig(
            max_daily_loss=150.0,
            max_total_drawdown=800.0,
            max_consecutive_losses=2,
            excluded_hours_utc=rth_excluded,
        ),
    )
    print(f"   -> {rth_stats['total_trades']} trades, {rth_stats['win_rate']:.1f}% WR, ${rth_stats['total_pnl']:,.2f}")

    # ===================================
    # CONFIG B: ALL SESSIONS MINUS TOXIC CHOP HOURS
    # Excludes 03, 04, 07, 23 UTC (overnight chop deadzones)
    # ===================================
    print("Running CONFIG B (Global minus Toxic Chop Hours)...")
    toxic_excluded = (3, 4, 7, 23)
    toxic_stats = run_backtest(
        candles,
        label="High-EV (Toxic Cut)",
        trade_filter_config=TradeFilterConfig(
            allow_c3=True,
            allow_c4=False,
            max_stop_points=35.0,
            min_stop_points=15.0,
            min_rr_ratio=1.0,
        ),
        breakeven_trigger_r=1.0,
        risk_guard_config=RiskGuardConfig(
            max_daily_loss=150.0,
            max_total_drawdown=800.0,
            max_consecutive_losses=2,
            excluded_hours_utc=toxic_excluded,
        ),
    )
    print(f"   -> {toxic_stats['total_trades']} trades, {toxic_stats['win_rate']:.1f}% WR, ${toxic_stats['total_pnl']:,.2f}")

    # ===================================
    # COMPARISON
    # ===================================
    print()
    print("=" * 88)
    print("  60-DAY YAHOO AUDIT: BASELINE vs OPTIMIZED CONFIGS")
    print("=" * 88)
    print()

    configs = [old_stats, rth_stats, toxic_stats]
    header = f"{'Metric':<22}"
    for c in configs:
        header += f" {c['label']:>16}"
    print(header)
    print("-" * (22 + 17 * len(configs)))

    metrics = [
        ("Total Trades", "total_trades", "d"),
        ("Wins", "wins", "d"),
        ("Losses", "losses", "d"),
        ("Win Rate", "win_rate", ".1f"),
        ("Net P&L", "total_pnl", ",.2f"),
        ("Avg Win", "avg_win", ",.2f"),
        ("Avg Loss", "avg_loss", ",.2f"),
        ("Best Day", "best_day", ",.2f"),
        ("Worst Day", "worst_day", ",.2f"),
        ("Green Days", "green_days", "d"),
        ("Red Days", "red_days", "d"),
    ]

    for label, key, fmt in metrics:
        row = f"  {label:<20}"
        for c in configs:
            val = c[key]
            if fmt == "d":
                row += f" {val:>16}"
            elif "f" in fmt:
                if key == "win_rate":
                    row += f" {val:>15.1f}%"
                else:
                    row += f" ${val:>14{fmt}}"
            else:
                row += f" {val:>16}"
        print(row)

    # Per-day for best config
    best = toxic_stats if toxic_stats["total_pnl"] > rth_stats["total_pnl"] else rth_stats
    print()
    print("=" * 72)
    print(f"  PER-DAY BREAKDOWN: {best['label']}")
    print("=" * 72)
    print(f"  {'Date':<12} {'Trades':>8} {'Wins':>6} {'P&L':>12} {'Status':>8}")
    print("  " + "-" * 48)

    for day in sorted(best["daily"].keys()):
        pnl = best["daily"][day]
        count = best["daily_count"][day]
        w = best["daily_wins"].get(day, 0)
        status = "GREEN" if pnl > 0 else ("FLAT" if pnl == 0 else "RED")
        sign = "+" if pnl > 0 else ""
        print(f"  {day:<12} {count:>8} {w:>6} {sign}${pnl:>10,.2f} {status:>8}")

    # Summary verdict
    print()
    print("=" * 72)
    print("  VERDICT")
    print("=" * 72)

    if best["win_rate"] > old_stats["win_rate"]:
        delta_wr = best["win_rate"] - old_stats["win_rate"]
        print(f"  Win rate: {old_stats['win_rate']:.1f}% -> {best['win_rate']:.1f}% (+{delta_wr:.1f}%)")

    if best["worst_day"] > old_stats["worst_day"]:
        print(f"  Worst day: ${old_stats['worst_day']:,.2f} -> ${best['worst_day']:,.2f} (IMPROVED)")

    total_days = max(best["green_days"] + best["red_days"], 1)
    avg_daily = best["total_pnl"] / total_days
    print(f"  Avg daily P&L: ${avg_daily:,.2f}")

    if avg_daily > 0:
        days_to_pass = 838.0 / avg_daily
        print(f"  Estimated days to pass eval ($838 remaining): ~{days_to_pass:.0f} trading days")
    else:
        print(f"  WARNING: Avg daily P&L is negative — strategy needs further tuning")

    print()


if __name__ == "__main__":
    main()
