import pytest

from mnq_fractal_bot.data.timeframes import get_higher_timeframe


def test_5m_maps_to_1h():
    assert get_higher_timeframe("5m") == "1h"


def test_15m_maps_to_4h():
    assert get_higher_timeframe("15m") == "4h"


def test_30m_maps_to_4h():
    assert get_higher_timeframe("30m") == "4h"


def test_1h_maps_to_1d():
    assert get_higher_timeframe("1h") == "1d"


def test_invalid_timeframe_is_rejected():
    with pytest.raises(ValueError):
        get_higher_timeframe("7m")