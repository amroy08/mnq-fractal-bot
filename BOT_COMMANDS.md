# 🚀 MNQ Fractal Bot — Quick Command Guide

This file contains all the commands you need to manage your 24/7 trading bot and laptop sleep settings.

---

## 1. Bot Controls (Start, Stop, Auto-Start Service)

### ⚡ Auto-Start Service (LaunchAgent)
The bot is installed as an automatic macOS system service (`com.amroy.mnqfractalbot`). It starts automatically on boot/wake and restarts if it ever stops.

- **Check Service Status:**
  ```bash
  launchctl list | grep mnqfractalbot
  ```

- **Stop / Turn OFF Auto-Start Service:**
  ```bash
  launchctl unload ~/Library/LaunchAgents/com.amroy.mnqfractalbot.plist
  ```

- **Start / Turn ON Auto-Start Service:**
  ```bash
  launchctl load ~/Library/LaunchAgents/com.amroy.mnqfractalbot.plist
  ```

- **Emergency Kill (Stop All):**
  ```bash
  launchctl unload ~/Library/LaunchAgents/com.amroy.mnqfractalbot.plist
  pkill -f live_daemon.py
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
