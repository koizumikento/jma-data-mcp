import sys

from .cli import run_cli
from .server import create_server


def main() -> None:
    if sys.argv[1:] and sys.argv[1:] != ["serve"]:
        run_cli(sys.argv[1:])
    else:
        create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
