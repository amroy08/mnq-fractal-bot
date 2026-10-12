from mnq_fractal_bot.notifications.discord_notifier import DiscordNotifier


def test_discord_notifier_not_configured():
    notifier = DiscordNotifier(webhook_url=None)
    assert not notifier.is_configured
    res = notifier.send_embed(title="Test", description="Test desc")
    assert not res.success
    assert "not configured" in (res.error or "")


def test_discord_notifier_configured_status():
    valid_url = "https://discord.com/api/webhooks/123456/abcdef"
    notifier = DiscordNotifier(webhook_url=valid_url)
    assert notifier.is_configured
    assert notifier.webhook_url == valid_url


def test_discord_notifier_invalid_url_prefix():
    invalid_url = "https://example.com/not-discord"
    notifier = DiscordNotifier(webhook_url=invalid_url)
    assert not notifier.is_configured


def test_discord_notifier_format_helpers(monkeypatch):
    notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/dummy/key")

    captured_payloads = []

    def mock_send(title, description, color, fields, footer="MNQ Fractal Bot — Paper Trading"):
        captured_payloads.append({
            "title": title,
            "description": description,
            "color": color,
            "fields": fields,
        })
        from mnq_fractal_bot.notifications.discord_notifier import DiscordNotificationResult
        return DiscordNotificationResult(success=True, status_code=204)

    monkeypatch.setattr(notifier, "send_embed", mock_send)

    # 1. Order submitted
    res1 = notifier.notify_order_submitted(
        signal_id="S:100:test",
        direction="LONG",
        entry_price=30000.0,
        stop_price=29975.0,
        target_price=30050.0,
        timestamp_str="2026-10-12 12:00 UTC",
    )
    assert res1.success
    assert len(captured_payloads) == 1
    assert "Order Submitted" in captured_payloads[0]["title"]
    assert captured_payloads[0]["color"] == 0x2ECC71

    # 2. Entry filled
    res2 = notifier.notify_entry_filled(
        signal_id="S:100:test",
        fill_price=30000.0,
        timestamp_str="2026-10-12 12:05 UTC",
    )
    assert res2.success
    assert len(captured_payloads) == 2
    assert "Entry Filled" in captured_payloads[1]["title"]

    # 3. Trade closed (Target)
    res3 = notifier.notify_trade_closed(
        signal_id="S:100:test",
        exit_reason="TARGET",
        exit_price=30050.0,
        gross_pnl=100.0,
        timestamp_str="2026-10-12 12:45 UTC",
    )
    assert res3.success
    assert len(captured_payloads) == 3
    assert "TARGET HIT" in captured_payloads[2]["title"]

    # 4. Trade closed (Time-stop)
    res4 = notifier.notify_trade_closed(
        signal_id="S:100:test",
        exit_reason="TIME_STOP",
        exit_price=30010.0,
        gross_pnl=20.0,
        timestamp_str="2026-10-12 15:05 UTC",
    )
    assert res4.success
    assert len(captured_payloads) == 4
    assert "TIME-STOP" in captured_payloads[3]["title"]
