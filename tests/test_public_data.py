import json

import httpx
import pytest

from jma_data_mcp import api, cli, normals, warning_reports
from tests.public_data_fixtures import ANOMALIES_PATH, NORMALS_PATH, WARNING_PATH, public_files


@pytest.fixture
def upstream_files(monkeypatch):
    files = public_files()
    requests = []
    monkeypatch.setattr(normals, "_archive_cache", None)
    monkeypatch.setattr(warning_reports, "_feed_cache", None)

    def upstream(request):
        assert request.url.host == "www.data.jma.go.jp"
        requests.append(request.url.path)
        return httpx.Response(200, content=files[request.url.path])

    factory = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: factory(transport=httpx.MockTransport(upstream), **kwargs))
    return requests


async def test_normals_preserve_values_remarks_and_sample_years(upstream_files, monkeypatch):
    clock = [50]
    monkeypatch.setattr(normals, "monotonic", lambda: clock[0])
    result = await api.get_climate_normals("44132")
    temperature = result["metrics"]["mean_temperature"]
    assert len(temperature["monthly"]) == 12
    assert temperature["sample_years"] == 30
    assert temperature["monthly"]["2"] == {"value": None, "remark": 0}
    assert temperature["monthly"]["3"] == {"value": -0.7, "remark": 7}
    assert temperature["monthly"]["4"] == {"value": 0, "remark": 8}
    assert temperature["annual"] == {"value": 15.8, "remark": 8}
    one_month = await api.get_climate_normals("44132", month=1)
    assert one_month["metrics"]["mean_temperature"]["monthly"] == {"1": {"value": 5.4, "remark": 8}}
    with pytest.raises(ValueError, match="No monthly climate normals"):
        await api.get_climate_normals("99999")
    assert upstream_files == [NORMALS_PATH]
    clock[0] += 3600
    await api.get_climate_normals("44132")
    assert upstream_files == [NORMALS_PATH, NORMALS_PATH]


async def test_warning_filters_and_recent_scope(upstream_files):
    result = await api.list_weather_warning_reports(office="気象庁", limit=1)
    assert result["kind"] == "recent_bulletin_publications"
    assert result["total_matches"] == 2
    assert [r["bulletin_code"] for r in result["reports"]] == ["VPWW55"]
    result["reports"][0]["title"] = "local modification"
    all_reports = await api.list_weather_warning_reports()
    assert all_reports["reports"][0]["title"] == "気象警報・注意報"
    filtered = await api.list_weather_warning_reports(bulletin_code="VPWW53")
    assert filtered["total_matches"] == 1
    assert filtered["active_warning_status_url"] == "https://www.jma.go.jp/bosai/warning/"
    empty = await api.list_weather_warning_reports(office="札幌")
    assert empty["reports"] == []
    assert upstream_files == [WARNING_PATH]


def test_climate_anomalies_cli_bounds_years(upstream_files, capsys):
    assert cli.main(["climate", "anomalies", "--metric", "temperature", "--end-year", "1900"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["available_years"] == {"start_year": 1898, "end_year": 2025}
    assert result["annual"] == [{"year": 1898, "anomaly": -1.03}]
    assert cli.main(["climate", "anomalies", "--metric", "temperature", "--start-year", "1897"]) == 2
    assert "1898" in json.loads(capsys.readouterr().out)["error"]
    assert upstream_files == [ANOMALIES_PATH]
