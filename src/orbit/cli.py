"""ORBIT command-line entry point."""

from __future__ import annotations

import argparse

from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orbit", description="Local-first AI operating environment"
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("start", help="initialize and start the ORBIT control plane")
    sub.add_parser("status", help="inspect local hardware and ORBIT state")
    sub.add_parser("serve", help="run the ORBIT HTTP API")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    app = OrbitApp(OrbitConfig.default())

    if args.command == "start":
        app.start()
        print(f"ORBIT is ready ({app.state.value})")
        return 0

    if args.command == "status":
        app.start()
        hardware = app.hardware
        assert hardware is not None
        memory_gb = (
            f"{hardware.memory_bytes / 1024**3:.1f} GiB"
            if hardware.memory_bytes
            else "unknown"
        )
        print(f"ORBIT: {app.state.value}")
        print(f"Platform: {hardware.platform} / {hardware.architecture}")
        print(f"Memory: {memory_gb}")
        for accelerator in hardware.accelerators:
            memory = (
                f"{accelerator.memory_bytes / 1024**3:.1f} GiB"
                if accelerator.memory_bytes
                else "memory unknown"
            )
            print(f"Accelerator: {accelerator.vendor.value} — {accelerator.name} ({memory})")
        return 0

    if args.command == "serve":
        import uvicorn

        uvicorn.run("orbit.api.server:app", host="127.0.0.1", port=8787, reload=False)
        return 0

    build_parser().print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
