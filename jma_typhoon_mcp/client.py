import csv
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from io import StringIO
from typing import Annotated, Any

from pydantic import Field, validate_call

from ._best_track import load_best_tracks
from ._cache import Document, Snapshot, cache_path, load_snapshot

BASE_URL = "https://www.data.jma.go.jp/typhoon/position_table/"
Year = Annotated[int, Field(ge=2001, le=9999)]
BestTrackYear = Annotated[int, Field(ge=1951, le=9999)]
Number = Annotated[int, Field(ge=1, le=99)]


def _load_typhoons(fetch: Callable[[str], Document], year: int) -> dict[str, Any]:
    page = BASE_URL + f"table{year}.html"
    url = BASE_URL + f"table{year}.csv"
    document = fetch(url)
    try:
        text = document.body.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = document.body.decode("cp932")
    rows = csv.reader(StringIO(text), strict=True)
    if next(rows, [])[:11] != [
        "年",
        "月",
        "日",
        "時（UTC）",
        "台風番号",
        "台風名",
        "階級",
        "緯度",
        "経度",
        "中心気圧",
        "最大風速",
    ]:
        raise ValueError("JMA typhoon position CSV columns have changed.")
    tracks: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not any(row):
            continue
        if len(row) < 11 or not re.fullmatch(r"[0-9]{4}", row[4]):
            raise ValueError("Invalid row in the JMA typhoon position CSV.")
        if int(row[4][:2]) != year % 100 or not int(row[4][2:]):
            raise ValueError("JMA CSV contains a typhoon number outside the requested season.")
        observed_year, month, day, hour = map(int, row[:4])
        timestamp = datetime(observed_year, month, day, hour, tzinfo=UTC)
        lat, lon = float(row[7]), float(row[8])
        if not -90 <= lat <= 90 or not -180 <= lon <= 360:
            raise ValueError("Invalid coordinates in the JMA typhoon position CSV.")
        pressure, wind = int(row[9]), int(row[10])
        track = tracks.setdefault(
            row[4],
            {
                "typhoon_id": row[4],
                "number": int(row[4][2:]),
                "name": row[5],
                "positions": [],
            },
        )
        track["positions"].append(
            {
                "time_utc": timestamp.isoformat(),
                "latitude": lat,
                "longitude": round(lon - 360, 10) if lon > 180 else lon,
                "central_pressure_hpa": pressure or None,
                "max_wind_kt": wind or None,
                "grade": int(row[6]),
            }
        )
    updated = parsedate_to_datetime(document.last_modified) if document.last_modified else None
    return {
        "data_as_of": updated.isoformat() if updated else None,
        "source_urls": [page, url],
        "tracks": tracks,
    }


async def _snapshot(year: int, *, force: bool = False) -> Snapshot:
    current_year = datetime.now(timezone(timedelta(hours=9))).year
    if year > current_year:
        raise ValueError(f"Use a published season from 2001 to {current_year}.")
    path = cache_path("jma-typhoon-mcp", "JMA_TYPHOON_CACHE_DIR")
    ttl = timedelta(days=1 if year == current_year else 30)
    return await load_snapshot(
        path, str(year), ttl, lambda fetch: _load_typhoons(fetch, year), force=force
    )


@validate_call
async def list_typhoons(year: Year) -> dict[str, Any]:
    """List typhoons with completed post-analysis in a JMA CSV season, from 2001."""
    snapshot = await _snapshot(year)
    items = [
        {"typhoon_id": track["typhoon_id"], "number": track["number"], "name": track["name"]}
        for track in snapshot.data["tracks"].values()
    ]
    return {"year": year, "analysis": "final", "items": items, **snapshot.metadata()}


@validate_call
async def get_typhoon_track(year: Year, number: Number) -> dict[str, Any]:
    """Read final UTC positions, pressure and wind for a typhoon by season and number."""
    snapshot = await _snapshot(year)
    typhoon_id = f"{year % 100:02}{number:02}"
    return {
        "year": year,
        "analysis": "final",
        "typhoon_id": typhoon_id,
        "track": snapshot.data["tracks"].get(typhoon_id),
        **snapshot.metadata(),
    }


@validate_call
async def refresh_cache(year: Year) -> dict[str, Any]:
    """Check the official JMA CSV for one season immediately."""
    snapshot = await _snapshot(year, force=True)
    return {"year": year, "typhoons": len(snapshot.data["tracks"]), **snapshot.metadata()}


async def _best_track_snapshot(year: int) -> Snapshot:
    current_year = datetime.now(timezone(timedelta(hours=9))).year
    if year > current_year:
        raise ValueError(f"Use a published season from 1951 to {current_year}.")
    path = cache_path("jma-typhoon-mcp", "JMA_TYPHOON_CACHE_DIR")
    return await load_snapshot(
        path,
        "rsmc-best-track",
        timedelta(days=1),
        lambda fetch: load_best_tracks(fetch, current_year),
    )


@validate_call
async def list_best_track_typhoons(year: BestTrackYear) -> dict[str, Any]:
    """List typhoons in the JMA RSMC historical best track archive, from 1951."""
    snapshot = await _best_track_snapshot(year)
    items = [
        {key: track[key] for key in ("typhoon_id", "number", "name", "revision_date")}
        for track in snapshot.data["tracks"].values()
        if track["year"] == year
    ]
    return {"year": year, "analysis": "best_track", "items": items, **snapshot.metadata()}


@validate_call
async def get_best_track(year: BestTrackYear, number: Number) -> dict[str, Any]:
    """Read positions, pressure and wind from the JMA RSMC best track archive."""
    snapshot = await _best_track_snapshot(year)
    typhoon_id = f"{year % 100:02}{number:02}"
    track = snapshot.data["tracks"].get(typhoon_id)
    return {
        "year": year,
        "analysis": "best_track",
        "typhoon_id": typhoon_id,
        "track": track if track is not None and track["year"] == year else None,
        **snapshot.metadata(),
    }
