import json
import logging
from dataclasses import dataclass
from typing import Any
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiscordNotificationResult:
    success: bool
    status_code: int | None = None
    error: str | None = None


class DiscordNotifier:
    """
    Sends formatted trade alert embeds to a Discord channel via Webhook.
    Works in paper simulation with zero external dependencies (uses standard urllib).
    """

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url.strip() if webhook_url else None

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url and self.webhook_url.startswith("https://discord.com/api/webhooks/"))

    def send_embed(
        self,
        title: str,
        description: str,
        color: int = 0x3498DB,  # Default blue
        fields: list[dict[str, Any]] | None = None,
        footer: str = "MNQ Fractal Bot — Paper Trading",
    ) -> DiscordNotificationResult:
        if not self.is_configured:
            return DiscordNotificationResult(
                success=False,
                error="Discord webhook URL not configured or invalid.",
            )

        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": description,
                    "color": color,
                    "fields": fields or [],
                    "footer": {"text": footer},
                }
            ]
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "MNQ-Fractal-Bot/1.0",
            },
            method="POST",
        )

        try:
            import ssl
            try:
                import certifi
                ssl_ctx = ssl.create_default_context(cafile=certifi.where())
            except Exception:
                ssl_ctx = ssl.create_default_context()

            with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as response:
                return DiscordNotificationResult(
                    success=response.status in (200, 204),
                    status_code=response.status,
                )
        except urllib.error.HTTPError as e:
            logger.warning(f"Discord webhook failed with HTTP {e.code}: {e.reason}")
            return DiscordNotificationResult(
                success=False,
                status_code=e.code,
                error=str(e),
            )
        except Exception as e:
            logger.warning(f"Discord webhook error: {e}")
            return DiscordNotificationResult(
                success=False,
                error=str(e),
            )

    def notify_order_submitted(
        self,
        signal_id: str,
        direction: str,
        entry_price: float,
        stop_price: float,
        target_price: float,
        timestamp_str: str,
    ) -> DiscordNotificationResult:
        stop_dist = abs(entry_price - stop_price)
        target_dist = abs(entry_price - target_price)
        color = 0x2ECC71 if direction.upper() == "LONG" else 0xE74C3C

        fields = [
            {"name": "Direction", "value": f"**{direction.upper()}**", "inline": True},
            {"name": "Limit Entry", "value": f"`{entry_price:.2f}`", "inline": True},
            {"name": "Stop Loss", "value": f"`{stop_price:.2f}` ({stop_dist:.2f} pts)", "inline": True},
            {"name": "Profit Target", "value": f"`{target_price:.2f}` ({target_dist:.2f} pts)", "inline": True},
            {"name": "Time", "value": timestamp_str, "inline": True},
        ]

        return self.send_embed(
            title="📝 [PAPER] Order Submitted",
            description=f"Signal ID: `{signal_id}`",
            color=color,
            fields=fields,
        )

    def notify_entry_filled(
        self,
        signal_id: str,
        fill_price: float,
        timestamp_str: str,
    ) -> DiscordNotificationResult:
        fields = [
            {"name": "Fill Price", "value": f"`{fill_price:.2f}`", "inline": True},
            {"name": "Time", "value": timestamp_str, "inline": True},
        ]
        return self.send_embed(
            title="🟢 [PAPER] Entry Filled",
            description=f"Position opened for `{signal_id}`",
            color=0x2ECC71,
            fields=fields,
        )

    def notify_trade_closed(
        self,
        signal_id: str,
        exit_reason: str,
        exit_price: float,
        gross_pnl: float,
        timestamp_str: str,
    ) -> DiscordNotificationResult:
        is_win = gross_pnl > 0
        is_scratch = gross_pnl == 0
        if is_win:
            emoji = "🎯"
            title = "TARGET HIT — WIN"
            color = 0x2ECC71  # Green
        elif is_scratch:
            emoji = "⚖️"
            title = "SCRATCH / BREAK-EVEN"
            color = 0xF1C40F  # Gold
        else:
            emoji = "🛑"
            title = "STOP HIT — LOSS"
            color = 0xE74C3C  # Red

        if exit_reason == "TIME_STOP":
            title = f"⏱️ TIME-STOP ({'WIN' if is_win else 'SCRATCH' if is_scratch else 'LOSS'})"

        sign = "+" if gross_pnl > 0 else ""
        fields = [
            {"name": "Exit Price", "value": f"`{exit_price:.2f}`", "inline": True},
            {"name": "Gross P&L", "value": f"**{sign}${gross_pnl:.2f}**", "inline": True},
            {"name": "Exit Reason", "value": f"`{exit_reason}`", "inline": True},
            {"name": "Time", "value": timestamp_str, "inline": True},
        ]

        return self.send_embed(
            title=f"{emoji} [PAPER] {title}",
            description=f"Trade closed for `{signal_id}`",
            color=color,
            fields=fields,
        )
