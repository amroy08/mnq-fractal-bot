import json
import urllib.request
from datetime import datetime, timezone
from threading import Thread

from mnq_fractal_bot.data.webhook_server import WebhookServer
from mnq_fractal_bot.execution.bot_runner import BotRunner
from mnq_fractal_bot.execution.stream_session import PaperStreamSession


def test_webhook_server_http_flow():
    runner = BotRunner()
    session = PaperStreamSession(bot_runner=runner, warmup_candles=0)
    server = WebhookServer(("127.0.0.1", 0), stream_session=session, secret_token="test-secret")
    port = server.server_port

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}/webhook/candle"
    payload = json.dumps({
        "time": "2026-10-11T14:00:00Z",
        "open": 31000.0,
        "high": 31010.0,
        "low": 30990.0,
        "close": 31005.0,
        "volume": 1200,
    }).encode("utf-8")

    # 1. Test unauthorized (missing token)
    req_no_auth = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req_no_auth)
    except urllib.error.HTTPError as e:
        assert e.code == 401

    # 2. Test authorized POST
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Auth-Token": "test-secret",
        },
    )

    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        body = json.loads(resp.read().decode("utf-8"))
        assert body["status"] == "success"
        assert body["candle_time"] == "2026-10-11T14:00:00+00:00"

    assert server.received_candles_count == 1
    server.shutdown()
