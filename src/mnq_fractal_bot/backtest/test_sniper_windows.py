"""
Backtest Verification of the 3 Sniper Windows (Frankfurt/London + NY Morning + NY Afternoon)
Evaluates across the full 13,669 5-minute historical dataset.
"""
from collections import defaultdict
from pathlib import Path
from mnq_fractal_bot.data.csv_loader import load_candles_from_csv
from mnq_fractal_bot.execution.bot_runner import BotRunner
from mnq_fractal_bot.execution.paper_broker import MNQ_POINT_VALUE
from mnq_fractal_bot.execution.stream_session import PaperStreamSession
from mnq_fractal_bot.risk.trade_filter import TradeFilterConfig
from mnq_fractal_bot.risk.risk_guard import RiskGuardConfig

def main():
    csv_path = Path("data/mnq_5m_deep.csv")
    if not csv_path.exists():
        csv_path = Path("data/mnq_5m_live.csv")
        
    print(f"Loading {csv_path}...")
    candles = load_candles_from_csv(csv_path)
    print(f"Loaded {len(candles)} continuous 5m candles.")

    # 1. BASELINE (ALL HOURS / NO TIME FILTER)
    tf_base = TradeFilterConfig(
        allow_c3=True,
        allow_c4=False,
        min_stop_points=15.0,
        max_stop_points=35.0,
        min_rr_ratio=1.0,
    )
    rg_base = RiskGuardConfig(
        max_daily_loss=600.0,
        max_total_drawdown=1000.0,
        max_consecutive_losses=10,
        excluded_hours_utc=(),
    )
    runner_base = BotRunner(
        trade_filter_config=tf_base,
        point_value=MNQ_POINT_VALUE,
        risk_guard_config=rg_base,
    )
    session_base = PaperStreamSession(bot_runner=runner_base, warmup_candles=500, on_event=lambda ev: None)
    session_base.stream_all(candles)
    trades_base = runner_base.broker.closed_trades

    # 2. 3-WINDOW SNIPER STRATEGY (FRANKFURT/LONDON + NY OPEN + NY PM)
    allowed_sniper_hours_utc = {6, 7, 8, 13, 14, 15, 17, 18, 19}
    all_hours = set(range(24))
    excluded_hours = tuple(sorted(all_hours - allowed_sniper_hours_utc))

    rg_sniper = RiskGuardConfig(
        max_daily_loss=150.0,
        max_total_drawdown=800.0,
        max_consecutive_losses=2,
        excluded_hours_utc=excluded_hours,
    )
    runner_sniper = BotRunner(
        trade_filter_config=tf_base,
        point_value=MNQ_POINT_VALUE,
        risk_guard_config=rg_sniper,
    )
    session_sniper = PaperStreamSession(bot_runner=runner_sniper, warmup_candles=500, on_event=lambda ev: None)
    session_sniper.stream_all(candles)
    trades_sniper = runner_sniper.broker.closed_trades

    def calc_stats(trades):
        wins = [t for t in trades if t.gross_pnl > 0]
        losses = [t for t in trades if t.gross_pnl <= 0]
        total_pnl = sum(t.gross_pnl for t in trades)
        win_rate = (len(wins) / len(trades) * 100) if trades else 0.0
        gain = sum(t.gross_pnl for t in wins)
        loss = abs(sum(t.gross_pnl for t in losses))
        pf = (gain / loss) if loss > 0 else 99.9
        
        daily = defaultdict(float)
        for t in trades:
            day = t.exit_time.strftime("%Y-%m-%d")
            daily[day] += t.gross_pnl
        worst_day = min(daily.values()) if daily else 0.0
        best_day = max(daily.values()) if daily else 0.0
        return len(trades), len(wins), len(losses), win_rate, pf, total_pnl, worst_day, best_day

    b_total, b_w, b_l, b_wr, b_pf, b_pnl, b_worst, b_best = calc_stats(trades_base)
    s_total, s_w, s_l, s_wr, s_pf, s_pnl, s_worst, s_best = calc_stats(trades_sniper)

    print("\n" + "=" * 70)
    print(" 🏛️ 60-DAY BACKTEST COMPARISON: ALL HOURS vs 3-WINDOW SNIPER")
    print("=" * 70)
    print(f"{'Metric':<28} | {'All Hours (No Filter)':<20} | {'3 Sniper Windows'}")
    print("-" * 70)
    print(f"{'Total Trades':<28} | {b_total:<20} | {s_total}")
    print(f"{'Winning Trades':<28} | {b_w:<20} | {s_w}")
    print(f"{'Losing Trades':<28} | {b_l:<20} | {s_l}")
    print(f"{'Win Rate':<28} | {b_wr:<19.1f}% | {s_wr:.1f}%")
    print(f"{'Profit Factor':<28} | {b_pf:<20.2f} | {s_pf:.2f}")
    print(f"{'Net Profit (P&L)':<28} | +${b_pnl:<19.2f} | +${s_pnl:.2f}")
    print(f"{'Worst Single Day':<28} | -${abs(b_worst):<19.2f} | -${abs(s_worst):.2f}")
    print(f"{'Best Single Day':<28} | +${b_best:<19.2f} | +${s_best:.2f}")
    print("=" * 70)

if __name__ == "__main__":
    main()
