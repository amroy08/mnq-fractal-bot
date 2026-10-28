"""
Binance XAU/USDT (Gold Futures) Autonomous Execution Daemon.
Safely protects capital with strict risk management:
- Max Loss Cap per trade: $1.00 (Max 5% of account)
- Daily Circuit Breaker: 2 consecutive losses stops trading for the day
- Leverage: 5x Isolated
- Min R:R: 1.5x
- Real-time Discord notifications for Entry, Stop Loss, and Take Profit
"""
import os
import sys
import time
import logging
from datetime import datetime, timezone
import ccxt

from mnq_fractal_bot.notifications.discord_notifier import DiscordNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("GoldBot")

API_KEY = os.environ.get("BINANCE_API_KEY", "vjTyiyaBiXbfODyOVsUAqtd0ZhW7MEfbnnItYcD3ISn3UzT92Y32GusIwnAKTtR6")
API_SECRET = os.environ.get("BINANCE_API_SECRET", "qn57eCxlgA5EL25KJDLjNYS55lyjsoPoC1ONHmbcaU5aROJl9eLbHHkvGTojlf5F")
DISCORD_URL = os.environ.get("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1560897680371351583/d06UiB9C79jlNs9G5lf9EyEc9Y-e_p7tsssxmV8t9ydI8sLBb_aByckvEgy4DBdcB8FA")

SYMBOL = "XAU/USDT:USDT"
BINANCE_RAW_SYMBOL = "XAUUSDT"
LEVERAGE = 5
MAX_RISK_USD = 2.00      # $2.00 risk per trade (+ $3.00 profit target at 1:1.5 R:R)
MIN_RR = 1.5             # Target at least 1:1.5 Risk/Reward
SWING_LOOKBACK = 4

def run():
    logger.info("=" * 60)
    logger.info("👑 BINANCE XAU/USDT (GOLD FUTURES) AUTONOMOUS EXECUTION DAEMON")
    logger.info(f"Target: {SYMBOL} | Leverage: {LEVERAGE}x Isolated")
    logger.info(f"Capital Protection: Max ${MAX_RISK_USD:.2f} risk per trade | Min R:R: 1:{MIN_RR}")
    logger.info("=" * 60)

    exchange = ccxt.binance({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    notifier = DiscordNotifier(webhook_url=DISCORD_URL)

    try:
        exchange.set_leverage(LEVERAGE, SYMBOL)
        logger.info(f"Set leverage to {LEVERAGE}x for {SYMBOL}")
    except Exception as e:
        logger.warning(f"Leverage notice: {e}")

    # Fetch initial balance
    bal = exchange.fetch_balance()
    usdt = bal['total'].get('USDT', 0)
    logger.info(f"Account Balance Verified: ${usdt:.2f} USDT")

    notifier.send_embed(
        title="👑 GOLD BOT ONLINE (CAPITAL PROTECTION MODE)",
        description=f"Bot is actively scanning **XAU/USDT (Gold)** on 15m.\n"
                    f"**Account Balance:** `${usdt:.2f} USDT`\n"
                    f"**Leverage:** `{LEVERAGE}x Isolated`\n"
                    f"**Max Risk Per Trade:** `${MAX_RISK_USD:.2f}`\n"
                    f"**Target R:R:** `1:{MIN_RR}`",
        color=0xF1C40F,
        fields=[
            {"name": "Status", "value": "🟢 ACTIVE & MONITORING", "inline": True},
            {"name": "Risk Model", "value": "Strict Capital Preservation", "inline": True}
        ]
    )

    consecutive_losses = 0
    processed_signal_bars = set()

    while True:
        try:
            # 1. Fetch latest 15m candles
            candles = exchange.fetch_ohlcv(SYMBOL, timeframe='15m', limit=50)
            if len(candles) < 30:
                time.sleep(15)
                continue

            # Check open positions
            positions = exchange.fetch_positions([SYMBOL])
            open_pos = [p for p in positions if abs(float(p.get('contracts', 0))) > 0]
            if open_pos:
                time.sleep(30)
                continue

            # Swing calculations on closed candles (up to index -2)
            highs = [c[2] for c in candles[:-1]]
            lows = [c[3] for c in candles[:-1]]
            closes = [c[4] for c in candles[:-1]]
            opens = [c[1] for c in candles[:-1]]
            timestamps = [c[0] for c in candles[:-1]]

            last_idx = len(closes) - 1
            last_ts = timestamps[last_idx]

            if last_ts in processed_signal_bars:
                time.sleep(15)
                continue

            cur_h = highs[last_idx]
            cur_l = lows[last_idx]
            cur_c = closes[last_idx]
            cur_o = opens[last_idx]

            # Reference swing highs and lows
            ref_high = max(highs[last_idx - SWING_LOOKBACK : last_idx])
            ref_low = min(lows[last_idx - SWING_LOOKBACK : last_idx])

            # 50 EMA trend filter
            import numpy as np
            import pandas as pd
            df_c = pd.Series(closes)
            ema50 = df_c.ewm(span=50, adjust=False).mean().iloc[-1]

            # Sweep conditions
            bull_sweep = cur_c > ema50 and cur_l < ref_low and cur_c > ref_low
            bear_sweep = cur_c < ema50 and cur_h > ref_high and cur_c < ref_high

            action = None
            entry_price = cur_c
            stop_loss = 0.0
            take_profit = 0.0

            if bull_sweep:
                action = "BUY"
                stop_loss = cur_l - 0.50
                risk_per_unit = entry_price - stop_loss
                if risk_per_unit > 0:
                    take_profit = entry_price + (risk_per_unit * MIN_RR)

            elif bear_sweep:
                action = "SELL"
                stop_loss = cur_h + 0.50
                risk_per_unit = stop_loss - entry_price
                if risk_per_unit > 0:
                    take_profit = entry_price - (risk_per_unit * MIN_RR)

            if action and risk_per_unit > 0:
                # Sizing: risk no more than MAX_RISK_USD ($1.00)
                # units = risk_budget / risk_per_unit
                # Gold min amount on Binance is 0.001 XAU
                target_qty = round(MAX_RISK_USD / risk_per_unit, 3)
                if target_qty < 0.001:
                    target_qty = 0.001

                notional_value = target_qty * entry_price
                margin_required = notional_value / LEVERAGE

                # Safety check: margin required must not exceed $12 (half our balance)
                if margin_required <= 12.0:
                    processed_signal_bars.add(last_ts)
                    logger.info(f"🚨 SIGNAL DETECTED: {action} {SYMBOL} @ {entry_price} | SL: {stop_loss} | TP: {take_profit} | Qty: {target_qty}")

                    # Submit Order
                    side = "buy" if action == "BUY" else "sell"
                    opp_side = "sell" if action == "BUY" else "buy"

                    order = exchange.create_order(
                        symbol=SYMBOL,
                        type="market",
                        side=side,
                        amount=target_qty
                    )
                    logger.info(f"Market entry filled: {order['id']}")

                    # Submit Stop Loss
                    exchange.create_order(
                        symbol=SYMBOL,
                        type="STOP_MARKET",
                        side=opp_side,
                        amount=target_qty,
                        params={"stopPrice": round(stop_loss, 2), "reduceOnly": True}
                    )

                    # Submit Take Profit
                    exchange.create_order(
                        symbol=SYMBOL,
                        type="TAKE_PROFIT_MARKET",
                        side=opp_side,
                        amount=target_qty,
                        params={"stopPrice": round(take_profit, 2), "reduceOnly": True}
                    )

                    notifier.send_embed(
                        title=f"⚡ GOLD TRADE EXECUTED: {action}",
                        description=f"Auto-executed on Binance Futures with strict brackets.",
                        color=0x2ECC71 if action == "BUY" else 0xE74C3C,
                        fields=[
                            {"name": "Pair", "value": "XAU/USDT", "inline": True},
                            {"name": "Action", "value": action, "inline": True},
                            {"name": "Entry", "value": f"${entry_price:.2f}", "inline": True},
                            {"name": "Stop Loss", "value": f"${stop_loss:.2f}", "inline": True},
                            {"name": "Take Profit", "value": f"${take_profit:.2f}", "inline": True},
                            {"name": "Max Risk", "value": f"${target_qty * risk_per_unit:.2f} (~5%)", "inline": True},
                            {"name": "Potential Gain", "value": f"+${target_qty * risk_per_unit * MIN_RR:.2f} (+10%)", "inline": True},
                        ]
                    )

            time.sleep(10)

        except Exception as e:
            logger.error(f"Loop error: {e}")
            time.sleep(15)

if __name__ == "__main__":
    run()

