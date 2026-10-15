import logging
import subprocess
import time
import pyautogui

logger = logging.getLogger(__name__)

class TradovateAutoClicker:
    """
    Hands-free UI controller for Tradovate Web.
    Activates Chrome and triggers orders while attached to the 'MNQ Fractal 25K' bracket.
    """

    def __init__(self):
        # Target coordinate offsets based on standard 1470x956 fullscreen Tradovate layout
        # Chart order bar buttons:
        # Buy Bid: x=420, y=268
        # Sell Ask: x=475, y=268
        # Exit at Mkt & Cxl: x=675, y=232
        self.buy_bid_pos = (420, 268)
        self.sell_ask_pos = (475, 268)
        self.exit_pos = (675, 232)

    def activate_tradovate(self) -> bool:
        """Brings Tradovate window to front if on macOS, or bypasses on Linux/Xvfb."""
        import sys
        if sys.platform != "darwin":
            # On Linux (AWS EC2 Xvfb), the virtual display is always dedicated to Chrome
            return True

        script = '''
        tell application "Google Chrome" to activate
        tell application "System Events"
            tell process "Google Chrome"
                set frontmost to true
            end tell
        end tell
        '''
        try:
            subprocess.run(["osascript", "-e", script], check=True, timeout=5)
            time.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Failed to focus Tradovate window: {e}")
            return False

    def click_buy(self) -> bool:
        """Executes a Buy order with the pre-attached bracket."""
        if not self.activate_tradovate():
            return False
        logger.info(f"Triggering automated BUY at {self.buy_bid_pos}...")
        pyautogui.click(self.buy_bid_pos[0], self.buy_bid_pos[1])
        return True

    def click_sell(self) -> bool:
        """Executes a Sell order with the pre-attached bracket."""
        if not self.activate_tradovate():
            return False
        logger.info(f"Triggering automated SELL at {self.sell_ask_pos}...")
        pyautogui.click(self.sell_ask_pos[0], self.sell_ask_pos[1])
        return True

    def emergency_flatten(self) -> bool:
        """Clicks Exit at Market & Cancel All."""
        if not self.activate_tradovate():
            return False
        logger.info("Executing Emergency Flatten...")
        pyautogui.click(self.exit_pos[0], self.exit_pos[1])
        return True
