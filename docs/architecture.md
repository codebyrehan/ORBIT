# ORBIT Architecture

## Direction

ORBIT is organized around **capabilities and stable contracts**, not around a fixed set of containerized services.

The control plane owns configuration, lifecycle, hardware capabilities, model selection, routing, scheduling, events, secrets, and health. Inference engines and other AI systems are replaceable adapters behind runtime interfaces.

```text
                    ORBIT Control Plane
                           |
             +-------------+-------------+
             |             |             |
          Hardware      Models       Runtimes
             |             |             |
             +-------------+-------------+
                           |
                    Resource Scheduler
                           |
          +----------------+----------------+
          |                |                |
       Agents            Media          Knowledge
          |                |                |
          +----------------+----------------+
                           |
                    ORBIT User Experience
```

## Design rules

1. **Local-first:** local execution is the default product path.
2. **Runtime-agnostic:** no inference backend is part of the core contract.
3. **Hardware-aware:** resource decisions are represented as data and capabilities.
4. **Small core:** heavyweight integrations belong in adapters or capabilities.
5. **Explicit permissions:** tools and agents must have bounded capabilities.
6. **Stable contracts:** UI, CLI, API, and integrations should depend on core interfaces rather than implementation details.
7. **Best-effort discovery:** hardware detection must degrade gracefully when vendor utilities are unavailable.
8. **Deterministic placement:** model placement produces explainable decisions before any process is launched.

## Current boundaries

- `core.config` — typed process configuration and local state location.
- `core.hardware` — normalized hardware and accelerator capabilities.
- `core.hardware_detect` — dependency-light host discovery.
- `core.runtime` — inference backend contract.
- `core.runtime_manager` — runtime adapter registration and selection.
- `core.models` — runtime-neutral model metadata and compatibility scoring.
- `core.scheduler` — resource-aware model placement decisions.
- `core.lifecycle` — control-plane lifecycle states.
- `core.app` — application bootstrap and lifecycle orchestration.
- `cli` — human-facing command line entry point.

Future layers will add routing, knowledge, agents, plugins, persistence, and the Control Center without changing the foundational contracts unnecessarily.
