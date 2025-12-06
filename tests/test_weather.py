"""Tests for weather data functions."""

from datetime import datetime, timedelta

import pytest

from jma_data_mcp.weather import (
    AREA_CODES,
    JST,
    WIND_DIRECTIONS,
    WIND_DIRECTIONS_JA,
    fetch_amedas_data,
    fetch_forecast,
    fetch_historical_amedas_data,
    fetch_time_series_data,
    format_time_for_api,
    get_latest_data_time,
    parse_observation_value,
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
    from datetime import datetime, timedelta, timezone
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


@pytest.mark.asyncio
async def test_fetch_historical_amedas_data():
    """Test fetching historical AMeDAS data."""
    # Fetch data from 1 hour ago
    target_time = datetime.now(JST) - timedelta(hours=1)
    data = await fetch_historical_amedas_data("44132", target_time)

    assert "observation_time" in data
    assert "station_code" in data
    assert data["station_code"] == "44132"

    # Should have data (not error)
    if "error" not in data:
        assert "data" in data
        assert "temperature" in data["data"] or "precipitation" in data["data"]


@pytest.mark.asyncio
async def test_fetch_time_series_data():
    """Test fetching time series data."""
    data = await fetch_time_series_data("44132", hours=3, interval_minutes=60)

    assert "station_code" in data
    assert data["station_code"] == "44132"
    assert "time_series" in data
    assert "data_points" in data
    # Should have at least some data points
    assert data["data_points"] > 0
    assert len(data["time_series"]) > 0

    # Each data point should have observation_time
    for point in data["time_series"]:
        assert "observation_time" in point


@pytest.mark.asyncio
async def test_fetch_time_series_data_with_interval():
    """Test fetching time series data with different intervals."""
    data = await fetch_time_series_data("44132", hours=2, interval_minutes=30)

    assert "interval_minutes" in data
    assert data["interval_minutes"] == 30
    assert "time_series" in data
