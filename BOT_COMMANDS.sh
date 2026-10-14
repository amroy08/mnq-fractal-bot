# ==============================================================================
# MNQ FRACTAL BOT — CONTROL COMMANDS CHEATSHEET
# ==============================================================================
# Use these commands in your Mac Terminal whenever you want to check, stop,
# restart, or manage your 24/7 trading bot and laptop power settings.
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. BOT CONTROLS (START / STOP / STATUS)
# ------------------------------------------------------------------------------

# CHECK IF BOT IS CURRENTLY RUNNING:
ps aux | grep live_daemon | grep -v grep

# STOP / KILL THE TRADING BOT:
pkill -f live_daemon.py

# START THE TRADING BOT (Runs silently in background even if Terminal closes):
cd /Users/amroy/Desktop/mnq-fractal-bot
nohup /opt/anaconda3/bin/python -m mnq_fractal_bot.execution.live_daemon > bot_live.log 2>&1 &

# VIEW LIVE REAL-TIME LOGS OF THE BOT (Press Ctrl+C to exit):
tail -f /Users/amroy/Desktop/mnq-fractal-bot/bot_live.log


# ------------------------------------------------------------------------------
# 2. MAC POWER / SLEEP CONTROLS (CLAMSHELL MODE)
# ------------------------------------------------------------------------------

# CHECK CURRENT SLEEP STATUS:
# If it says 'SleepDisabled 1', your Mac will stay awake with lid closed.
# If it says 'SleepDisabled 0', standard sleep is restored.
pmset -g live | grep -i sleep

# ENABLE 24/7 CLAMSHELL MODE (Mac stays 100% awake with lid closed while charging):
# (Will ask for your Mac password: billion)
echo "billion" | sudo -S pmset -a disablesleep 1

# RESTORE NORMAL MAC SLEEP (Mac will sleep normally when lid is closed):
# (Will ask for your Mac password: billion)
echo "billion" | sudo -S pmset -a disablesleep 0


# ------------------------------------------------------------------------------
# 3. EMERGENCY KILL-SWITCH (TRADOVATE)
# ------------------------------------------------------------------------------

# IF YOU EVER WANT TO IMMEDIATELY STOP ALL TRADING AND RESTORE NORMAL LAPTOP SLEEP:
pkill -f live_daemon.py
pkill -f caffeinate
echo "billion" | sudo -S pmset -a disablesleep 0
echo "Bot stopped and normal sleep restored."
