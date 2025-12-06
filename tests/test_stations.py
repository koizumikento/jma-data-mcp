"""Tests for station data functions."""

from jma_data_mcp.stations import (
    get_all_stations,
    get_station,
    get_stations_by_type,
    load_stations,
    search_stations_by_location,
    search_stations_by_name,
)


def test_load_stations():
    """Test loading station data."""
    stations = load_stations()
    assert len(stations) == 1286


def test_get_station():
    """Test getting a specific station."""
    # Tokyo station
    station = get_station("44132")
    assert station is not None
    assert station["name"]["ja"] == "東京"
    assert station["name"]["en"] == "Tokyo"
    assert station["type"] == "A"


def test_get_station_not_found():
    """Test getting non-existent station."""
    station = get_station("99999")
    assert station is None


def test_search_stations_by_name_japanese():
    """Test searching by Japanese name."""
    results = search_stations_by_name("東京")
    assert len(results) > 0
    assert any(s["name"]["ja"] == "東京" for s in results)


def test_search_stations_by_name_english():
    """Test searching by English name."""
    results = search_stations_by_name("Tokyo")
    assert len(results) > 0


def test_search_stations_by_location():
    """Test searching by location."""
    # Search around Tokyo Station (35.6812, 139.7671)
    results = search_stations_by_location(35.6812, 139.7671, radius_km=10)
    assert len(results) > 0
    # Results should be sorted by distance
    distances = [r["distance_km"] for r in results]
    assert distances == sorted(distances)


def test_get_stations_by_type():
    """Test getting stations by type."""
    # Type A (Staffed observatories)
    stations = get_stations_by_type("A")
    assert len(stations) > 0
    assert all(s["type"] == "A" for s in stations)


def test_get_all_stations():
    """Test getting all stations."""
    stations = get_all_stations()
    assert len(stations) == 1286
