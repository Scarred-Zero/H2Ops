FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 1. Bring in uv from Astral Docs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /server

# 2. System dependencies (cleaned up to keep image slim)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Copy ONLY the modern configuration mapping files
COPY pyproject.toml uv.lock ./

# 4. Corrected uv sync layout (Removed --system, added --no-dev to keep it slim)
RUN uv sync --frozen --no-install-project --no-dev --no-cache

# 5. Copy alembic config, migration scripts, and source code
COPY alembic.ini ./
COPY alembic/ ./alembic
COPY src/ ./src

EXPOSE 8000

# Note: Remove --reload when deploying this to actual production environments!
CMD ["sh", "-c", "uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --app-dir /server"]
