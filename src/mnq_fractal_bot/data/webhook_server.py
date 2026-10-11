import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Callable

from mnq_fractal_bot.execution.bot_runner import BotRunner
from mnq_fractal_bot.execution.stream_session import PaperStreamSession, StreamEvent
from mnq_fractal_bot.models.candle import Candle

logger = logging.getLogger(__name__)


def parse_candle_payload(payload: dict) -> Candle:
    """
    Parse a JSON payload into a Candle object.
    Supports standard TradingView alert webhook format:
    {
        "time": "2026-10-11T12:00:00Z" (or "timestamp" or numeric unix ms),
        "open": 31200.0,
        "high": 31220.5,
        "low": 31195.0,
        "close": 31215.25,
        "volume": 2500
    }
    """
    raw_time = payload.get("time") or payload.get("timestamp")
    if raw_time is None:
        raise ValueError("Missing 'time' or 'timestamp' in candle payload.")

    if isinstance(raw_time, (int, float)):
        # If timestamp is in milliseconds (> 1e11)
        if raw_time > 1e11:
            raw_time = raw_time / 1000.0
        ts = datetime.fromtimestamp(raw_time, tz=timezone.utc)
    elif isinstance(raw_time, str):
        cleaned = raw_time.strip()
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        ts = datetime.fromisoformat(cleaned)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    else:
        raise TypeError(f"Unsupported timestamp type: {type(raw_time)}")

    return Candle(
        timestamp=ts,
        open=float(payload["open"]),
        high=float(payload["high"]),
        low=float(payload["low"]),
        close=float(payload["close"]),
        volume=float(payload.get("volume", 0.0)),
    )


class WebhookServer(HTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        stream_session: PaperStreamSession,
        secret_token: str | None = None,
    ):
        super().__init__(server_address, WebhookHandler)
        self.stream_session = stream_session
        self.secret_token = secret_token
        self.received_candles_count = 0


class WebhookHandler(BaseHTTPRequestHandler):
    server: WebhookServer  # Type hint

    def do_POST(self):
        # 1. Check path
        if self.path != "/webhook/candle":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Not Found"}')
            return

        # 2. Check auth token if configured
        if self.server.secret_token:
            auth_header = self.headers.get("X-Auth-Token")
            if auth_header != self.server.secret_token:
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'{"error": "Unauthorized"}')
                return

        # 3. Read body
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Empty body"}')
            return

        body = self.rfile.read(content_length).decode("utf-8")
        try:
            payload = json.loads(body)
            candle = parse_candle_payload(payload)
            stream_event = self.server.stream_session.process_candle(candle)
            self.server.received_candles_count += 1

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            response = {
                "status": "success",
                "candle_time": candle.timestamp.isoformat(),
                "is_live_step": stream_event.is_live_step,
                "order_submitted": stream_event.snapshot.order_submitted,
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))

        except Exception as e:
            logger.exception("Error processing webhook candle")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def log_message(self, format, *args):
        # Silence default stderr logging during normal runs
        pass
