# ORBIT Phase Completion

This document is the release checklist for the product-plane activation phase.

## Engineering gates

- [ ] Semantic RAG is wired to the product knowledge API and chat context.
- [ ] Real model provider is configured through deployment secrets; no credentials are committed.
- [ ] Streaming chat is exercised end-to-end against the configured runtime.
- [ ] Agent execution can invoke capability-gated tools and return tool results to the model.
- [ ] STT, TTS, and vision adapters are connected to concrete providers where configured.
- [ ] Authentication, authorization, rate limiting, audit, recovery, and load checks pass.
- [ ] Model lifecycle operations are exposed in the product UI/API.
- [ ] Database migrations and rollback/recovery procedures are tested.
- [ ] Docker/package/release artifacts are reproducible and production health checks pass.

## Provider activation

ORBIT deliberately does not store provider credentials in Git. Configure these at deployment time:

- `ORBIT_OPENAI_API_KEY`
- `ORBIT_OPENAI_BASE_URL`
- `ORBIT_OPENAI_MODEL`

For multimodal providers, configure their provider-specific secrets using the deployment secret manager. The control plane remains provider-neutral.

## Release gate

A release is complete only when CI is green, the selected provider answers a real inference request, knowledge retrieval returns project-scoped sources, streaming produces incremental events, capability checks reject unauthorized tools, media upload succeeds, migrations run idempotently, and `/health` plus `/ready` report healthy in the target deployment.
