"""Allow `python -m app ...` to dispatch to the CLI."""

from app.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
