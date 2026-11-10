"""Recent weather warning publications in the official JMA Atom feed."""

import re
from datetime import datetime
from time import monotonic
from typing import Any
from xml.etree import ElementTree as ET

from .public_files import fetch_public_file

WARNING_FEED_URL = "https://www.data.jma.go.jp/developer/xml/feed/extra_l.xml"
WARNING_STATUS_URL = "https://www.jma.go.jp/bosai/warning/"
WARNING_CODES = frozenset(f"VPWW{number}" for number in range(53, 62))
ATOM = "{http://www.w3.org/2005/Atom}"
BULLETIN_URL = re.compile(
    r"https://www\.data\.jma\.go\.jp/developer/xml/data/"
    r"[0-9]{14}_[0-9]+_(VPWW[0-9]{2})_[0-9]{6}\.xml"
)
_feed_cache: tuple[float, tuple[str, list[dict[str, str]]]] | None = None


async def _load_feed() -> tuple[str, list[dict[str, str]]]:
    global _feed_cache
    if _feed_cache and monotonic() < _feed_cache[0]:
        return _feed_cache[1]
    data = await fetch_public_file(WARNING_FEED_URL, 16 * 1024 * 1024)
    document = data.decode("utf-8")
    if "<!DOCTYPE" in document:
        raise ValueError("Unexpected XML document type in JMA warning feed")
    feed = ET.fromstring(document)
    updated = feed.findtext(f"{ATOM}updated")
    if feed.tag != f"{ATOM}feed" or not updated:
        raise ValueError("Unexpected JMA warning feed format")
    reports: dict[str, dict[str, str]] = {}
    for entry in feed.findall(f"{ATOM}entry"):
        link = entry.find(f"{ATOM}link")
        url = link.get("href", "") if link is not None else ""
        match = BULLETIN_URL.fullmatch(url)
        if match is None or match[1] not in WARNING_CODES:
            continue
        published_at = entry.findtext(f"{ATOM}updated")
        if not published_at:
            raise ValueError("Missing timestamp in JMA warning bulletin")
        reports[url] = {
            "bulletin_code": match[1],
            "updated_at": published_at,
            "title": entry.findtext(f"{ATOM}title", ""),
            "office": entry.findtext(f"{ATOM}author/{ATOM}name", ""),
            "summary": entry.findtext(f"{ATOM}content", ""),
            "source_url": url,
        }
    result = (
        updated,
        sorted(reports.values(), key=lambda report: datetime.fromisoformat(report["updated_at"]), reverse=True),
    )
    _feed_cache = (monotonic() + 60, result)
    return result


async def fetch_weather_warning_reports(
    office: str | None,
    bulletin_code: str | None,
    limit: int,
) -> dict[str, Any]:
    if not 1 <= limit <= 50:
        raise ValueError("Limit must be between 1 and 50")
    if bulletin_code is not None and bulletin_code not in WARNING_CODES:
        raise ValueError("Bulletin code must be VPWW53 through VPWW61")
    if office is not None:
        office = office.strip()
        if not 1 <= len(office) <= 80:
            raise ValueError("Office filter must contain 1 to 80 characters")

    updated, reports = await _load_feed()
    matches = [
        report for report in reports
        if (office is None or office in report["office"])
        and (bulletin_code is None or bulletin_code == report["bulletin_code"])
    ]
    return {
        "kind": "recent_bulletin_publications",
        "source_url": WARNING_FEED_URL,
        "feed_updated_at": updated,
        "active_warning_status_url": WARNING_STATUS_URL,
        "total_matches": len(matches),
        "reports": [report.copy() for report in matches[:limit]],
    }
