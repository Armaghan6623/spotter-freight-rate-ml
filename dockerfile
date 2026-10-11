FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --locked --no-install-project

COPY pipeline/ ./pipeline/
COPY sql/ ./sql/
COPY data/ ./data/

CMD ["python", "-m", "pipeline.pipeline", "--skip-missing"]
