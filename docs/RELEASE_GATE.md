# ORBIT production activation gate

This checklist is the release contract for the real-AI product phase.

## Runtime

- [ ] Configure `ORBIT_OPENAI_API_KEY`, `ORBIT_OPENAI_BASE_URL`, and `ORBIT_OPENAI_MODEL` in the deployment secret store.
- [ ] Verify model registration and routing.
- [ ] Verify one real inference request and one streaming request.
- [ ] Verify provider timeout/failure produces a structured error and does not poison the process.

## RAG

- [x] Persist document chunks.
- [x] Persist deterministic embedding vectors.
- [x] Project-scope retrieval.
- [x] Source metadata and bounded context builder.
- [ ] Wire retrieval context into the production chat request path.
- [ ] Verify citations/sources in the UI.

## Agents and tools

- [x] Persistent agents.
- [x] Capability-gated tools.
- [x] MCP-compatible HTTP surface.
- [ ] Complete model -> tool -> result -> model loop.
- [ ] Persist execution/audit events for each tool call.

## Multimodal

- [x] Durable media storage and backend contracts.
- [ ] Configure STT backend and verify audio -> text.
- [ ] Configure TTS backend and verify text -> audio.
- [ ] Configure vision backend and verify image -> model context.

## Operations

- [x] Authentication foundation.
- [x] Rate limiting and readiness/metrics foundation.
- [x] Persistent recovery/backup foundation.
- [x] Idempotent SQLite migration runner.
- [ ] Run load/security/failure-injection gate against the release candidate.
- [ ] Verify restore from backup.

## Model management

- [x] Model catalog/lifecycle foundation.
- [ ] Production download/install UX.
- [ ] Checksum verification UX.
- [ ] Start/stop/delete UX.
- [ ] Storage usage reporting.

## Release

- [x] Python package metadata.
- [x] Production container entrypoint.
- [x] One-command distribution foundation.
- [ ] Run full test suite on release candidate.
- [ ] Promote the tested commit to `main`.
- [ ] Deploy and verify health/readiness/metrics plus core product smoke tests.
