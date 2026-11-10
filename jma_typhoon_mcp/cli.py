import asyncio
import json
import sys
from argparse import SUPPRESS, ArgumentParser
from collections.abc import Sequence

import httpx

from .client import (
    get_best_track,
    get_typhoon_track,
    list_best_track_typhoons,
    list_typhoons,
    refresh_cache,
)


def run_cli(argv: Sequence[str]) -> None:
    parser = ArgumentParser(prog="jma-typhoon-mcp")
    commands = parser.add_subparsers(required=True)

    command = commands.add_parser("list-typhoons", argument_default=SUPPRESS)
    command.add_argument("--year", type=int, required=True)
    command.set_defaults(handler=list_typhoons)

    command = commands.add_parser("get-typhoon-track", argument_default=SUPPRESS)
    command.add_argument("--year", type=int, required=True)
    command.add_argument("--number", type=int, required=True)
    command.set_defaults(handler=get_typhoon_track)

    command = commands.add_parser("list-best-track-typhoons", argument_default=SUPPRESS)
    command.add_argument("--year", type=int, required=True)
    command.set_defaults(handler=list_best_track_typhoons)

    command = commands.add_parser("get-best-track", argument_default=SUPPRESS)
    command.add_argument("--year", type=int, required=True)
    command.add_argument("--number", type=int, required=True)
    command.set_defaults(handler=get_best_track)

    command = commands.add_parser("refresh", argument_default=SUPPRESS)
    command.add_argument("--year", type=int, required=True)
    command.set_defaults(handler=refresh_cache)

    arguments = vars(parser.parse_args(argv))
    handler = arguments.pop("handler")
    try:
        result = asyncio.run(handler(**arguments))
    except (ValueError, OSError, httpx.HTTPError) as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8"))
