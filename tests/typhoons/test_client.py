import sqlite3
from contextlib import closing
from io import BytesIO
from zipfile import ZipFile

import httpx
import pytest
import respx

from jma_typhoon_mcp import (
    get_best_track,
    get_typhoon_track,
    list_best_track_typhoons,
    list_typhoons,
)
from jma_typhoon_mcp._best_track import ARCHIVE_URL
from jma_typhoon_mcp.client import BASE_URL


@pytest.mark.asyncio
@respx.mock
async def test_list_and_track_preserve_final_analysis_and_utc(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("JMA_TYPHOON_CACHE_DIR", str(tmp_path))
    csv = (
        "年,月,日,時（UTC）,台風番号,台風名,階級,緯度,経度,中心気圧,最大風速\n"
        "2001,5,9,12,0101,CIMARON,2,11.8,180.6,1004,0\n"
    )
    route = respx.get(BASE_URL + "table2001.csv").mock(
        return_value=httpx.Response(200, content=csv.encode("cp932")),
    )
    result = await list_typhoons(2001)
    assert result["analysis"] == "final"
    item = result["items"][0]
    track = (await get_typhoon_track(2001, item["number"]))["track"]
    assert track["typhoon_id"] == "0101"
    assert track["positions"][0]["time_utc"] == "2001-05-09T12:00:00+00:00"
    assert track["positions"][0]["central_pressure_hpa"] == 1004
    assert track["positions"][0]["longitude"] == -179.4
    assert track["positions"][0]["max_wind_kt"] is None
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_best_tracks_share_archive_and_preserve_observation_year(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("JMA_TYPHOON_CACHE_DIR", str(tmp_path))
    unnamed_header = "66666 5101   01      5101 0 6".ljust(64) + "19901017"
    named_header = "66666 0101   02      0101 0 6".ljust(30) + "CIMARON".ljust(34) + "20010201"
    text = (
        f"{unnamed_header}\n"
        "51021906 002 2 200 1385 1010\n"
        f"{named_header}\n"
        "00123118 002 2 118 1806 1004\n"
        "01010100 002 3 125 1790  996      40\n"
    )
    data = BytesIO()
    with ZipFile(data, "w") as archive:
        archive.writestr("bst_all.txt", text)
    modified = "Wed, 28 Oct 2026 05:04:08 GMT"
    route = respx.get(ARCHIVE_URL).mock(
        side_effect=[
            httpx.Response(200, content=data.getvalue(), headers={"Last-Modified": modified}),
            httpx.Response(200, content=b"invalid ZIP"),
        ],
    )
    result = await list_best_track_typhoons(1951)
    assert result["analysis"] == "best_track"
    assert result["data_as_of"] == "2026-10-28T05:04:08+00:00"
    assert result["items"][0]["typhoon_id"] == "5101"
    track = (await get_best_track(2001, 1))["track"]
    assert track["name"] == "CIMARON"
    assert track["revision_date"] == "2001-02-01"
    assert track["positions"][0]["time_utc"] == "2000-12-31T18:00:00+00:00"
    assert track["positions"][0]["longitude"] == -179.4
    assert track["positions"][0]["max_wind_kt"] is None
    assert track["positions"][1]["max_wind_kt"] == 40
    assert (await get_best_track(2001, 2))["track"] is None
    assert route.call_count == 1

    with closing(sqlite3.connect(tmp_path / "cache.sqlite3")) as db, db:
        db.execute("UPDATE snapshots SET checked = '2000-01-01T00:00:00+00:00'")
    stale = await list_best_track_typhoons(1951)
    assert stale["items"] == result["items"]
    assert stale["cache"]["refresh_failed"] is True
    assert (await get_best_track(2001, 1))["track"] == track
    assert route.call_count == 2
    assert route.calls[1].request.headers["If-Modified-Since"] == modified
