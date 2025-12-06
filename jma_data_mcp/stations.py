"""AMeDAS station data management."""

import json
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data"
STATIONS_FILE = DATA_DIR / "amedas_stations.json"

_stations_cache: Optional[dict] = None


def load_stations() -> dict:
    """Load AMeDAS station data from JSON file."""
    global _stations_cache
    if _stations_cache is None:
        with open(STATIONS_FILE, "r", encoding="utf-8") as f:
            _stations_cache = json.load(f)
    return _stations_cache


def get_station(code: str) -> Optional[dict]:
    """Get station by code."""
    stations = load_stations()
    return stations.get(code)


def search_stations_by_name(name: str) -> list[dict]:
    """Search stations by name (Japanese, Kana, or English)."""
    stations = load_stations()
    results = []
    name_lower = name.lower()

    for station in stations.values():
        if (name in station["name"]["ja"] or
            name in station["name"]["kana"] or
            name_lower in station["name"]["en"].lower()):
            results.append(station)

    return results


def search_stations_by_location(
    lat: float,
    lon: float,
    radius_km: float = 50.0
) -> list[dict]:
    """Search stations within radius from given location."""
    import math

    stations = load_stations()
    results = []

    for station in stations.values():
        station_lat = station["location"]["lat"]
        station_lon = station["location"]["lon"]

        # Haversine formula for distance calculation
        lat1, lon1 = math.radians(lat), math.radians(lon)
        lat2, lon2 = math.radians(station_lat), math.radians(station_lon)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        # Earth radius in km
        r = 6371
        distance = r * c

        if distance <= radius_km:
            result = station.copy()
            result["distance_km"] = round(distance, 2)
            results.append(result)

    # Sort by distance
    results.sort(key=lambda x: x["distance_km"])
    return results


def get_stations_by_type(station_type: str) -> list[dict]:
    """Get all stations of a specific type (A, B, C, D, E, F)."""
    stations = load_stations()
    return [s for s in stations.values() if s["type"] == station_type]


def get_all_stations() -> list[dict]:
    """Get all stations."""
    stations = load_stations()
    return list(stations.values())
