from datetime import (
    datetime,
    timedelta,
    timezone,
)

from mnq_fractal_bot.execution.bot_runner import (
    BotRunner,
)

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.models.setup import Setup


NOW = datetime(
    2026,
    10,
    9,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_candle(
    timestamp,
):
    return Candle(
        timestamp=timestamp,
        open=106,
        high=110,
        low=102,
        close=108,
        volume=100,
    )


def add_ready_setup(
    runner,
):
    setup = Setup(
        is_bullish=False,

        is_confirmed=True,
        cisd_triggered=True,
        is_post_c2=True,

        sweep_price=112,
        cisd_level=109,

        sweep_bar_index=100,
        swept_htf_index=5,

        c2_extreme=120,

        c4_zone_set=True,
        c4_invalid=False,

        c4_zone_bottom=104,
        c4_zone_top=108,

        c4_start_time=NOW,
        c4_end_time=(
            NOW + timedelta(hours=1)
        ),

        liq_c1_price=100,
        liq_c0_price=90,
    )

    runner.engine.completed_setups.append(
        setup
    )

    return setup


def test_ready_signal_creates_audit():
    runner = BotRunner()

    add_ready_setup(
        runner
    )

    snapshot = runner.on_candle(
        make_candle(
            NOW
        )
    )

    assert snapshot.audit_count == 1

    assert len(
        runner.signal_audits
    ) == 1

    audit = (
        runner.signal_audits[0]
    )

    assert audit.direction == "SHORT"

    assert audit.sweep_price == 112
    assert audit.cisd_level == 109

    assert audit.entry_price == 106

    assert audit.stop_price == 120.5

    assert audit.tp_c1 == 100


def test_same_signal_is_not_audited_twice():
    runner = BotRunner()

    add_ready_setup(
        runner
    )

    runner.on_candle(
        make_candle(
            NOW
        )
    )

    runner.on_candle(
        make_candle(
            NOW + timedelta(minutes=5)
        )
    )

    assert len(
        runner.signal_audits
    ) == 1


def test_audit_timestamp_is_signal_detection_candle():
    runner = BotRunner()

    add_ready_setup(
        runner
    )

    detection_time = (
        NOW + timedelta(minutes=15)
    )

    runner.on_candle(
        make_candle(
            detection_time
        )
    )

    audit = (
        runner.signal_audits[0]
    )

    assert (
        audit.created_at
        == detection_time
    )