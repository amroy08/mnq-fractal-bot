import argparse
import sys
import time
from pathlib import Path

from mnq_fractal_bot.data.csv_loader import load_candles_from_csv
from mnq_fractal_bot.data.webhook_server import WebhookServer
from mnq_fractal_bot.execution.bot_runner import BotRunner
from mnq_fractal_bot.execution.paper_broker import MNQ_POINT_VALUE
from mnq_fractal_bot.execution.stream_session import PaperStreamSession, StreamEvent
from mnq_fractal_bot.notifications import DiscordNotifier
from mnq_fractal_bot.risk.risk_guard import RiskGuard, RiskGuardConfig
from mnq_fractal_bot.risk.trade_filter import TradeFilterConfig


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="MNQ Fractal Bot — Live Real-Time Webhook Runner"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to listen for incoming 5m candle webhooks (default: 8080)",
    )

    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host address to bind the webhook server (default: 0.0.0.0)",
    )

    parser.add_argument(
        "--history-csv",
        type=Path,
        default=Path("data/mnq_5m_real.csv"),
        help="Path to historical CSV for pre-warming the strategy engine (default: data/mnq_5m_real.csv)",
    )

    parser.add_argument(
        "--min-stop-points",
        type=float,
        default=22.0,
        help="Minimum required stop loss distance in points (default: 22.0)",
    )

    parser.add_argument(
        "--max-stop-points",
        type=float,
        default=35.0,
        help="Maximum allowed stop loss distance in points (default: 35.0)",
    )

    parser.add_argument(
        "--exclude-hours-utc",
        type=int,
        nargs="*",
        default=[3, 4, 9],
        help="UTC hours (0-23) to exclude from trading (default: 3 4 9)",
    )

    parser.add_argument(
        "--max-hold-minutes",
        type=float,
        default=180.0,
        help="Time-stop: auto-exit open position if lingering beyond N minutes (default: 180.0)",
    )

    parser.add_argument(
        "--discord-webhook",
        type=str,
        default="https://discord.com/api/webhooks/1559122213980995637/VGqK-9RYzrw1vx1H-0pfblxzyGZKXEylBLID_rK_ZcF606gJCWAvBt4Y83ZAXWtqDQ6R",
        help="Discord Webhook URL for live trade alerts",
    )

    return parser.parse_args(args)


def run_live_bot(args: argparse.Namespace) -> int:
    print("=" * 72)
    print("MNQ FRACTAL BOT — LIVE REAL-TIME PAPER RUNNER")
    print("=" * 72)
    print(f"Server host:port: {args.host}:{args.port}")
    print(f"Risk Rules      : Stop [{args.min_stop_points:.0f} - {args.max_stop_points:.0f} pts], Time-stop {args.max_hold_minutes:.0f}m")
    print(f"Session Filter  : Exclude UTC {args.exclude_hours_utc}")
    print("Execution Mode  : PAPER SIMULATION (NO REAL BROKER ORDERS)")
    print("=" * 72)

    # 1. Trade Filter & Risk Guard
    filter_config = TradeFilterConfig(
        allow_c3=True,
        allow_c4=False,
        min_stop_points=args.min_stop_points,
        max_stop_points=args.max_stop_points,
    )

    risk_guard_config = RiskGuardConfig(
        excluded_hours_utc=tuple(args.exclude_hours_utc),
    )

    runner = BotRunner(
        trade_filter_config=filter_config,
        point_value=MNQ_POINT_VALUE,
        max_hold_minutes=args.max_hold_minutes,
        risk_guard_config=risk_guard_config,
    )

    # 2. Discord Notifier
    notifier = DiscordNotifier(webhook_url=args.discord_webhook)
    if notifier.is_configured:
        print(f"Discord Alerts  : ENABLED -> #mnq-alerts")

    def on_stream_event(ev: StreamEvent) -> None:
        for broker_ev in ev.snapshot.events:
            ts = ev.candle.timestamp.strftime("%Y-%m-%d %H:%M UTC")

            if broker_ev.event_type == "ORDER_SUBMITTED":
                print(f"[{ts}] 📝 LIVE ORDER SUBMITTED: {broker_ev.signal_id} @ {broker_ev.price}")
                if notifier.is_configured and runner.broker.pending_order is not None:
                    po = runner.broker.pending_order
                    notifier.notify_order_submitted(
                        signal_id=broker_ev.signal_id or "",
                        direction=po.direction,
                        entry_price=po.entry_price,
                        stop_price=po.stop_price,
                        target_price=po.target_price,
                        timestamp_str=ts,
                    )

            elif broker_ev.event_type == "ENTRY_FILLED":
                print(f"[{ts}] 🟢 LIVE ENTRY FILLED   : {broker_ev.signal_id} @ {broker_ev.price}")
                if notifier.is_configured:
                    notifier.notify_entry_filled(
                        signal_id=broker_ev.signal_id or "",
                        fill_price=broker_ev.price or 0.0,
                        timestamp_str=ts,
                    )

            elif broker_ev.event_type == "TARGET_HIT":
                pnl = broker_ev.gross_pnl or 0.0
                print(f"[{ts}] 🎯 LIVE TARGET HIT     : +${pnl:.2f}")
                if notifier.is_configured:
                    notifier.notify_trade_closed(
                        signal_id=broker_ev.signal_id or "",
                        exit_reason="TARGET",
                        exit_price=broker_ev.price or 0.0,
                        gross_pnl=pnl,
                        timestamp_str=ts,
                    )

            elif broker_ev.event_type in ("STOP_HIT", "POSITION_STOPPED"):
                pnl = broker_ev.gross_pnl or 0.0
                print(f"[{ts}] 🛑 LIVE STOP HIT       : -${abs(pnl):.2f}")
                if notifier.is_configured:
                    notifier.notify_trade_closed(
                        signal_id=broker_ev.signal_id or "",
                        exit_reason="STOPPED",
                        exit_price=broker_ev.price or 0.0,
                        gross_pnl=pnl,
                        timestamp_str=ts,
                    )

            elif broker_ev.event_type == "POSITION_TIME_STOP":
                pnl = broker_ev.gross_pnl or 0.0
                sign = "+" if pnl >= 0 else "-"
                print(f"[{ts}] ⏱️ LIVE TIME-STOP EXIT : {sign}${abs(pnl):.2f}")
                if notifier.is_configured:
                    notifier.notify_trade_closed(
                        signal_id=broker_ev.signal_id or "",
                        exit_reason="TIME_STOP",
                        exit_price=broker_ev.price or 0.0,
                        gross_pnl=pnl,
                        timestamp_str=ts,
                    )

    # 3. Create Stream Session & Warm up with recent history
    session = PaperStreamSession(
        bot_runner=runner,
        warmup_candles=0,
        on_event=on_stream_event,
    )

    if args.history_csv.exists():
        history = load_candles_from_csv(args.history_csv)
        if history:
            print(f"Pre-warming engine with {min(len(history), 500)} recent candles from {args.history_csv}...")
            # Feed last 500 candles to establish HTF context
            warm_candles = history[-500:]
            for c in warm_candles:
                runner.on_candle(c)
            print("Engine pre-warmed successfully. Ready for live candles.")

    # 4. Start HTTP Webhook Server
    server = WebhookServer(
        server_address=(args.host, args.port),
        stream_session=session,
    )

    print("-" * 72)
    print(f"🚀 LIVE BOT LISTENING on http://{args.host}:{args.port}/webhook/candle")
    print("Press Ctrl+C to stop.")
    print("-" * 72)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping live bot gracefully...")
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    sys.exit(run_live_bot(parse_args()))
