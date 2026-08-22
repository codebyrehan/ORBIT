"""ORBIT command-line interface."""

from __future__ import annotations

import argparse
import json
import sys

from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig
from orbit.core.health import HealthStatus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orbit", description="Local-first AI operating environment")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("start", help="initialize and start the ORBIT control plane")
    sub.add_parser("status", help="inspect local hardware and ORBIT state")
    sub.add_parser("health", help="run component health checks")
    sub.add_parser("serve", help="run the ORBIT HTTP API")
    models = sub.add_parser("models", help="inspect the local model catalog")
    models.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser


def _new_app() -> OrbitApp:
    app = OrbitApp(OrbitConfig.default())
    app.start()
    return app


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "start":
        app = _new_app()
        print(f"ORBIT is ready ({app.state.value})")
        return 0

    if args.command == "status":
        app = _new_app()
        hardware = app.hardware
        assert hardware is not None
        memory = f"{hardware.memory_bytes / 1024**3:.1f} GiB" if hardware.memory_bytes else "unknown"
        print(f"ORBIT: {app.state.value}")
        print(f"Platform: {hardware.platform} / {hardware.architecture}")
        print(f"Memory: {memory}")
        print(f"Models: {len(app.models.all())}")
        for accelerator in hardware.accelerators:
            accelerator_memory = f"{accelerator.memory_bytes / 1024**3:.1f} GiB" if accelerator.memory_bytes else "unknown"
            print(f"Accelerator: {accelerator.vendor.value} — {accelerator.name} ({accelerator_memory})")
        return 0

    if args.command == "health":
        app = _new_app()
        checks = app.health.check()
        for check in checks:
            print(f"{check.status.value:10} {check.name}: {check.detail}")
        return 0 if app.health.overall() is HealthStatus.HEALTHY else 1

    if args.command == "models":
        app = _new_app()
        data = [{"id": model.model_id, "modality": model.modality.value, "capabilities": sorted(model.capabilities)} for model in app.models.all()]
        if args.json:
            print(json.dumps(data, indent=2))
        elif not data:
            print("No models registered.")
        else:
            for model in data:
                print(f"{model['id']} [{model['modality']}] — {', '.join(model['capabilities']) or 'no capabilities'}")
        return 0

    if args.command == "serve":
        import uvicorn
        uvicorn.run("orbit.api.server:app", host="127.0.0.1", port=8787, reload=False)
        return 0

    build_parser().print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
