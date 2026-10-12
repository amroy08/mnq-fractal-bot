import argparse
import sys
import time
from pathlib import Path

from mnq_fractal_bot.data.csv_loader import load_candles_from_csv
from mnq_fractal_bot.data.feed_audit import audit_candle_feed_gaps
from mnq_fractal_bot.execution.bot_runner import BotRunner
from mnq_fractal_bot.execution.paper_broker import MNQ_POINT_VALUE
from mnq_fractal_bot.execution.stream_session import PaperStreamSession, StreamEvent
from mnq_fractal_bot.risk.trade_filter import TradeFilterConfig


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="MNQ Fractal Bot - Realtime / Forward Paper Stream CLI"
    )

    parser.add_argument(
        "csv_path",
        type=Path,
        help="Path to 5m candle CSV file",
    )

    parser.add_argument(
        "--warmup-candles",
        type=int,
        default=500,
        help="Number of initial candles used for engine warmup (default: 500)",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Simulated inter-candle delay in seconds for terminal replay (default: 0.0)",
    )

    parser.add_argument(
        "--max-stop-points",
        type=float,
        default=50.0,
        help="Maximum allowed stop loss distance in points (default: 50.0)",
    )

    parser.add_argument(
        "--min-stop-points",
        type=float,
        default=None,
        help="Minimum required stop loss distance in points to filter tight-stop noise (e.g. 20.0)",
    )

    parser.add_argument(
        "--max-target-points",
        type=float,
        default=None,
        help="Maximum target distance in points to focus on high-probability near targets (e.g. 35.0)",
    )

    parser.add_argument(
        "--c3-only",
        action="store_true",
        default=True,
        help="Restrict execution to C3 entry zone only (default: True)",
    )

    parser.add_argument(
        "--initial-balance",
        type=float,
        default=25000.0,
        help="Starting paper simulation balance (default: $25,000.00)",
    )

    return parser.parse_args(args)


def format_currency(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}${value:,.2f}"


def run_paper_stream(args: argparse.Namespace) -> int:
    if not args.csv_path.exists():
        print(f"Error: CSV file not found: {args.csv_path}", file=sys.stderr)
        return 1

    print("=" * 72)
    print("MNQ FRACTAL BOT — FORWARD PAPER STREAM RUNNER")
    print("=" * 72)
    print(f"Data file       : {args.csv_path}")
    print(f"Warmup candles  : {args.warmup_candles}")
    print(f"Initial balance : ${args.initial_balance:,.2f}")
    filter_desc = f"C3 only, Stop [{args.min_stop_points or 0:.0f} - {args.max_stop_points:.0f} pts]"
    if args.max_target_points:
        filter_desc += f", Max Target {args.max_target_points:.0f} pts"
    print(f"Filter          : {filter_desc}")
    print("Broker mode     : LOCAL PAPER SIMULATION ONLY (NO REAL ORDERS)")
    print("=" * 72)

    # 1. Load data
    candles = load_candles_from_csv(args.csv_path)
    if not candles:
        print("Error: No candles loaded from file.", file=sys.stderr)
        return 1

    print(f"Loaded candles  : {len(candles):,}")
    print(f"Date range      : {candles[0].timestamp} -> {candles[-1].timestamp}")

    # 2. Audit feed quality
    quality = audit_candle_feed_gaps(candles)
    if quality.has_intraday_gaps:
        print(f"Feed audit      : {quality.gap_count} gaps detected across session boundaries")
    else:
        print("Feed audit      : Continuous (no gaps)")
    print("-" * 72)

    # 3. Configure runner & stream session
    filter_config = TradeFilterConfig(
        allow_c3=True,
        allow_c4=not args.c3_only,
        max_stop_points=args.max_stop_points,
        min_stop_points=args.min_stop_points,
        max_target_points=args.max_target_points,
    )

    runner = BotRunner(
        trade_filter_config=filter_config,
        point_value=MNQ_POINT_VALUE,
    )

    live_trade_count = 0
    live_pnl = 0.0

    def on_stream_event(ev: StreamEvent) -> None:
        nonlocal live_trade_count, live_pnl

        # Log broker events as they happen
        for broker_ev in ev.snapshot.events:
            ts = ev.candle.timestamp.strftime("%Y-%m-%d %H:%M UTC")

            if broker_ev.event_type == "ORDER_SUBMITTED":
                print(f"[{ts}] 📝 ORDER SUBMITTED: {broker_ev.signal_id} @ {broker_ev.price}")

            elif broker_ev.event_type == "ENTRY_FILLED":
                print(f"[{ts}] 🟢 ENTRY FILLED   : {broker_ev.signal_id} @ {broker_ev.price}")

            elif broker_ev.event_type == "TARGET_HIT":
                pnl = broker_ev.gross_pnl or 0.0
                live_pnl += pnl
                live_trade_count += 1
                print(f"[{ts}] 🎯 TARGET HIT     : +${pnl:.2f} | Running P&L: {format_currency(live_pnl)}")

            elif broker_ev.event_type == "STOP_HIT":
                pnl = broker_ev.gross_pnl or 0.0
                live_pnl += pnl
                live_trade_count += 1
                print(f"[{ts}] 🛑 STOP HIT       : -${abs(pnl):.2f} | Running P&L: {format_currency(live_pnl)}")

            elif broker_ev.event_type == "ORDER_EXPIRED":
                print(f"[{ts}] ⌛ ORDER EXPIRED  : {broker_ev.signal_id}")

            elif broker_ev.event_type == "ORDER_CANCELLED":
                print(f"[{ts}] 🚫 ORDER CANCELLED: {broker_ev.signal_id}")

        if args.delay > 0:
            time.sleep(args.delay)

    session = PaperStreamSession(
        bot_runner=runner,
        warmup_candles=args.warmup_candles,
        on_event=on_stream_event,
    )

    print("Starting forward stream processing...")
    session.stream_all(candles)

    # 4. Final summary
    closed_trades = runner.broker.closed_trades
    total_gross = sum(t.gross_pnl for t in closed_trades)
    wins = [t for t in closed_trades if t.gross_pnl > 0]
    losses = [t for t in closed_trades if t.gross_pnl <= 0]
    win_rate = (len(wins) / len(closed_trades) * 100) if closed_trades else 0.0

    print("=" * 72)
    print("FORWARD PAPER STREAM COMPLETE")
    print("=" * 72)
    print(f"Total trades filled: {len(closed_trades)}")
    print(f"Wins / Losses      : {len(wins)} / {len(losses)} ({win_rate:.1f}% win rate)")
    print(f"Gross P&L          : {format_currency(total_gross)}")
    print(f"Final Balance      : ${args.initial_balance + total_gross:,.2f}")
    print("=" * 72)

    return 0


def main() -> None:
    sys.exit(run_paper_stream(parse_args()))


if __name__ == "__main__":
    main()
