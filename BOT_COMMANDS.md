# 🚀 MNQ Fractal Bot — Quick Command Guide

This file contains all the commands you need to manage your 24/7 trading bot and laptop sleep settings.

---

## 1. Bot Controls (Start, Stop, Status)

### 🔴 Stop / Kill the Trading Bot
Run this whenever you want to completely stop the bot:
```bash
pkill -f live_daemon.py
```

### 🟢 Start the Trading Bot
Run this in your terminal to start the bot in the background:
```bash
cd /Users/amroy/Desktop/mnq-fractal-bot
nohup /opt/anaconda3/bin/python -m mnq_fractal_bot.execution.live_daemon > bot_live.log 2>&1 &
```

### 🔍 Check if the Bot is Running
```bash
ps aux | grep live_daemon | grep -v grep
```

### 📜 View Live Bot Logs (Every 5m candle, setups, orders)
Press `Ctrl + C` anytime to exit the view:
```bash
tail -f /Users/amroy/Desktop/mnq-fractal-bot/bot_live.log
```

---

## 2. Laptop Sleep Controls (Clamshell Mode)

### 🌙 Restore Normal Sleep (When you're NOT trading)
Use this command to allow your Mac to sleep normally when you close the lid:
```bash
echo "billion" | sudo -S pmset -a disablesleep 0
```

### ⚡ Enable 24/7 Clamshell Mode (Trading with lid closed)
Use this command to keep your Mac 100% awake with the lid closed (must be charging):
```bash
echo "billion" | sudo -S pmset -a disablesleep 1
```

### 🔎 Check Current Sleep Setting
```bash
pmset -g live | grep -i sleep
```
- `SleepDisabled 1`: Mac will **stay awake** with lid closed.
- `SleepDisabled 0`: Mac will **sleep** when lid is closed.

---

## 3. Emergency All-in-One Kill Switch
To immediately stop all trading AND restore normal laptop sleep in one go:
```bash
pkill -f live_daemon.py
pkill -f caffeinate
echo "billion" | sudo -S pmset -a disablesleep 0
echo "Bot stopped and normal sleep restored."
```
