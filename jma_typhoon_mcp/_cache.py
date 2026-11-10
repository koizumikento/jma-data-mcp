import asyncio
import csv
import json
import os
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zipfile import BadZipFile

import httpx


@dataclass
class Document:
    body: bytes
    etag: str | None
    last_modified: str | None


@dataclass
class Snapshot:
    data: dict[str, Any]
    checked_at: datetime
    fetched_at: datetime
    refresh_failed: bool = False

    def metadata(self) -> dict[str, Any]:
        return {
            "data_as_of": self.data["data_as_of"],
            "source_urls": self.data["source_urls"],
            "cache": {
                "checked_at": self.checked_at.isoformat(),
                "fetched_at": self.fetched_at.isoformat(),
                "refresh_failed": self.refresh_failed,
            },
        }


Loader = Callable[[Callable[[str], Document]], dict[str, Any]]


def cache_path(repo: str, env_name: str) -> Path:
    override = os.environ.get(env_name)
    if override:
        return Path(override).expanduser() / "cache.sqlite3"
    cache_root = (
        os.environ.get("LOCALAPPDATA") if os.name == "nt" else os.environ.get("XDG_CACHE_HOME")
    )
    root = Path(cache_root) if cache_root else Path.home() / ".cache"
    return root / repo / "cache.sqlite3"


async def load_snapshot(
    path: Path, key: str, ttl: timedelta, loader: Loader, *, force: bool = False
) -> Snapshot:
    return await asyncio.to_thread(_load, path, key, ttl, loader, force=force)


def _load(path: Path, key: str, ttl: timedelta, loader: Loader, *, force: bool) -> Snapshot:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=90)) as db, db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS snapshots ("
            "key TEXT PRIMARY KEY, payload TEXT, checked TEXT, fetched TEXT, retry_after TEXT)"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS documents ("
            "key TEXT, url TEXT, body BLOB, etag TEXT, modified TEXT, PRIMARY KEY (key, url))"
        )
        # Share one refresh across processes. A failed download never replaces the snapshot.
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT payload, checked, fetched, retry_after FROM snapshots WHERE key = ?", (key,)
        ).fetchone()
        now = datetime.now(UTC)
        previous = None
        if row:
            payload, checked, fetched, retry_after = row
            previous = Snapshot(
                json.loads(payload),
                datetime.fromisoformat(checked),
                datetime.fromisoformat(fetched),
                bool(retry_after),
            )
            if not force and (
                now - previous.checked_at < ttl
                or (retry_after and now < datetime.fromisoformat(retry_after))
            ):
                return previous

        documents: dict[str, Document] = {}
        with httpx.Client(timeout=15, follow_redirects=False) as client:

            def fetch(url: str) -> Document:
                stored = db.execute(
                    "SELECT body, etag, modified FROM documents WHERE key = ? AND url = ?",
                    (key, url),
                ).fetchone()
                headers = {}
                if stored and stored[1]:
                    headers["If-None-Match"] = stored[1]
                if stored and stored[2]:
                    headers["If-Modified-Since"] = stored[2]
                with client.stream("GET", url, headers=headers) as response:
                    if response.status_code == 304 and stored:
                        document = Document(*stored)
                    else:
                        response.raise_for_status()
                        body = bytearray()
                        for chunk in response.iter_bytes():
                            body.extend(chunk)
                            if len(body) > 32 * 1024 * 1024:
                                raise ValueError("Official data file exceeds the download limit.")
                        document = Document(
                            bytes(body),
                            response.headers.get("ETag"),
                            response.headers.get("Last-Modified"),
                        )
                documents[url] = document
                return document

            try:
                data = loader(fetch)
            except (httpx.HTTPError, ValueError, OSError, BadZipFile, csv.Error) as exc:
                if previous is None:
                    raise ValueError(
                        f"No cached copy. Official data could not be loaded: {exc}"
                    ) from exc
                previous.refresh_failed = True
                db.execute(
                    "UPDATE snapshots SET retry_after = ? WHERE key = ?",
                    ((datetime.now(UTC) + timedelta(minutes=15)).isoformat(), key),
                )
                return previous

        checked_at = datetime.now(UTC)
        fetched_at = previous.fetched_at if previous and previous.data == data else checked_at
        db.execute("DELETE FROM documents WHERE key = ?", (key,))
        db.executemany(
            "INSERT INTO documents VALUES (?, ?, ?, ?, ?)",
            [(key, url, doc.body, doc.etag, doc.last_modified) for url, doc in documents.items()],
        )
        db.execute(
            "INSERT OR REPLACE INTO snapshots VALUES (?, ?, ?, ?, NULL)",
            (
                key,
                json.dumps(data, ensure_ascii=False),
                checked_at.isoformat(),
                fetched_at.isoformat(),
            ),
        )
        return Snapshot(data, checked_at, fetched_at)
