FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project || uv sync --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev || uv sync --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "jobact.apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# The speech worker is isolated so API/general-worker images do not carry
# Whisper/PyAV/model dependencies.
FROM base AS stt
RUN uv sync --frozen --no-dev --extra stt || uv sync --no-dev --extra stt
CMD ["python", "-m", "jobact.apps.stt_worker"]
