# ORBIT

**A local-first AI operating environment.**

ORBIT is an open-source platform for running, managing, and orchestrating AI on your own hardware. It is designed around capabilities rather than a fixed collection of services: models, agents, knowledge, automation, voice, vision, and tools are managed through a unified runtime.

## Project status

🚧 **Early development — control-plane rate limiting complete**

The project is being built as an independent architecture, with an emphasis on local-first operation, hardware awareness, privacy, modular runtimes, and a simple user experience.

## Current foundation

- Hardware discovery and normalized resource profiling
- Durable local model catalog
- Verified local model artifact lifecycle
- Compatibility scoring and resource placement
- Runtime adapter contract with a llama.cpp HTTP adapter
- Local state/configuration primitives
- Unified HTTP control-plane API
- OpenAI-compatible model and chat endpoint shapes
- Deterministic runtime routing with health/resource checks
- Routed streaming chat completions using Server-Sent Events
- Optional constant-time bearer API-key authentication for `/v1/*`
- Configurable process-local token-bucket rate limiting for `/v1/*`
- Health/readiness probes excluded from authentication and rate limiting
- Capability-based permissions
- Plugin manifest and registry contracts
- Python 3.11–3.13 CI, linting, type checking, and tests

## Control-plane security

ORBIT can protect its versioned control-plane endpoints with a local API key. Set `OrbitConfig.api_key` to enable authentication. Clients must then send `Authorization: Bearer <api-key>` for `/v1/*` requests. Health and readiness endpoints remain unauthenticated so local process supervisors can probe the service.

The control plane also supports `rate_limit_per_minute` and `rate_limit_burst`. The limiter is an in-process token bucket keyed by the authenticated identity, or by client address when authentication is disabled. A distributed deployment should enforce distributed limits at its reverse proxy or service boundary.

## Model lifecycle

The model lifecycle is now a complete local control-plane flow:

1. Register runtime-neutral model metadata with `POST /v1/models`.
2. Install a local artifact with `POST /v1/models/{id}/install`.
3. Verify file size and optional SHA-256 before activation.
4. Atomically move the verified artifact into ORBIT-managed storage.
5. Restore lifecycle state from durable metadata after restart.
6. Inspect lifecycle state with `GET /v1/models/{id}` or `GET /v1/models`.
7. Remove stopped models with `DELETE /v1/models/{id}`.

## Inference routing and streaming

Chat requests are resolved through the model catalog, resource scheduler, and runtime health checks before execution. Callers may leave runtime selection automatic or request a specific runtime.

`POST /v1/chat/completions` supports both buffered and streaming responses. With `"stream": true`, ORBIT returns Server-Sent Events containing OpenAI-compatible chat-completion chunks and terminates with `data: [DONE]`. Runtime failures are surfaced as structured streaming error events and recorded by the API metrics layer.

## Principles

- **Local-first:** your hardware and data come first.
- **Free and open source:** no mandatory subscription or hosted account.
- **Runtime-agnostic:** model runtimes are adapters, not the product architecture.
- **Hardware-aware:** ORBIT should make sensible resource decisions automatically.
- **Secure by default:** tools and agents operate under explicit capabilities.
- **Simple for users, powerful for developers:** advanced controls remain available without making them mandatory.

## Planned capabilities

- Remote model registries and resumable downloads
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
