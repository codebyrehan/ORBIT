# Real AI provider activation

ORBIT supports OpenAI-compatible remote and self-hosted runtimes. The application keeps the demo runtime only as a fallback when `ORBIT_ENABLE_DEMO_MODEL=true` and no configured real model is available.

## OpenAI-compatible endpoint

Set:

```text
ORBIT_OPENAI_BASE_URL=https://your-provider.example/v1
ORBIT_OPENAI_MODEL=your-model-id
ORBIT_OPENAI_API_KEY=your-secret
ORBIT_OPENAI_RUNTIME_NAME=openai-compatible
```

For a local/self-hosted endpoint that does not require authentication, leave `ORBIT_OPENAI_API_KEY` empty.

## llama.cpp server

Start an OpenAI-compatible llama.cpp server and set:

```text
ORBIT_LLAMA_CPP_URL=http://127.0.0.1:8080
ORBIT_LLAMA_CPP_MODEL=your-model-id
```

## Verify before production

Run:

```bash
python scripts/provider_smoke.py
```

The smoke check exits non-zero when no provider/model is configured or when the provider cannot answer `GET /v1/models`.

Then exercise ORBIT's normal chat endpoint using the model ID returned by the provider. Streaming uses the same runtime selection path.

## Render

Do not commit provider secrets. Configure them as Render environment variables. Keep `ORBIT_ENABLE_DEMO_MODEL=true` until real inference has been verified; then it may be disabled to make missing provider configuration fail visibly instead of silently falling back.
