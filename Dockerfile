# Lovelight: FastAPI + SQLite. Build: docker build -t lovelight .  Run: docker run -p 8000:8000 -v lovelight-data:/data lovelight

FROM ghcr.io/astral-sh/uv:0.9.3 AS uv

FROM python:3.12-slim AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
# Dependencies first (cached layer), then the project itself; both pinned by uv.lock.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY README.md LICENSE ./
COPY src ./src
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --no-create-home app
WORKDIR /app
# Code and venv stay root-owned (read-only for the app user); only the upload inbox and /data are writable.
COPY --from=build /app /app
COPY data/generated ./data/generated
COPY data/invoiceReceivables.csv ./data/invoiceReceivables.csv
RUN mkdir -p /app/data/incoming /app/data/cache /data && chown app:app /app/data/incoming /app/data/cache /data
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 LOVELIGHT_DB=/data/lovelight.db
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"]
USER 10001:10001
CMD ["uvicorn", "lovelight.server:app", "--host", "0.0.0.0", "--port", "8000"]
