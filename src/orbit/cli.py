"""ORBIT command-line entry point."""

from __future__ import annotations

import argparse

from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orbit", description="Local-first AI operating environment")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("start", help="initialize and start the ORBIT control plane")
    sub.add_parser("status", help="show local ORBIT status")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    app = OrbitApp(OrbitConfig.default())

    if args.command == "start":
        app.start()
        print(f"ORBIT is ready ({app.state.value})")
        return 0

    if args.command == "status":
        print(f"ORBIT: {app.state.value}")
        return 0

    build_parser().print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
