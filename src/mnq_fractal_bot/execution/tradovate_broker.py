import json
import logging
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from mnq_fractal_bot.execution.paper_broker import BrokerEvent
from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.strategy.trade_plan import TradePlan

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TradovateConfig:
    username: str
    password: str
    app_id: str = "MNQFractalBot"
    app_version: str = "1.0"
    cid: int = 0
    sec: str = ""
    account_spec: str = "LFE02592063680001"
    base_url: str = "https://live-api.staging.ninjatrader.dev/v1"  # Tradovate Prop / Simulation endpoint
    symbol: str = "MNQZ6"
    device_id: str | None = None


class TradovateClient:
    """
    Direct REST API client for Tradovate order routing and account surveillance.
    Supports OAuth access token generation, OSO bracket orders, and account status checks.
    """

    def __init__(self, config: TradovateConfig):
        self.config = config
        self.device_id = config.device_id or str(uuid.uuid4())
        self.access_token: str | None = None
        self.token_expiry: datetime | None = None
        self.account_id: int | None = None

    def authenticate(self) -> bool:
        """Requests OAuth bearer token from Tradovate."""
        auth_url = f"{self.config.base_url}/auth/accesstokenrequest"
        payload = {
            "name": self.config.username,
            "password": self.config.password,
            "appId": self.config.app_id,
            "appVersion": self.config.app_version,
            "cid": self.config.cid,
            "sec": self.config.sec,
            "deviceId": self.device_id,
        }

        req = urllib.request.Request(
            auth_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self.access_token = data.get("accessToken")
                if self.access_token:
                    logger.info("Successfully authenticated with Tradovate API")
                    # Fetch numeric account ID for accountSpec
                    self._resolve_account_id()
                    return True
                else:
                    logger.error(f"Tradovate auth returned no token: {data}")
                    return False
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            logger.error(f"Tradovate auth failed ({e.code}): {err_body}")
            return False
        except Exception as e:
            logger.error(f"Tradovate connection error: {e}")
            return False

    def _ensure_authenticated(self) -> bool:
        if not self.access_token:
            return self.authenticate()
        return True

    def _resolve_account_id(self) -> None:
        """Fetches account list to match accountSpec string with numeric accountId."""
        url = f"{self.config.base_url}/account/list"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                accounts = json.loads(resp.read().decode("utf-8"))
                for acc in accounts:
                    if acc.get("name") == self.config.account_spec:
                        self.account_id = acc.get("id")
                        logger.info(f"Mapped account {self.config.account_spec} -> ID {self.account_id}")
                        break
        except Exception as e:
            logger.warning(f"Could not resolve account list: {e}")

    def place_bracket_order(
        self,
        action: str,  # "Buy" or "Sell"
        entry_price: float,
        stop_price: float,
        target_price: float,
        qty: int = 1,
    ) -> dict[str, Any] | None:
        """
        Submits an OSO (Order Sends Order) bracket order:
        - Primary: Limit entry
        - Bracket 1: Limit take-profit
        - Bracket 2: Stop-loss
        """
        if not self._ensure_authenticated():
            logger.error("Cannot place order: Not authenticated with Tradovate")
            return None

        exit_action = "Sell" if action.lower() == "buy" else "Buy"

        payload = {
            "accountSpec": self.config.account_spec,
            "accountId": self.account_id or 0,
            "action": action.capitalize(),
            "symbol": self.config.symbol,
            "orderQty": qty,
            "orderType": "Limit",
            "price": entry_price,
            "isAutomated": True,
            "bracket1": {
                "action": exit_action,
                "orderType": "Limit",
                "price": target_price,
            },
            "bracket2": {
                "action": exit_action,
                "orderType": "Stop",
                "stopPrice": stop_price,
            },
        }

        url = f"{self.config.base_url}/order/placeoso"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                logger.info(f"Tradovate Bracket Order Submitted: {res}")
                return res
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8")
            logger.error(f"Tradovate placeoso failed ({e.code}): {err}")
            return None
        except Exception as e:
            logger.error(f"Tradovate order exception: {e}")
            return None

    def cancel_order(self, order_id: int) -> bool:
        """Cancels an active pending order."""
        if not self._ensure_authenticated():
            return False

        url = f"{self.config.base_url}/order/cancelorder"
        payload = {"orderId": order_id}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info(f"Tradovate Cancel Order {order_id} successful")
                return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False


class TradovateLiveBroker:
    """
    Adapter implementing the broker interface required by BotRunner,
    routing real live execution into Tradovate.
    """

    def __init__(self, client: TradovateClient):
        self.client = client
        self.active_order_id: int | None = None
        self.pending_order = None
        self.position = None
        self.closed_trades: list[Any] = []

    def submit_trade_plan(
        self,
        plan: TradePlan,
        signal_id: str,
        expires_at: datetime | None = None,
    ) -> bool:
        action = "Buy" if plan.direction == "LONG" else "Sell"
        res = self.client.place_bracket_order(
            action=action,
            entry_price=plan.entry_price,
            stop_price=plan.stop_price,
            target_price=plan.preferred_target,
            qty=1,
        )
        if res and "orderId" in res:
            self.active_order_id = res["orderId"]
            return True
        return False

    def cancel_pending_order(self) -> BrokerEvent | None:
        if self.active_order_id is not None:
            self.client.cancel_order(self.active_order_id)
            self.active_order_id = None
        return None

    def on_candle(self, candle: Candle) -> BrokerEvent | None:
        # Fills and exits are managed natively by Tradovate's OSO bracket engine
        return None
