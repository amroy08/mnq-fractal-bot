import logging
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from mnq_fractal_bot.data.live_yahoo_fetcher import fetch_live_mnq_candles
from mnq_fractal_bot.data.csv_loader import load_candles_from_csv
from mnq_fractal_bot.execution.bot_runner import BotRunner
from mnq_fractal_bot.execution.paper_broker import MNQ_POINT_VALUE
from mnq_fractal_bot.execution.auto_clicker import TradovateAutoClicker
from mnq_fractal_bot.risk.trade_filter import TradeFilterConfig
from mnq_fractal_bot.risk.risk_guard import RiskGuardConfig
from mnq_fractal_bot.notifications import DiscordNotifier

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("LiveDaemon")

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1559122213980995637/VGqK-9RYzrw1vx1H-0pfblxzyGZKXEylBLID_rK_ZcF606gJCWAvBt4Y83ZAXWtqDQ6R"

def run_loop():
    logger.info("=" * 60)
    logger.info("MNQ FRACTAL BOT — 24/7 LIVE AUTONOMOUS EXECUTION DAEMON")
    logger.info("Account: LFE02592063680001 (LucidFlex 25K)")
    logger.info("Stop Clamping: 15-35 pts | Excluded Hours: 03, 04, 07, 23 UTC")
    logger.info("Attached Bracket: 'MNQ Fractal 25K' (25 pt SL / 35 pt TP)")
    logger.info("=" * 60)

    clicker = TradovateAutoClicker()
    notifier = DiscordNotifier(webhook_url=DISCORD_WEBHOOK)
    
    trade_filter = TradeFilterConfig(
        allow_c3=True,
        allow_c4=False,
        min_stop_points=15.0,
        max_stop_points=35.0,
        min_rr_ratio=1.0,
    )
    # -------------------------------------------------------------
    # 3 INSTITUTIONAL SNIPER WINDOWS (FRANKFURT/LONDON + NY)
    # -------------------------------------------------------------
    # We strictly block dead chop periods and trade only high-volume bursts:
    # 1. Frankfurt & London Open: 06:00 - 08:30 UTC (02:00 - 04:30 AM ET / 11:30 AM - 2:00 PM IST)
    # 2. NY Morning Open:         13:30 - 15:30 UTC (09:30 - 11:30 AM ET / 07:00 PM - 9:00 PM IST)
    # 3. NY Afternoon Run:        17:30 - 19:30 UTC (01:30 - 03:30 PM ET / 11:00 PM - 1:00 AM IST)
    # All dead European lulls, Wall Street lunch, and Asian low-volume drift are BLOCKED.
    # -------------------------------------------------------------
    allowed_sniper_hours_utc = {6, 7, 8, 13, 14, 15, 17, 18, 19}
    all_hours = set(range(24))
    excluded_hours = tuple(sorted(all_hours - allowed_sniper_hours_utc))

    risk_guard = RiskGuardConfig(
        max_daily_loss=150.0,
        max_total_drawdown=800.0,
        max_consecutive_losses=2,
        excluded_hours_utc=excluded_hours,
    )

    last_processed_ts = None
    processed_signal_ids = set()

    while True:
        try:
            # 1. Fetch latest 5m live data
            csv_path = fetch_live_mnq_candles()
            candles = load_candles_from_csv(csv_path)

            if not candles:
                time.sleep(30)
                continue

            latest_candle = candles[-1]

            if latest_candle.timestamp != last_processed_ts:
                last_processed_ts = latest_candle.timestamp
                logger.info(f"New 5m Candle closed: {latest_candle.timestamp} | Close: {latest_candle.close}")

                # 2. Run fractal engine across history
                runner = BotRunner(
                    trade_filter_config=trade_filter,
                    point_value=MNQ_POINT_VALUE,
                    risk_guard_config=risk_guard,
                )

                for c in candles:
                    runner.on_candle(c)

                # Check if an active order was submitted on the latest candle
                if runner.broker.pending_order is not None:
                    order = runner.broker.pending_order
                    sig_id = order.signal_id

                    if sig_id not in processed_signal_ids:
                        processed_signal_ids.add(sig_id)
                        logger.info(f"🚨 LIVE SETUP DETECTED! Direction: {order.direction} | Entry: {order.entry_price}")

                        # Execute via Tradovate Auto-Clicker
                        if order.direction == "LONG":
                            logger.info("Executing BUY into Tradovate...")
                            success = clicker.click_buy()
                        else:
                            logger.info("Executing SELL into Tradovate...")
                            success = clicker.click_sell()

                        # Alert Discord
                        notifier.send_embed(
                            title=f"🚨 TRADOVATE ORDER FIRED: {order.direction}",
                            description=f"Auto-clicker triggered **{order.direction}** order into Tradovate.",
                            color=0x2ECC71 if order.direction == "LONG" else 0xE74C3C,
                            fields=[
                                {"name": "Entry Price", "value": f"{order.entry_price:.2f}", "inline": True},
                                {"name": "Stop Loss", "value": f"{order.stop_price:.2f} ({abs(order.entry_price - order.stop_price):.1f} pts)", "inline": True},
                                {"name": "Profit Target", "value": f"{order.target_price:.2f}", "inline": True},
                                {"name": "Account", "value": "LFE02592063680001", "inline": True},
                                {"name": "Execution Status", "value": "SUCCESS" if success else "FAILED", "inline": True},
                            ],
                            footer="MNQ Fractal Bot — Live Autonomous Execution",
                        )

        except Exception as e:
            logger.error(f"Error in execution loop: {e}")

        # Sleep until near next 5-minute interval
        time.sleep(30)

if __name__ == "__main__":
    run_loop()
