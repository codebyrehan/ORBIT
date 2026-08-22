# ORBIT

**A local-first AI operating environment.**

ORBIT is an open-source platform for running, managing, and orchestrating AI on your own hardware. It is designed around capabilities rather than a fixed collection of services: models, agents, knowledge, automation, voice, vision, and tools are managed through a unified runtime.

## Project status

🚧 **Early development — production control plane + product-plane foundation**

The control plane, model lifecycle, routing, observability, security, recovery, browser dashboard, remote inference adapter, persistent projects/conversations, knowledge retrieval, capability-gated tools, agents, MCP HTTP compatibility, multimodal artifact handling, and production packaging foundations are implemented.

## Current foundation

- Hardware discovery and normalized resource profiling
- Durable local model catalog and verified local artifact lifecycle
- Compatibility scoring and resource placement
- Runtime adapter contract with llama.cpp and generic OpenAI-compatible remote adapters
- Unified HTTP control-plane API and OpenAI-compatible chat endpoint shapes
- Deterministic routing with health/resource checks and routed SSE streaming
- Bearer authentication, rate limiting, privacy-conscious request audit, backup/recovery and readiness probes
- Persistent SQLite product state for projects, conversations and messages
- Project-scoped knowledge ingestion with SHA-256 identity and lexical retrieval baseline
- Capability-gated built-in tools and MCP-compatible HTTP tool shim
- Persistent agent definitions with model routing and execution
- Audio/image upload, hashing and durable media inventory
- Replaceable voice/vision backend contracts
- Unified production entrypoint and Docker packaging
- Python 3.11–3.13 CI, linting, type checking, tests and release gates

## Remote AI runtime

ORBIT can use a remote service that implements the OpenAI-compatible API contract. Configure:

```bash
export ORBIT_OPENAI_API_KEY="your-provider-key"
export ORBIT_OPENAI_BASE_URL="https://api.openai.com/v1"
export ORBIT_OPENAI_MODEL="your-model-id"
export ORBIT_OPENAI_RUNTIME_NAME="openai-compatible"
```

When these variables are present and no model is already registered, ORBIT automatically registers the configured remote model and routes inference through the adapter. The adapter uses `/models` for health checks and `/chat/completions` for generation. API keys are read only from process environment and are never written to the audit log.

## Product-plane APIs

- `GET/POST /v1/projects` — durable projects
- `POST /v1/projects/{id}/conversations` — project chat sessions
- `GET/POST /v1/conversations/{id}` — conversation history and messages
- `POST /v1/projects/{id}/knowledge` — local knowledge ingestion
- `POST /v1/projects/{id}/knowledge/search` — retrieval baseline
- `GET/POST /v1/tools` and `POST /v1/tools/{name}/run` — capability-gated tools
- `POST /v1/mcp/tools/{name}` — MCP-compatible HTTP tool surface
- `GET/POST /v1/agents` and `POST /v1/agents/{id}/run` — agent definitions/execution
- `POST/GET /v1/media` — audio/image artifact ingestion and inventory
- `GET /v1/platform` — product capability matrix
- `GET /v1/packaging` — installation/container metadata
- `GET /control` — production control-center metadata

Voice and vision remain adapter-based: ORBIT securely stores media now, while heavier speech/vision engines can be installed without changing the control-plane contract.

## Control-plane security and auditability

ORBIT can protect its versioned control-plane endpoints with a local API key. Clients must send `Authorization: Bearer <api-key>` for `/v1/*` requests. Health and readiness remain unauthenticated for process supervisors.

The limiter is an in-process token bucket, and every request is recorded in a privacy-conscious append-only audit trail. Tool execution requires explicit capability grants and has no arbitrary shell execution path.

## Packaging

Build Python distributions with:

```bash
./scripts/package.sh
```

Build the production container with:

```bash
docker build -t orbit-ai .
```

The production container now starts `orbit.entrypoint:app`, which exposes the complete product-plane router.

## Principles

- **Local-first:** your hardware and data come first.
- **Free and open source:** no mandatory subscription or hosted account.
- **Runtime-agnostic:** inference engines are replaceable adapters.
- **Hardware-aware:** resource decisions are explicit and inspectable.
- **Secure by default:** tools and agents operate under explicit capabilities.
- **Simple for users, powerful for developers:** advanced controls remain available without making them mandatory.

## License

ORBIT is released under the Apache License 2.0.
