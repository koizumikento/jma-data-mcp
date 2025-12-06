"""Tests for weather data functions."""

import pytest
from jma_data_mcp.weather import (
    get_latest_data_time,
    format_time_for_api,
    parse_observation_value,
    fetch_amedas_data,
    fetch_forecast,
    WIND_DIRECTIONS,
    WIND_DIRECTIONS_JA,
    AREA_CODES,
)


def test_wind_directions():
    """Test wind direction mappings."""
    assert len(WIND_DIRECTIONS) == 16
    assert len(WIND_DIRECTIONS_JA) == 16
    assert WIND_DIRECTIONS[16] == "N"
    assert WIND_DIRECTIONS_JA[16] == "北"


def test_area_codes():
    """Test area codes."""
    assert "tokyo" in AREA_CODES
    assert AREA_CODES["tokyo"] == "130000"
    assert "osaka" in AREA_CODES


def test_get_latest_data_time():
    """Test getting latest data time."""
    dt = get_latest_data_time()
    assert dt is not None
    # Should be rounded to 10 minutes
    assert dt.minute % 10 == 0
    assert dt.second == 0


def test_format_time_for_api():
    """Test time formatting for API."""
    from datetime import datetime, timezone, timedelta
    JST = timezone(timedelta(hours=9))
    dt = datetime(2025, 12, 6, 10, 30, 0, tzinfo=JST)
    result = format_time_for_api(dt)
    assert result == "20251206103000"


def test_parse_observation_value():
    """Test parsing observation values."""
    assert parse_observation_value([10.5, 0]) == 10.5
    assert parse_observation_value([0, 0]) == 0
    assert parse_observation_value([None, 0]) is None
    assert parse_observation_value([10, None]) is None
    assert parse_observation_value(None) is None


@pytest.mark.asyncio
async def test_fetch_amedas_data_single_station():
    """Test fetching AMeDAS data for a single station."""
    data = await fetch_amedas_data(station_code="44132")  # Tokyo
    assert "observation_time" in data
    assert "stations" in data
    assert "44132" in data["stations"]

    tokyo_data = data["stations"]["44132"]
    assert "code" in tokyo_data
    # Tokyo station should have temperature data
    if "temperature" in tokyo_data:
        assert "value" in tokyo_data["temperature"]
        assert "unit" in tokyo_data["temperature"]


@pytest.mark.asyncio
async def test_fetch_amedas_data_all_stations():
    """Test fetching AMeDAS data for all stations."""
    data = await fetch_amedas_data()
    assert "observation_time" in data
    assert "stations" in data
    # Should have many stations
    assert len(data["stations"]) > 1000


@pytest.mark.asyncio
async def test_fetch_forecast():
    """Test fetching weather forecast."""
    data = await fetch_forecast("130000")  # Tokyo
    assert data is not None
    assert isinstance(data, list)
    # Forecast data should be a list
    assert len(data) > 0
