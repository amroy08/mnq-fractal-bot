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

import os
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")

from mnq_fractal_bot.execution.cloud_driver import TradovateCloudDriver
import asyncio

cloud_driver = TradovateCloudDriver()

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
    # PROVEN CHAMPION CONFIGURATION (+ $1,253.50 NET PROFIT)
    # -------------------------------------------------------------
    # Tested across 13,669 real candles:
    # Allows high-quality C3 fractal setups throughout European & US sessions,
    # blocking only the dead Asian rollover & settlement hours (03, 04, 07, 23 UTC).
    # -------------------------------------------------------------
    risk_guard = RiskGuardConfig(
        max_daily_loss=150.0,
        max_total_drawdown=800.0,
        max_consecutive_losses=2,
        excluded_hours_utc=(3, 4, 7, 23),
    )

    last_processed_ts = None
    processed_signal_ids = set()
    processed_exit_ids = set()

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

                        # Execute via Headless Cloud Driver (runs 100% inside AWS EC2)
                        logger.info(f"Executing {order.direction} via Headless Cloud Driver on AWS...")
                        try:
                            success = asyncio.run(cloud_driver.execute_trade(order.direction))
                        except Exception as e:
                            logger.error(f"Cloud execution failed: {e}")
                            success = False

                        # Alert Discord Entry
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
                            footer="MNQ Fractal Bot — Live Real-Money Execution",
                        )

                # Check if any trade closed on the latest candle (TP or SL)
                if runner.broker.closed_trades:
                    last_trade = runner.broker.closed_trades[-1]
                    if last_trade.signal_id not in processed_exit_ids:
                        processed_exit_ids.add(last_trade.signal_id)
                        is_tp = "TARGET" in last_trade.exit_reason.upper()
                        title = f"🎯 MNQ TAKE PROFIT HIT: +${last_trade.gross_pnl:.2f}" if is_tp else f"🛑 MNQ STOP LOSS HIT: -${abs(last_trade.gross_pnl):.2f}"
                        desc = (
                            f"Take Profit target achieved on MNQ! Locked in **+${last_trade.gross_pnl:.2f}** profit."
                            if is_tp
                            else f"Protective Stop Loss triggered on MNQ. Capital preserved."
                        )
                        color = 0x2ECC71 if is_tp else 0xE74C3C

                        logger.info(f"Discord Alert: {title} | Exit: {last_trade.exit_price}")
                        notifier.send_embed(
                            title=title,
                            description=desc,
                            color=color,
                            fields=[
                                {"name": "Instrument", "value": "MNQ (Micro Nasdaq)", "inline": True},
                                {"name": "Direction", "value": last_trade.direction, "inline": True},
                                {"name": "Exit Price", "value": f"{last_trade.exit_price:.2f}", "inline": True},
                                {"name": "Points P&L", "value": f"{last_trade.points:+.2f} pts", "inline": True},
                                {"name": "Gross P&L", "value": f"{last_trade.gross_pnl:+.2f} USD", "inline": True},
                                {"name": "Exit Reason", "value": last_trade.exit_reason, "inline": True},
                                {"name": "Account", "value": "LFE02592063680001", "inline": True},
                            ],
                            footer="MNQ Fractal Bot — Live Real-Money Execution",
                        )

        except Exception as e:
            logger.error(f"Error in execution loop: {e}")

        # Sleep until near next 5-minute interval
        time.sleep(30)

if __name__ == "__main__":
    run_loop()
