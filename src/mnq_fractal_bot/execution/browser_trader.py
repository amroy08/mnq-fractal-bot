import asyncio
import logging
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class TradovateWebTrader:
    """
    Automated browser bridge for Tradovate Web.
    Directly operates the Buy/Sell DOM buttons with pre-configured brackets.
    """

    def __init__(self, cdp_url: str = "http://127.0.0.1:9222"):
        self.cdp_url = cdp_url
        self.browser = None
        self.page = None

    async def connect_to_browser(self) -> bool:
        """Connects to the active Chrome session via Chrome DevTools Protocol."""
        try:
            pw = await async_playwright().start()
            self.browser = await pw.chromium.connect_over_cdp(self.cdp_url)
            
            # Find the active Tradovate tab
            for context in self.browser.contexts:
                for page in context.pages:
                    if "tradovate.com" in page.url:
                        self.page = page
                        logger.info(f"Found active Tradovate tab: {page.url}")
                        return True
            logger.warning("No open Tradovate tab found on Chrome port 9222")
            return False
        except Exception as e:
            logger.error(f"Could not connect to Chrome CDP: {e}")
            return False

    async def click_buy_bid(self) -> bool:
        """Clicks the Buy Bid button in Tradovate."""
        if not self.page:
            return False
        try:
            btn = self.page.locator('button:has-text("Buy Bid")').first
            if await btn.is_visible():
                await btn.click()
                logger.info("Successfully clicked [Buy Bid] with attached bracket!")
                return True
        except Exception as e:
            logger.error(f"Error clicking Buy Bid: {e}")
        return False

    async def click_sell_ask(self) -> bool:
        """Clicks the Sell Ask button in Tradovate."""
        if not self.page:
            return False
        try:
            btn = self.page.locator('button:has-text("Sell Ask")').first
            if await btn.is_visible():
                await btn.click()
                logger.info("Successfully clicked [Sell Ask] with attached bracket!")
                return True
        except Exception as e:
            logger.error(f"Error clicking Sell Ask: {e}")
        return False

    async def click_exit_market(self) -> bool:
        """Emergency circuit breaker: Flatten position immediately."""
        if not self.page:
            return False
        try:
            btn = self.page.locator('button:has-text("Exit at Mkt & Cxl")').first
            if await btn.is_visible():
                await btn.click()
                logger.info("Emergency exit clicked!")
                return True
        except Exception as e:
            logger.error(f"Error clicking Exit: {e}")
        return False
