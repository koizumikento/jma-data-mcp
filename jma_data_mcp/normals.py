"""Monthly and annual AMeDAS climate normals from JMA's official ZIP."""

import csv
import io
import re
from time import monotonic
from typing import Any
from zipfile import BadZipFile, ZipFile

from .public_files import fetch_public_file

NORMALS_URL = "https://www.data.jma.go.jp/stats/data/mdrr/normal/2020/data/normal_amedas_monthly.zip"
ELEMENTS = {
    "0500": ("mean_temperature", "°C", 10),
    "0600": ("mean_daily_max_temperature", "°C", 10),
    "0700": ("mean_daily_min_temperature", "°C", 10),
    "2600": ("mean_wind_speed", "m/s", 10),
    "3500": ("total_sunshine", "h", 10),
    "4000": ("total_precipitation", "mm", 10),
    "6200": ("maximum_snow_depth", "cm", 1),
    "6300": ("total_snowfall", "cm", 1),
}
_archive_cache: tuple[float, bytes] | None = None


async def _load_archive() -> bytes:
    global _archive_cache
    if _archive_cache and monotonic() < _archive_cache[0]:
        return _archive_cache[1]
    data = await fetch_public_file(NORMALS_URL, 8 * 1024 * 1024)
    try:
        with ZipFile(io.BytesIO(data)) as archive:
            if not any(name.startswith("monthly/area") and name.endswith(".csv") for name in archive.namelist()):
                raise ValueError("Unexpected layout in JMA climate normals archive")
    except BadZipFile as exc:
        raise ValueError("Invalid JMA climate normals archive") from exc
    _archive_cache = (monotonic() + 3600, data)
    return data


async def fetch_climate_normals(station_code: str, month: int | None) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9]{5}", station_code):
        raise ValueError("Station code must be five ASCII digits")
    if month is not None and not 1 <= month <= 12:
        raise ValueError("Month must be between 1 and 12")

    data = await _load_archive()
    path = f"monthly/area{station_code[:2]}/nml_amd_m_{station_code}.csv"
    with ZipFile(io.BytesIO(data)) as archive:
        try:
            member = archive.getinfo(path)
        except KeyError as exc:
            raise ValueError(f"No monthly climate normals for AMeDAS station {station_code}") from exc
        if member.file_size > 128 * 1024:
            raise ValueError("JMA climate normals station file exceeds the configured size limit")
        rows = csv.reader(archive.read(member).decode("ascii").splitlines())

    metrics: dict[str, Any] = {}
    months = [month] if month is not None else list(range(1, 13))
    for row in rows:
        if len(row) != 32 or row[:2] != ["21", station_code]:
            raise ValueError("Unexpected record in JMA climate normals station file")
        element = ELEMENTS.get(row[2])
        if element is None:
            continue
        name, unit, scale = element
        metrics[name] = {
            "unit": unit,
            "sample_years": int(row[3]),
            "statistics_start_year": int(row[4]) or None,
            "statistics_end_year": int(row[5]) or None,
            "monthly": {str(index): _value(row, index, scale) for index in months},
            "annual": _value(row, 13, scale),
        }
    if not metrics:
        raise ValueError("No supported metrics in JMA climate normals station file")

    return {
        "station_code": station_code,
        "source_url": NORMALS_URL,
        "normal_period": {"start_year": 1991, "end_year": 2020},
        "metrics": metrics,
    }


def _value(row: list[str], period: int, scale: int) -> dict[str, float | int | None]:
    index = 6 + (period - 1) * 2
    remark = int(row[index + 1])
    raw_value = row[index].strip()
    return {"value": int(raw_value) / scale if remark and raw_value else None, "remark": remark}
