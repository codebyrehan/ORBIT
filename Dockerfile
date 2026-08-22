FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ORBIT_DATA_DIR=/var/lib/orbit

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 orbit \
    && mkdir -p /var/lib/orbit \
    && chown -R orbit:orbit /app /var/lib/orbit

USER orbit
EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -m orbit.cli health || exit 1

CMD ["uvicorn", "orbit.api.server:app", "--host", "0.0.0.0", "--port", "8787"]
