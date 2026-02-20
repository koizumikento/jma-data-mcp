"""Command-line interface for JMA data tools."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

from . import server

JsonDict = dict[str, Any]
Handler = Callable[[argparse.Namespace], Awaitable[JsonDict]]


class JsonArgumentParser(argparse.ArgumentParser):
    """Argument parser that raises exceptions instead of exiting on errors."""

    def error(self, message: str) -> None:
        raise ValueError(message)


def _build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        prog="jma-data-mcp",
        description="CLI for Japan Meteorological Agency (JMA) data",
    )
    subparsers = parser.add_subparsers(dest="resource", required=True)

    station_parser = subparsers.add_parser("station", help="Station data commands")
    station_subparsers = station_parser.add_subparsers(dest="station_command", required=True)

    station_get = station_subparsers.add_parser("get", help="Get station info by code")
    station_get.add_argument("--code", required=True, help="Station code (e.g., 44132)")
    station_get.set_defaults(handler=_station_get)

    station_search = station_subparsers.add_parser("search", help="Search stations by name")
    station_search.add_argument("--name", required=True, help="Station name to search")
    station_search.set_defaults(handler=_station_search)

    station_nearby = station_subparsers.add_parser("nearby", help="Search nearby stations")
    station_nearby.add_argument("--lat", type=float, required=True, help="Latitude")
    station_nearby.add_argument("--lon", type=float, required=True, help="Longitude")
    station_nearby.add_argument("--radius-km", type=float, default=50.0, help="Radius in km")
    station_nearby.set_defaults(handler=_station_nearby)

    station_type = station_subparsers.add_parser("type", help="List stations by type")
    station_type.add_argument(
        "--station-type",
        choices=["A", "B", "C", "D", "E", "F"],
        required=True,
        help="Station type",
    )
    station_type.set_defaults(handler=_station_type)

    station_list = station_subparsers.add_parser("list", help="List stations")
    station_list.add_argument("--limit", type=int, default=100, help="Max records")
    station_list.add_argument("--offset", type=int, default=0, help="Offset")
    station_list.set_defaults(handler=_station_list)

    weather_parser = subparsers.add_parser("weather", help="Weather commands")
    weather_subparsers = weather_parser.add_subparsers(dest="weather_command", required=True)

    weather_current = weather_subparsers.add_parser("current", help="Get current weather data")
    weather_current.add_argument("--station-code", help="Station code")
    weather_current.set_defaults(handler=_weather_current)

    weather_by_location = weather_subparsers.add_parser(
        "by-location",
        help="Get weather by coordinates",
    )
    weather_by_location.add_argument("--lat", type=float, required=True, help="Latitude")
    weather_by_location.add_argument("--lon", type=float, required=True, help="Longitude")
    weather_by_location.set_defaults(handler=_weather_by_location)

    forecast_parser = subparsers.add_parser("forecast", help="Forecast commands")
    forecast_subparsers = forecast_parser.add_subparsers(dest="forecast_command", required=True)

    forecast_get = forecast_subparsers.add_parser("get", help="Get forecast by prefecture")
    forecast_get.add_argument("--prefecture", required=True, help="Prefecture key")
    forecast_get.set_defaults(handler=_forecast_get)

    forecast_list = forecast_subparsers.add_parser(
        "list-prefectures",
        help="List all supported prefectures",
    )
    forecast_list.set_defaults(handler=_forecast_list_prefectures)

    history_parser = subparsers.add_parser("history", help="Historical weather commands")
    history_subparsers = history_parser.add_subparsers(dest="history_command", required=True)

    history_get = history_subparsers.add_parser("get", help="Get historical weather")
    history_get.add_argument("--station-code", required=True, help="Station code")
    history_get.add_argument(
        "--target-datetime",
        required=True,
        help='Target datetime (e.g., "2025-12-01 12:00" or ISO 8601)',
    )
    history_get.set_defaults(handler=_history_get)

    history_series = history_subparsers.add_parser("series", help="Get weather time series")
    history_series.add_argument("--station-code", required=True, help="Station code")
    history_series.add_argument("--hours", type=int, default=24, help="Hours to fetch")
    history_series.add_argument(
        "--interval-minutes",
        type=int,
        choices=[10, 30, 60],
        default=60,
        help="Data interval in minutes",
    )
    history_series.set_defaults(handler=_history_series)

    return parser


def _print_json(payload: JsonDict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _normalize_exit_code(code: object) -> int:
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    return 2


def main(argv: list[str] | None = None) -> int:
    """Run CLI with JSON output."""
    parser = _build_parser()

    try:
        args = parser.parse_args(argv)
        handler: Handler = args.handler
    except ValueError as exc:
        _print_json({"error": str(exc)})
        return 2
    except SystemExit as exc:
        return _normalize_exit_code(exc.code)

    try:
        result = asyncio.run(handler(args))
    except Exception as exc:
        _print_json({"error": str(exc)})
        return 2

    _print_json(result)
    return 0


async def _station_get(args: argparse.Namespace) -> JsonDict:
    return await server.get_station_info(code=args.code)


async def _station_search(args: argparse.Namespace) -> JsonDict:
    return await server.search_stations(name=args.name)


async def _station_nearby(args: argparse.Namespace) -> JsonDict:
    return await server.search_nearby_stations(
        lat=args.lat,
        lon=args.lon,
        radius_km=args.radius_km,
    )


async def _station_type(args: argparse.Namespace) -> JsonDict:
    return await server.get_stations_of_type(station_type=args.station_type)


async def _station_list(args: argparse.Namespace) -> JsonDict:
    return await server.list_stations(limit=args.limit, offset=args.offset)


async def _weather_current(args: argparse.Namespace) -> JsonDict:
    return await server.get_current_weather(station_code=args.station_code)


async def _weather_by_location(args: argparse.Namespace) -> JsonDict:
    return await server.get_weather_by_location(lat=args.lat, lon=args.lon)


async def _forecast_get(args: argparse.Namespace) -> JsonDict:
    return await server.get_forecast(prefecture=args.prefecture)


async def _forecast_list_prefectures(args: argparse.Namespace) -> JsonDict:
    del args
    return await server.list_prefectures()


async def _history_get(args: argparse.Namespace) -> JsonDict:
    return await server.get_historical_weather(
        station_code=args.station_code,
        target_datetime=args.target_datetime,
    )


async def _history_series(args: argparse.Namespace) -> JsonDict:
    return await server.get_weather_time_series(
        station_code=args.station_code,
        hours=args.hours,
        interval_minutes=args.interval_minutes,
    )
