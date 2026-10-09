from datetime import datetime, timezone

from mnq_fractal_bot.models.candle import Candle
from mnq_fractal_bot.models.setup import Setup
from mnq_fractal_bot.strategy.liquidity import (
    get_valid_targets,
    set_formation_liquidity,
)


NOW = datetime(
    2026,
    10,
    9,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_candle(
    open_price,
    high,
    low,
    close,
):
    return Candle(
        timestamp=NOW,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=100,
    )


def test_bearish_c1_liquidity():
    setup = Setup(
        is_bullish=False,
    )

    c1 = make_candle(
        110,
        120,
        100,
        115,
    )

    result = set_formation_liquidity(
        setup=setup,
        c1=c1,
    )

    assert result.liq_c1_price == 100
    assert result.liq_c0_price is None


def test_bearish_c0_requires_lower_low():
    setup = Setup(
        is_bullish=False,
    )

    c1 = make_candle(
        110,
        120,
        100,
        115,
    )

    c0 = make_candle(
        105,
        115,
        90,
        110,
    )

    result = set_formation_liquidity(
        setup=setup,
        c1=c1,
        c0=c0,
    )

    assert result.liq_c1_price == 100
    assert result.liq_c0_price == 90


def test_bullish_c0_requires_higher_high():
    setup = Setup(
        is_bullish=True,
    )

    c1 = make_candle(
        110,
        120,
        100,
        115,
    )

    c0 = make_candle(
        115,
        130,
        105,
        120,
    )

    result = set_formation_liquidity(
        setup=setup,
        c1=c1,
        c0=c0,
    )

    assert result.liq_c1_price == 120
    assert result.liq_c0_price == 130


def test_short_targets_must_be_below_entry():
    setup = Setup(
        is_bullish=False,
        liq_c1_price=100,
        liq_c0_price=90,
    )

    targets = get_valid_targets(
        setup=setup,
        entry_price=110,
    )

    assert targets.c1 == 100
    assert targets.c0 == 90
    assert targets.has_valid_target is True
    assert targets.preferred_target == 100


def test_long_targets_must_be_above_entry():
    setup = Setup(
        is_bullish=True,
        liq_c1_price=120,
        liq_c0_price=130,
    )

    targets = get_valid_targets(
        setup=setup,
        entry_price=110,
    )

    assert targets.c1 == 120
    assert targets.c0 == 130
    assert targets.has_valid_target is True
    assert targets.preferred_target == 120


def test_wrong_side_targets_are_rejected():
    setup = Setup(
        is_bullish=False,
        liq_c1_price=120,
        liq_c0_price=130,
    )

    targets = get_valid_targets(
        setup=setup,
        entry_price=110,
    )

    assert targets.c1 is None
    assert targets.c0 is None
    assert targets.has_valid_target is False
    assert targets.preferred_target is None