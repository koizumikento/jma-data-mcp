from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from io import BytesIO
from typing import Any
from zipfile import ZipFile

from ._cache import Document

PAGE_URL = "https://www.jma.go.jp/jma/jma-eng/jma-center/rsmc-hp-pub-eg/besttrack.html"
ARCHIVE_URL = "https://www.jma.go.jp/jma/jma-eng/jma-center/rsmc-hp-pub-eg/Besttracks/bst_all.zip"


def _read_position(line: str, year: int) -> dict[str, Any]:
    if len(line) < 28 or line[9:12] != "002":
        raise ValueError("Invalid position in the JMA best track archive.")
    offset = (int(line[:2]) - year + 1) % 100 - 1
    if offset > 1:
        raise ValueError("JMA best track position is outside the typhoon season.")
    observed = datetime(year + offset, int(line[2:4]), int(line[4:6]), int(line[6:8]), tzinfo=UTC)
    latitude, longitude = int(line[15:18]) / 10, int(line[19:23]) / 10
    if not 0 <= latitude <= 90 or not 0 <= longitude <= 360:
        raise ValueError("Invalid coordinates in the JMA best track archive.")
    return {
        "time_utc": observed.isoformat(),
        "latitude": latitude,
        "longitude": round(longitude - 360, 1) if longitude > 180 else longitude,
        "central_pressure_hpa": int(line[24:28].strip() or 0) or None,
        "max_wind_kt": int(line[33:36].strip() or 0) or None,
        "grade": int(line[13]),
    }


def load_best_tracks(fetch: Callable[[str], Document], current_year: int) -> dict[str, Any]:
    document = fetch(ARCHIVE_URL)
    with ZipFile(BytesIO(document.body)) as archive:
        try:
            entry = archive.getinfo("bst_all.txt")
        except KeyError as exc:
            raise ValueError("JMA best track ZIP is missing bst_all.txt.") from exc
        if entry.file_size > 16 * 1024 * 1024:
            raise ValueError("JMA best track text exceeds the extraction limit.")
        lines = iter(archive.read(entry).decode("ascii").splitlines())

    tracks: dict[str, dict[str, Any]] = {}
    for header in lines:
        typhoon_id = header[6:10]
        if (
            len(header) < 72
            or header[:5] != "66666"
            or len(typhoon_id) != 4
            or not typhoon_id.isdigit()
            or typhoon_id[2:] == "00"
            or typhoon_id in tracks
        ):
            raise ValueError("Invalid typhoon header in the JMA best track archive.")
        year = current_year - (current_year - int(typhoon_id[:2])) % 100
        count = int(header[12:15])
        if year < 1951 or count < 1:
            raise ValueError("Invalid year or position count in the JMA best track archive.")
        positions = [_read_position(next(lines, ""), year) for _ in range(count)]
        tracks[typhoon_id] = {
            "typhoon_id": typhoon_id,
            "number": int(typhoon_id[2:]),
            "name": header[30:50].strip(),
            "year": year,
            "revision_date": datetime.strptime(header[64:72], "%Y%m%d").date().isoformat(),
            "positions": positions,
        }

    if not tracks or min(track["year"] for track in tracks.values()) != 1951:
        raise ValueError("JMA best track archive is missing its 1951 starting season.")
    updated = parsedate_to_datetime(document.last_modified) if document.last_modified else None
    return {
        "data_as_of": updated.isoformat() if updated else None,
        "source_urls": [PAGE_URL, ARCHIVE_URL],
        "tracks": tracks,
    }
