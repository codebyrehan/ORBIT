# ORBIT Architecture

## Direction

ORBIT is organized around **capabilities and stable contracts**, not around a fixed set of containerized services.

The control plane owns configuration, lifecycle, hardware capabilities, model selection, routing, scheduling, events, secrets, and health. Inference engines and other AI systems are replaceable adapters behind runtime interfaces.

```text
                    ORBIT Control Plane
                           |
                    ORBIT Runtime Layer
                           |
          +----------------+----------------+
          |                |                |
       Models            Agents           Media
          |                |                |
          +----------------+----------------+
                           |
                    Knowledge / Data
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

## Initial boundaries

- `core.config` — typed process configuration and local state location.
- `core.hardware` — normalized hardware and accelerator capabilities.
- `core.runtime` — inference backend contract.
- `core.lifecycle` — control-plane lifecycle states.
- `core.app` — application bootstrap and lifecycle orchestration.
- `cli` — human-facing command line entry point.

Future layers will add model registry, scheduler, routing, knowledge, agents, plugins, and the Control Center without changing the foundational contracts unnecessarily.
