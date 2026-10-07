"""Allow python -m boardsnap to use the same CLI as the installed command."""

from boardsnap.adapters.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
