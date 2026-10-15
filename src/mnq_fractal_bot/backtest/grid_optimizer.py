"""
Quantitative Grid-Search Optimizer & Stress-Tester for MNQ Fractal Strategy
Tests parameter matrices across stops, targets, hours, and HTF bias.
Outputs:
- Win Rate (%)
- Net P&L ($)
- Profit Factor
- Max Drawdown ($)
- Max Consecutive Losses (Drawdown safety against $600 daily limit)
"""
import itertools
from collections import defaultdict
from pathlib import Path
from mnq_fractal_bot.data.csv_loader import load_candles_from_csv
from mnq_fractal_bot.execution.bot_runner import BotRunner
from mnq_fractal_bot.execution.paper_broker import MNQ_POINT_VALUE
from mnq_fractal_bot.execution.stream_session import PaperStreamSession
from mnq_fractal_bot.risk.trade_filter import TradeFilterConfig
from mnq_fractal_bot.risk.risk_guard import RiskGuardConfig

def run_simulation(candles, min_stop, max_stop, min_rr, require_htf):
    trade_filter = TradeFilterConfig(
        allow_c3=True,
        allow_c4=False,
        min_stop_points=min_stop,
        max_stop_points=max_stop,
        min_rr_ratio=min_rr,
    )
    risk_guard = RiskGuardConfig(
        max_daily_loss=600.0,
        max_total_drawdown=1000.0,
        max_consecutive_losses=10,
        excluded_hours_utc=(3, 4, 7, 23),
    )
    runner = BotRunner(
        trade_filter_config=trade_filter,
        point_value=MNQ_POINT_VALUE,
        risk_guard_config=risk_guard,
        require_htf_bias=require_htf,
    )
    session = PaperStreamSession(
        bot_runner=runner,
        warmup_candles=500,
        on_event=lambda ev: None,
    )
    session.stream_all(candles)
    
    trades = runner.broker.closed_trades
    if not trades:
        return None
        
    wins = [t for t in trades if t.gross_pnl > 0]
    losses = [t for t in trades if t.gross_pnl <= 0]
    total_pnl = sum(t.gross_pnl for t in trades)
    win_rate = (len(wins) / len(trades) * 100) if trades else 0.0
    
    # Calculate Profit Factor
    gross_gain = sum(t.gross_pnl for t in wins)
    gross_loss = abs(sum(t.gross_pnl for t in losses))
    profit_factor = (gross_gain / gross_loss) if gross_loss > 0 else 99.9
    
    # Calculate Max Consecutive Losses
    max_consec_losses = 0
    current_consec = 0
    for t in trades:
        if t.gross_pnl <= 0:
            current_consec += 1
            if current_consec > max_consec_losses:
                max_consec_losses = current_consec
        else:
            current_consec = 0
            
    # Daily performance & worst day
    daily_pnl = defaultdict(float)
    for t in trades:
        day = t.exit_time.strftime("%Y-%m-%d")
        daily_pnl[day] += t.gross_pnl
    worst_day = min(daily_pnl.values()) if daily_pnl else 0.0

    return {
        "min_stop": min_stop,
        "max_stop": max_stop,
        "min_rr": min_rr,
        "htf_bias": require_htf,
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_pnl": total_pnl,
        "worst_day": worst_day,
        "max_consecutive_losses": max_consec_losses,
    }

def main():
    csv_path = Path("data/mnq_5m_deep.csv")
    if not csv_path.exists():
        csv_path = Path("data/mnq_5m_live.csv")
        
    print(f"Loading candles from {csv_path}...")
    candles = load_candles_from_csv(csv_path)
    print(f"Loaded {len(candles)} candles.")
    
    # Grid parameters
    stop_ranges = [(15.0, 25.0), (15.0, 35.0), (20.0, 35.0), (20.0, 45.0)]
    rr_ratios = [1.0, 1.2, 1.5, 2.0]
    htf_options = [True, False]
    
    results = []
    print("\nRunning Parameter Grid Search across historical dataset...")
    print("-" * 85)
    for (min_s, max_s), rr, htf in itertools.product(stop_ranges, rr_ratios, htf_options):
        res = run_simulation(candles, min_s, max_s, rr, htf)
        if res:
            results.append(res)
            
    # Sort results by Profit Factor and Win Rate
    results.sort(key=lambda x: (x["profit_factor"], x["win_rate"]), reverse=True)
    
    print(f"{'Stops':<14} | {'Min R:R':<8} | {'HTF':<5} | {'Trades':<6} | {'Win Rate':<9} | {'PF':<6} | {'Net P&L':<10} | {'Worst Day':<10} | {'Max Loss Streak'}")
    print("=" * 85)
    for r in results[:10]:
        stops_str = f"{r['min_stop']:.0f}-{r['max_stop']:.0f} pts"
        htf_str = "YES" if r['htf_bias'] else "NO"
        print(f"{stops_str:<14} | {r['min_rr']:<8.1f} | {htf_str:<5} | {r['total_trades']:<6} | {r['win_rate']:<8.1f}% | {r['profit_factor']:<6.2f} | +${r['total_pnl']:<8.2f} | -${abs(r['worst_day']):<8.2f} | {r['max_consecutive_losses']} in a row")

if __name__ == "__main__":
    main()
