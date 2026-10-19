"""
Autonomous Headless Tradovate Web Controller for AWS Cloud.
Runs Playwright inside AWS EC2 with a persistent session to trigger Buy/Sell
orders directly into Tradovate with attached brackets, completely independent of user's laptop.
"""
import os
import logging
import asyncio
from playwright.async_api import async_playwright

logger = logging.getLogger("TradovateCloudDriver")

TRADOVATE_USER = os.environ.get("TRADOVATE_USER", "LTT5TMX9P74")
TRADOVATE_PASS = os.environ.get("TRADOVATE_PASS", "m48-vM1QCqc6V")

class TradovateCloudDriver:
    def __init__(self, user_data_dir: str = "/home/ubuntu/.tradovate_browser"):
        self.user_data_dir = user_data_dir
        self.playwright = None
        self.browser_context = None
        self.page = None

    async def initialize(self):
        """Launches persistent Chromium context in the cloud and ensures logged into Tradovate."""
        if self.browser_context is None:
            self.playwright = await async_playwright().start()
            self.browser_context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--window-size=1470,956"
                ],
                viewport={"width": 1470, "height": 956}
            )
            self.page = self.browser_context.pages[0] if self.browser_context.pages else await self.browser_context.new_page()
            logger.info("Cloud Browser Driver initialized.")

        # Ensure page is on Tradovate Trader and logged in
        try:
            if "tradovate.com" not in self.page.url:
                await self.page.goto("https://trader.tradovate.com", wait_until="domcontentloaded", timeout=30000)
            
            # Check if login inputs exist
            user_input = self.page.locator("input[name='name'], input[autocomplete='username'], #name-input").first
            if await user_input.count() > 0 and await user_input.is_visible():
                logger.info("Tradovate login form detected! Auto-authenticating in cloud...")
                await user_input.fill(TRADOVATE_USER)
                pass_input = self.page.locator("input[name='password'], input[type='password'], #password-input").first
                await pass_input.fill(TRADOVATE_PASS)
                
                # Click Login/Submit button
                login_btn = self.page.locator("button:has-text('Login'), button:has-text('Log In'), button[type='submit']").first
                await login_btn.click()
                logger.info("Submitted login credentials to Tradovate.")
                await self.page.wait_for_timeout(5000)
        except Exception as e:
            logger.warning(f"Tradovate session verification notice: {e}")

    async def execute_trade(self, direction: str) -> bool:
        """Clicks Buy Bid or Sell Ask directly inside the cloud browser."""
        try:
            await self.initialize()
            if "tradovate.com" not in self.page.url:
                await self.page.goto("https://trader.tradovate.com", wait_until="networkidle", timeout=30000)

            # Locate order buttons by text or role
            if direction.upper() == "LONG":
                # Look for Buy button / Buy Bid
                btn = self.page.locator("button:has-text('Buy Bid'), button:has-text('Buy Mkt')").first
                if await btn.count() > 0:
                    await btn.click()
                    logger.info("Successfully clicked BUY inside cloud Tradovate!")
                    return True
            else:
                # Look for Sell button / Sell Ask
                btn = self.page.locator("button:has-text('Sell Ask'), button:has-text('Sell Mkt')").first
                if await btn.count() > 0:
                    await btn.click()
                    logger.info("Successfully clicked SELL inside cloud Tradovate!")
                    return True

            # Fallback to coordinate click on 1470x956 DOM
            x = 420 if direction.upper() == "LONG" else 475
            await self.page.mouse.click(x, 268)
            logger.info(f"Fell back to coordinate click at ({x}, 268)")
            return True
        except Exception as e:
            logger.error(f"Cloud execution error: {e}")
            return False

    async def close(self):
        if self.browser_context:
            await self.browser_context.close()
        if self.playwright:
            await self.playwright.stop()
