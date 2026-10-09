from datetime import (
    datetime,
    timedelta,
    timezone,
)

from mnq_fractal_bot.models.setup import Setup
from mnq_fractal_bot.strategy.setup_selection import (
    select_setup,
    setup_score,
)


NOW = datetime(
    2026,
    10,
    9,
    12,
    0,
    tzinfo=timezone.utc,
)


def test_cisd_triggered_has_highest_score():
    setup = Setup(
        is_bullish=True,
        is_confirmed=True,
        cisd_triggered=True,
    )

    assert setup_score(setup) == 3


def test_confirmed_sweep_scores_two():
    setup = Setup(
        is_bullish=True,
        is_confirmed=True,
        cisd_triggered=False,
    )

    assert setup_score(setup) == 2


def test_more_advanced_live_setup_is_selected():
    bullish = Setup(
        is_bullish=True,
        is_confirmed=True,
        cisd_triggered=True,
    )

    bearish = Setup(
        is_bullish=False,
        is_confirmed=True,
        cisd_triggered=False,
    )

    result = select_setup(
        live_bullish=bullish,
        live_bearish=bearish,
        completed_setups=[],
        current_time=NOW,
    )

    assert result.setup is bullish
    assert result.both_sides is False


def test_equal_live_scores_returns_both_sides():
    bullish = Setup(
        is_bullish=True,
        is_confirmed=True,
    )

    bearish = Setup(
        is_bullish=False,
        is_confirmed=True,
    )

    result = select_setup(
        live_bullish=bullish,
        live_bearish=bearish,
        completed_setups=[],
        current_time=NOW,
    )

    assert result.setup is None
    assert result.both_sides is True


def test_active_historical_c4_can_be_selected():
    setup = Setup(
        is_bullish=False,
        is_confirmed=True,
        cisd_triggered=True,
        c4_zone_set=True,
        c4_invalid=False,
        c4_start_time=NOW,
        c4_end_time=(
            NOW + timedelta(hours=1)
        ),
    )

    result = select_setup(
        live_bullish=None,
        live_bearish=None,
        completed_setups=[
            setup
        ],
        current_time=(
            NOW + timedelta(minutes=10)
        ),
    )

    assert result.setup is setup
    assert result.both_sides is False


def test_expired_historical_c4_is_ignored():
    setup = Setup(
        is_bullish=False,
        c4_zone_set=True,
        c4_invalid=False,
        c4_start_time=(
            NOW - timedelta(hours=2)
        ),
        c4_end_time=(
            NOW - timedelta(hours=1)
        ),
    )

    result = select_setup(
        live_bullish=None,
        live_bearish=None,
        completed_setups=[
            setup
        ],
        current_time=NOW,
    )

    assert result.setup is None