# ORBIT

**A local-first AI operating environment.**

ORBIT is an open-source platform for running, managing, and orchestrating AI on your own hardware. It is designed around capabilities rather than a fixed collection of services: models, agents, knowledge, automation, voice, vision, and tools are managed through a unified runtime.

## Project status

🚧 **Early development — Phase 0**

The project is being built as an independent architecture, with an emphasis on local-first operation, hardware awareness, privacy, modular runtimes, and a simple user experience.

## Principles

- **Local-first:** your hardware and data come first.
- **Free and open source:** no mandatory subscription or hosted account.
- **Runtime-agnostic:** model runtimes are adapters, not the product architecture.
- **Hardware-aware:** ORBIT should make sensible resource decisions automatically.
- **Secure by default:** tools and agents operate under explicit capabilities.
- **Simple for users, powerful for developers:** advanced controls remain available without making them mandatory.

## Planned capabilities

- Hardware discovery and resource profiling
- Local model lifecycle and model catalog
- Runtime adapters for local inference engines
- Unified OpenAI-compatible API
- Native chat and projects
- Knowledge and retrieval
- Agents, tools, MCP, and memory
- Voice, vision, and image capabilities
- Automation and background tasks
- Plugin SDK
- Control Center and system observability

## License

ORBIT is intended to be released under the Apache License 2.0.

## Development

The initial implementation is Python-based. The repository is intentionally starting small so the core contracts can be established before adding heavyweight runtimes or UI dependencies.
