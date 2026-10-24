"""Verify the exact Windows candidate before the release job can publish it."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import locale
import os
import ssl
import subprocess
import sys
from email.parser import BytesParser
from importlib.metadata import version
from pathlib import Path

import certifi
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from PyInstaller.archive.readers import CArchiveReader


def verify_archive(executable: Path) -> dict[str, str]:
    """Compare bundled trust/runtime bytes and package metadata with this build."""
    archive = CArchiveReader(str(executable))
    members = {name.replace("\\", "/"): name for name in archive.toc}
    runtime = Path(sys.base_prefix)
    files = {
        "certifi/cacert.pem": Path(certifi.where()),
        f"python{sys.version_info.major}{sys.version_info.minor}.dll": runtime
        / f"python{sys.version_info.major}{sys.version_info.minor}.dll",
    }
    for pattern in ("libssl-*.dll", "libcrypto-*.dll"):
        matches = list((runtime / "DLLs").glob(pattern))
        if len(matches) != 1:
            raise ValueError(f"Expected one build-runtime DLL matching {pattern}")
        files[matches[0].name] = matches[0]
    hashes = {}
    for name, source in files.items():
        bundled = archive.extract(members[name])
        if bundled != source.read_bytes():
            raise ValueError(f"Bundled file does not match build environment: {name}")
        hashes[name] = hashlib.sha256(bundled).hexdigest()
    metadata_name = f"jma_data_mcp-{version('jma-data-mcp')}.dist-info/METADATA"
    metadata = BytesParser().parsebytes(archive.extract(members[metadata_name]))
    if metadata["Version"] != version("jma-data-mcp"):
        raise ValueError("Bundled package version mismatch")
    return hashes


async def smoke_test(executable: Path, https: bool) -> None:
    subprocess.run([str(executable), "--help"], capture_output=True, check=True, timeout=30)
    output = subprocess.run(
        [str(executable), "--version"], capture_output=True, check=True, timeout=30,
    )
    if output.stdout.decode("ascii").strip() != f"jma-data-mcp {version('jma-data-mcp')}":
        raise ValueError("Executable version mismatch")
    output = subprocess.run(
        [str(executable), "station", "get", "--code", "44132"],
        capture_output=True, check=True, timeout=30,
    )
    station = json.loads(output.stdout.decode(locale.getpreferredencoding(False)))
    if station["code"] != "44132":
        raise ValueError("Executable station lookup failed")
    if https and any(os.environ.get(name) for name in ("SSL_CERT_FILE", "SSL_CERT_DIR")):
        raise ValueError("Remove custom CA overrides before the release HTTPS test")
    transport = StdioTransport(command=str(executable), args=["serve"], env={"PYTHONUTF8": "1"})
    async with Client(transport, mode="legacy", timeout=60) as client:
        if client.server_info is None or client.server_info.version != version("jma-data-mcp"):
            raise ValueError("Executable MCP version mismatch")
        if len(await client.list_tools()) != 11:
            raise ValueError("Executable MCP tool discovery failed")
        station_result = await client.call_tool("get_station_info", {"code": "44132"})
        if station_result.data["code"] != "44132":
            raise ValueError("Executable MCP station lookup failed")
        if https:
            forecast = await client.call_tool("get_forecast", {"prefecture": "tokyo"})
            if not forecast.data.get("forecast"):
                raise ValueError("Executable HTTPS forecast lookup failed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--https", action="store_true", help="Require a live JMA HTTPS request")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if sys.platform != "win32":
        parser.error("Run with the Windows build environment")
    if sys.version.split()[0] != (root / ".python-version").read_text().strip():
        raise ValueError("Build Python does not match .python-version")
    hashes = verify_archive(args.executable)
    asyncio.run(smoke_test(args.executable.resolve(), args.https))
    report = {
        "source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "uv_lock_sha256": hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest(),
        "version": version("jma-data-mcp"),
        "python": sys.version.split()[0],
        "openssl": ssl.OPENSSL_VERSION,
        "certifi": version("certifi"),
        "pyinstaller": version("pyinstaller"),
        "exe_sha256": hashlib.sha256(args.executable.read_bytes()).hexdigest(),
        "bundled_sha256": hashes,
        "help_version_station_stdio": "passed",
        "jma_https": "passed" if args.https else "not_run",
    }
    serialized = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.write_text(serialized, encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
