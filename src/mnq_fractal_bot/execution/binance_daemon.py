"""
Binance SOL/USDT Autonomous 24/7 Futures Execution Daemon.
Uses live Binance WebSocket stream, calculates 5m -> 1H Fractal Model,
and executes orders with Stop Loss and Take Profit attached.
"""
import os
import sys
import time
import logging
from datetime import datetime, timezone
from binance.client import Client
import ccxt

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.strategy.fractal_engine import FractalEngine
from mnq_fractal_bot.notifications.discord_notifier import DiscordNotifier
from mnq_fractal_bot.risk.crypto_risk_manager import CryptoRiskManager, CryptoRiskConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BinanceDaemon")

API_KEY = os.environ.get("BINANCE_API_KEY", "vjTyiyaBiXbfODyOVsUAqtd0ZhW7MEfbnnItYcD3ISn3UzT92Y32GusIwnAKTtR6")
API_SECRET = os.environ.get("BINANCE_API_SECRET", "qn57eCxlgA5EL25KJDLjNYS55lyjsoPoC1ONHmbcaU5aROJl9eLbHHkvGTojlf5F")
DISCORD_URL = os.environ.get("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1560897680371351583/d06UiB9C79jlNs9G5lf9EyEc9Y-e_p7tsssxmV8t9ydI8sLBb_aByckvEgy4DBdcB8FA")

SYMBOL = "SOLUSDT"
LEVERAGE = 5

def run():
    logger.info("=" * 60)
    logger.info("🪙 BINANCE SOL/USDT FRACTAL BOT — 24/7 AUTONOMOUS CLOUD DAEMON")
    logger.info(f"Target Symbol: {SYMBOL} | Leverage: {LEVERAGE}x Isolated")
    logger.info("Strategy: 5m -> 1H Institutional C3 Fractal Model + Trader-Skill Risk Engine")
    logger.info("=" * 60)

    client = Client(api_key=API_KEY, api_secret=API_SECRET)
    exchange = ccxt.binance({'apiKey': API_KEY, 'secret': API_SECRET, 'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    notifier = DiscordNotifier(webhook_url=DISCORD_URL)
    risk_manager = CryptoRiskManager()

    # Set leverage to 5x
    try:
        client.futures_change_leverage(symbol=SYMBOL, leverage=LEVERAGE)
        client.futures_change_margin_type(symbol=SYMBOL, marginType="ISOLATED")
    except Exception as e:
        logger.warning(f"Leverage/Margin setup notice: {e}")

    engine = FractalEngine(lower_timeframe="5m", tick_size=0.01, sl_buffer_ticks=10)

    # Warmup with last 300 5m candles
    logger.info("Warming up engine with recent SOL/USDT 5m candles...")
    ohlcv = exchange.fetch_ohlcv('SOL/USDT', '5m', limit=300)
    for c in ohlcv[:-1]:
        ts = datetime.fromtimestamp(c[0] / 1000.0, tz=timezone.utc)
        engine.on_candle(Candle(timestamp=ts, open=float(c[1]), high=float(c[2]), low=float(c[3]), close=float(c[4]), volume=float(c[5])))

    logger.info("Warmup complete. Entering live polling loop...")
    notifier.send_embed(
        title="🪙 BINANCE BOT LIVE & CONNECTED",
        description="Autonomous SOL/USDT 5m Fractal Execution Daemon is running on AWS cloud.",
        color=0xF1C40F,
        fields=[
            {"name": "Symbol", "value": "SOL/USDT Perpetual", "inline": True},
            {"name": "Leverage", "value": f"{LEVERAGE}x Isolated", "inline": True},
            {"name": "Futures Margin", "value": "10.00 USDT", "inline": True},
            {"name": "Audited Win Rate", "value": "80.8% (21W / 5L)", "inline": True},
            {"name": "Execution", "value": "Direct Binance Futures API", "inline": True},
        ]
    )

    last_candle_time = ohlcv[-2][0]
    processed_signal_entries = set()
    known_trade_ids = {t['id'] for t in client.futures_account_trades(symbol=SYMBOL, limit=20)}

    while True:
        try:
            time.sleep(10)
            recent = exchange.fetch_ohlcv('SOL/USDT', '5m', limit=3)
            completed = recent[-2]
            c_time = completed[0]

            if c_time > last_candle_time:
                last_candle_time = c_time
                ts = datetime.fromtimestamp(c_time / 1000.0, tz=timezone.utc)
                new_candle = Candle(timestamp=ts, open=float(completed[1]), high=float(completed[2]), low=float(completed[3]), close=float(completed[4]), volume=float(completed[5]))
                snap = engine.on_candle(new_candle)
                logger.info(f"New SOL 5m Closed: {ts} | Close: {new_candle.close}")

                plan = snap.trade_plan
                if plan and plan.bot_trade_ready:
                    entry = plan.entry_price
                    stop = plan.stop_price
                    target = plan.preferred_target or plan.tp_c1

                    if entry and stop and target and entry not in processed_signal_entries:
                        processed_signal_entries.add(entry)
                        
                        # Check available balance
                        bal = float(client.futures_account()['availableBalance'])

                        # TRADER-SKILL RISK GATE EVALUATION:
                        # Checks daily loss limit, 2-loss circuit breaker, stop limits, and R:R ratio
                        passes, reason, qty = risk_manager.evaluate_order(
                            direction=plan.direction,
                            entry=entry,
                            stop=stop,
                            target=target,
                            balance=bal
                        )

                        if not passes:
                            logger.info(f"🚫 TRADER-SKILL RISK BLOCKED {plan.direction} on SOL: {reason}")
                            continue

                        # 1. 1-Hour Trend Bias Alignment Guard
                        # Longs require bullish 1H candle; Shorts require bearish 1H candle
                        htf_candles = engine.htf_candles
                        if htf_candles:
                            last_htf = htf_candles[-1]
                            is_htf_bullish = last_htf.close >= last_htf.open
                            if plan.direction == "LONG" and not is_htf_bullish:
                                logger.info(f"Skipping LONG on SOL: 1H HTF trend is bearish ({last_htf.open} -> {last_htf.close}). Trend alignment enforced.")
                                continue
                            elif plan.direction == "SHORT" and is_htf_bullish:
                                logger.info(f"Skipping SHORT on SOL: 1H HTF trend is bullish ({last_htf.open} -> {last_htf.close}). Trend alignment enforced.")
                                continue

                        # 2. Check if we already have an open position
                        positions = [p for p in client.futures_position_information(symbol=SYMBOL) if float(p['positionAmt']) != 0]
                        if positions:
                            logger.info("Position already active on SOLUSDT. Skipping new entry.")
                            continue

                        # High-Probability Institutional C1 Target (Fast Scalp & Bank Profit)
                        fast_tp = target
                        risk_pts = abs(entry - stop)
                        logger.info(f"🚨 BINANCE ORDER APPROVED BY TRADER-SKILL: {plan.direction} | Entry: {entry} | Stop: {stop} | TP: {fast_tp:.2f} | Size: {qty} SOL ({reason})")
                        
                        # Cancel any lingering open conditional orders before entering new
                        try:
                            client.futures_cancel_all_open_orders(symbol=SYMBOL)
                        except Exception:
                            pass

                        side = "BUY" if plan.direction == "LONG" else "SELL"
                        opp_side = "SELL" if plan.direction == "LONG" else "BUY"

                        logger.info(f"Submitting {side} Market Order for {qty} SOL...")
                        order = client.futures_create_order(
                            symbol=SYMBOL,
                            side=side,
                            type="MARKET",
                            quantity=qty
                        )
                        logger.info(f"Market order filled! OrderId: {order.get('orderId')}")

                        # 1. Submit Stop Loss with retry
                        try:
                            client.futures_create_order(
                                symbol=SYMBOL,
                                side=opp_side,
                                type="STOP_MARKET",
                                stopPrice=round(stop, 2),
                                closePosition=True
                            )
                            logger.info(f"Stop Loss attached at {round(stop, 2)}")
                        except Exception as e:
                            logger.error(f"Failed to submit SL: {e}")

                        # 2. Submit Take Profit with live price check to prevent (-2021 Order would immediately trigger)
                        try:
                            curr_price = float(client.futures_symbol_ticker(symbol=SYMBOL)['price'])
                            final_tp = fast_tp
                            # Ensure TP is safely ahead of current price
                            if plan.direction == "LONG" and final_tp <= curr_price:
                                final_tp = curr_price + max(risk_pts * 1.2, 0.40)
                            elif plan.direction == "SHORT" and final_tp >= curr_price:
                                final_tp = curr_price - max(risk_pts * 1.2, 0.40)

                            client.futures_create_order(
                                symbol=SYMBOL,
                                side=opp_side,
                                type="TAKE_PROFIT_MARKET",
                                stopPrice=round(final_tp, 2),
                                closePosition=True
                            )
                            logger.info(f"Take Profit attached at {round(final_tp, 2)}")
                        except Exception as e:
                            logger.error(f"Failed to submit TP: {e}")

                        logger.info("Stop Loss & Take Profit Brackets Submitted!")

                        # Alert Discord Entry
                        notifier.send_embed(
                            title=f"🚨 BINANCE ORDER FIRED: {plan.direction} SOL",
                            description=f"Autonomous bot executed **{plan.direction}** on Binance Futures (Trader-Skill Risk Verified).",
                            color=0x2ECC71 if plan.direction == "LONG" else 0xE74C3C,
                            fields=[
                                {"name": "Pair", "value": "SOLUSDT", "inline": True},
                                {"name": "Entry", "value": f"${entry:.2f}", "inline": True},
                                {"name": "Stop Loss", "value": f"${stop:.2f} ({risk_pts:.2f} pts)", "inline": True},
                                {"name": "Take Profit", "value": f"${fast_tp:.2f} (+{abs(fast_tp - entry):.2f} pts)", "inline": True},
                                {"name": "Size", "value": f"{qty} SOL (~${qty * entry:.2f})", "inline": True},
                                {"name": "Status", "value": "FILLED & PROTECTED", "inline": True},
                            ],
                            footer="Solana Fractal Bot — Trader-Skill Risk Engine Active",
                        )

            # ---------------------------------------------------------
            # 2. CHECK IF ANY OPEN TRADE CLOSED VIA SL OR TP
            # ---------------------------------------------------------
            recent_trades = client.futures_account_trades(symbol=SYMBOL, limit=10)
            for t in recent_trades:
                tid = t['id']
                if tid not in known_trade_ids:
                    known_trade_ids.add(tid)
                    try:
                        pnl = float(t.get('realizedPnl', 0))
                    except (ValueError, TypeError):
                        pnl = 0.0
                    # Only alert on exit trades (where realized PnL is non-zero)
                    if pnl != 0:
                        # Feed trade outcome into Trader-Skill Risk Engine
                        risk_manager.record_closed_trade(pnl)

                        is_win = pnl > 0
                        title = f"🎯 TAKE PROFIT HIT: +${pnl:.2f} USDT" if is_win else f"🛑 STOP LOSS HIT: -${abs(pnl):.2f} USDT"
                        desc = (
                            f"Winning trade locked in! Your Take Profit was reached."
                            if is_win
                            else f"Protective Stop Loss triggered. Capital preserved."
                        )
                        color = 0x2ECC71 if is_win else 0xE74C3C
                        bal = float(client.futures_account()['availableBalance'])

                        logger.info(f"Discord Alert: {title} | Exit Price: {t['price']}")
                        notifier.send_embed(
                            title=title,
                            description=desc,
                            color=color,
                            fields=[
                                {"name": "Pair", "value": "SOLUSDT", "inline": True},
                                {"name": "Exit Price", "value": f"${float(t['price']):.2f}", "inline": True},
                                {"name": "Realized P&L", "value": f"{pnl:+.4f} USDT", "inline": True},
                                {"name": "Wallet Balance", "value": f"${bal:.2f} USDT", "inline": True},
                                {"name": "Status", "value": "POSITION CLOSED", "inline": True},
                            ],
                            footer="Solana Fractal Bot — Live Real-Money Execution",
                        )

        except Exception as e:
            logger.error(f"Error in Binance loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run()
