"""Weather data fetching from JMA APIs."""

import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional

# Japan Standard Time (UTC+9)
JST = timezone(timedelta(hours=9))

# Wind direction mapping (16 directions)
WIND_DIRECTIONS = {
    1: "NNE", 2: "NE", 3: "ENE", 4: "E",
    5: "ESE", 6: "SE", 7: "SSE", 8: "S",
    9: "SSW", 10: "SW", 11: "WSW", 12: "W",
    13: "WNW", 14: "NW", 15: "NNW", 16: "N"
}

WIND_DIRECTIONS_JA = {
    1: "北北東", 2: "北東", 3: "東北東", 4: "東",
    5: "東南東", 6: "南東", 7: "南南東", 8: "南",
    9: "南南西", 10: "南西", 11: "西南西", 12: "西",
    13: "西北西", 14: "北西", 15: "北北西", 16: "北"
}


def get_latest_data_time() -> datetime:
    """Get the latest available data time (approximately 30 minutes behind current time)."""
    now = datetime.now(JST)
    # Data is available about 30-40 minutes after observation
    data_time = now - timedelta(minutes=40)
    # Round down to 10-minute intervals
    data_time = data_time.replace(minute=(data_time.minute // 10) * 10, second=0, microsecond=0)
    return data_time


def format_time_for_api(dt: datetime) -> str:
    """Format datetime for JMA API URL."""
    return dt.strftime('%Y%m%d%H%M00')


def parse_observation_value(value: list) -> Optional[float]:
    """Parse observation value from [value, quality_flag] format."""
    if value is None or len(value) < 2:
        return None
    val, quality = value
    if val is None or quality is None:
        return None
    return val


async def fetch_amedas_data(
    station_code: Optional[str] = None,
    data_time: Optional[datetime] = None
) -> dict:
    """
    Fetch AMeDAS observation data from JMA API.

    Args:
        station_code: Optional station code to filter (returns all if None)
        data_time: Optional datetime for historical data (uses latest if None)

    Returns:
        Dictionary with observation data
    """
    if data_time is None:
        data_time = get_latest_data_time()

    time_str = format_time_for_api(data_time)
    url = f'https://www.jma.go.jp/bosai/amedas/data/map/{time_str}.json'

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        raw_data = response.json()

    # Parse and format the data
    result = {
        "observation_time": data_time.isoformat(),
        "observation_time_jst": data_time.strftime('%Y-%m-%d %H:%M JST'),
        "stations": {}
    }

    stations_to_process = {station_code: raw_data.get(station_code)} if station_code else raw_data

    for code, data in stations_to_process.items():
        if data is None:
            continue

        station_data = {"code": code}

        # Temperature (℃)
        if "temp" in data:
            station_data["temperature"] = {
                "value": parse_observation_value(data["temp"]),
                "unit": "℃"
            }

        # Humidity (%)
        if "humidity" in data:
            station_data["humidity"] = {
                "value": parse_observation_value(data["humidity"]),
                "unit": "%"
            }

        # Pressure (hPa)
        if "pressure" in data:
            station_data["pressure"] = {
                "value": parse_observation_value(data["pressure"]),
                "unit": "hPa"
            }

        # Sea level pressure (hPa)
        if "normalPressure" in data:
            station_data["sea_level_pressure"] = {
                "value": parse_observation_value(data["normalPressure"]),
                "unit": "hPa"
            }

        # Wind
        if "wind" in data:
            wind_speed = parse_observation_value(data["wind"])
            wind_dir_code = parse_observation_value(data.get("windDirection", [None, None]))
            wind_dir = None
            wind_dir_ja = None
            if wind_dir_code is not None:
                wind_dir_code = int(wind_dir_code)
                wind_dir = WIND_DIRECTIONS.get(wind_dir_code)
                wind_dir_ja = WIND_DIRECTIONS_JA.get(wind_dir_code)

            station_data["wind"] = {
                "speed": wind_speed,
                "speed_unit": "m/s",
                "direction": wind_dir,
                "direction_ja": wind_dir_ja,
                "direction_code": wind_dir_code
            }

        # Precipitation
        precipitation = {}
        if "precipitation10m" in data:
            precipitation["10min"] = parse_observation_value(data["precipitation10m"])
        if "precipitation1h" in data:
            precipitation["1h"] = parse_observation_value(data["precipitation1h"])
        if "precipitation3h" in data:
            precipitation["3h"] = parse_observation_value(data["precipitation3h"])
        if "precipitation24h" in data:
            precipitation["24h"] = parse_observation_value(data["precipitation24h"])
        if precipitation:
            station_data["precipitation"] = {
                **precipitation,
                "unit": "mm"
            }

        # Sunshine
        if "sun1h" in data:
            station_data["sunshine"] = {
                "1h": parse_observation_value(data["sun1h"]),
                "unit": "hours"
            }

        # Snow
        snow = {}
        if "snow" in data:
            snow["depth"] = parse_observation_value(data["snow"])
        if "snow1h" in data:
            snow["1h"] = parse_observation_value(data["snow1h"])
        if "snow6h" in data:
            snow["6h"] = parse_observation_value(data["snow6h"])
        if "snow12h" in data:
            snow["12h"] = parse_observation_value(data["snow12h"])
        if "snow24h" in data:
            snow["24h"] = parse_observation_value(data["snow24h"])
        if snow:
            station_data["snow"] = {
                **snow,
                "unit": "cm"
            }

        result["stations"][code] = station_data

    return result


async def fetch_weather_warnings() -> dict:
    """
    Fetch current weather warnings/advisories from JMA.

    Returns:
        Dictionary with warning data
    """
    url = "https://www.jma.go.jp/bosai/warning/data/warning/000000.json"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        return response.json()


async def fetch_forecast(area_code: str) -> dict:
    """
    Fetch weather forecast for a specific area.

    Args:
        area_code: JMA area code (e.g., "130000" for Tokyo)

    Returns:
        Dictionary with forecast data
    """
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        return response.json()


# Area codes for major prefectures
AREA_CODES = {
    "hokkaido_sapporo": "016000",
    "aomori": "020000",
    "iwate": "030000",
    "miyagi": "040000",
    "akita": "050000",
    "yamagata": "060000",
    "fukushima": "070000",
    "ibaraki": "080000",
    "tochigi": "090000",
    "gunma": "100000",
    "saitama": "110000",
    "chiba": "120000",
    "tokyo": "130000",
    "kanagawa": "140000",
    "niigata": "150000",
    "toyama": "160000",
    "ishikawa": "170000",
    "fukui": "180000",
    "yamanashi": "190000",
    "nagano": "200000",
    "gifu": "210000",
    "shizuoka": "220000",
    "aichi": "230000",
    "mie": "240000",
    "shiga": "250000",
    "kyoto": "260000",
    "osaka": "270000",
    "hyogo": "280000",
    "nara": "290000",
    "wakayama": "300000",
    "tottori": "310000",
    "shimane": "320000",
    "okayama": "330000",
    "hiroshima": "340000",
    "yamaguchi": "350000",
    "tokushima": "360000",
    "kagawa": "370000",
    "ehime": "380000",
    "kochi": "390000",
    "fukuoka": "400000",
    "saga": "410000",
    "nagasaki": "420000",
    "kumamoto": "430000",
    "oita": "440000",
    "miyazaki": "450000",
    "kagoshima": "460000",
    "okinawa": "470000",
}
