# ORBIT

**A local-first AI operating environment.**

ORBIT is an open-source platform for running, managing, and orchestrating AI on your own hardware. It is designed around capabilities rather than a fixed collection of services: models, agents, knowledge, automation, voice, vision, and tools are managed through a unified runtime.

## Project status

🚧 **Early development — runtime/API foundation in progress**

The project is being built as an independent architecture, with an emphasis on local-first operation, hardware awareness, privacy, modular runtimes, and a simple user experience.

## Current foundation

- Hardware discovery and normalized resource profiling
- Durable local model catalog
- Compatibility scoring and resource placement
- Runtime adapter contract with a llama.cpp HTTP adapter
- Local state/configuration primitives
- Unified HTTP control-plane API
- OpenAI-compatible model and chat endpoint shapes
- Capability-based permissions
- Plugin manifest and registry contracts
- Python 3.11–3.13 CI, linting, type checking, and tests

## Principles

- **Local-first:** your hardware and data come first.
- **Free and open source:** no mandatory subscription or hosted account.
- **Runtime-agnostic:** model runtimes are adapters, not the product architecture.
- **Hardware-aware:** ORBIT should make sensible resource decisions automatically.
- **Secure by default:** tools and agents operate under explicit capabilities.
- **Simple for users, powerful for developers:** advanced controls remain available without making them mandatory.

## Planned capabilities

- Native model installation and lifecycle management
- Automatic runtime selection and model placement
- Native chat and projects
- Knowledge and retrieval
- Agents, tools, MCP, and memory
- Voice, vision, and image capabilities
- Automation and background tasks
- Plugin SDK and isolated tool execution
- Control Center and system observability
- Cross-platform packaging and one-command setup

## License

ORBIT is released under the Apache License 2.0.

## Development

The initial implementation is Python-based. The repository is intentionally starting with small, testable contracts so heavyweight runtimes and UI layers can be integrated without turning infrastructure details into the product architecture.
