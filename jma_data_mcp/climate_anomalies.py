"""JMA's observation-based annual climate anomalies for Japan."""

import csv
import math
from typing import Any, Literal

from .public_files import fetch_public_file

ClimateMetric = Literal["temperature", "precipitation"]
SERIES = {
    "temperature": ("an_jpn.csv", "°C"),
    "precipitation": ("an_jpn_r.csv", "mm"),
}


async def fetch_japan_climate_anomalies(
    metric: ClimateMetric,
    start_year: int,
    end_year: int | None,
) -> dict[str, Any]:
    if not 1898 <= start_year <= 9999 or (
        end_year is not None and not start_year <= end_year <= 9999
    ):
        raise ValueError("Years must be 1898 or later and start year must not exceed end year")
    if metric not in SERIES:
        raise ValueError("Metric must be temperature or precipitation")
    filename, unit = SERIES[metric]
    url = f"https://www.data.jma.go.jp/cpdinfo/temp/list/csv/{filename}"
    data = await fetch_public_file(url, 64 * 1024)
    rows = csv.reader(data.decode("shift_jis").splitlines())
    if next(rows, None) != ["年", "偏差"]:
        raise ValueError("Unexpected header in JMA climate anomaly CSV")

    series: dict[int, float] = {}
    for year_cell, anomaly_cell in rows:
        year = int(year_cell)
        anomaly = float(anomaly_cell)
        if year in series or not math.isfinite(anomaly):
            raise ValueError("Unexpected record in JMA climate anomaly CSV")
        series[year] = anomaly
    if not series:
        raise ValueError("No values in JMA climate anomaly CSV")

    return {
        "metric": metric,
        "scope": "Japan",
        "unit": unit,
        "source_url": url,
        "baseline": {"start_year": 1991, "end_year": 2020},
        "available_years": {"start_year": min(series), "end_year": max(series)},
        "annual": [
            {"year": year, "anomaly": anomaly}
            for year, anomaly in sorted(series.items())
            if year >= start_year and (end_year is None or year <= end_year)
        ],
    }
