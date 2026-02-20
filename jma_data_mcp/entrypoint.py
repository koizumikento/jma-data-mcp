"""Unified entrypoint for MCP server mode and CLI mode."""

from __future__ import annotations

import sys

from . import cli, server


def _normalize_exit_code(code: object) -> int:
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    return 1


def _run_server() -> int:
    try:
        server.main()
        return 0
    except SystemExit as exc:
        return _normalize_exit_code(exc.code)


def main(argv: list[str] | None = None) -> int:
    """Dispatch to server mode or CLI mode."""
    args = list(sys.argv[1:] if argv is None else argv)

    if not args or args[0] == "serve":
        return _run_server()

    try:
        return cli.main(args)
    except SystemExit as exc:
        return _normalize_exit_code(exc.code)
