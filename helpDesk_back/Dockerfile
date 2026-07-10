# Use Python 3.12 slim image as base
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=2.3.0 \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN curl -sSL https://install.python-poetry.org | python3 - --version 2.3.0 && \
    ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

# Set work directory
WORKDIR /app

# Copy Poetry files
COPY pyproject.toml poetry.lock ./


# Configure Poetry and install dependencies (only main group for reproducible image)
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --only main -vvv && \
    rm -rf $POETRY_CACHE_DIR

    

# Copy application code
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set Python path to src directory
ENV PYTHONPATH=/app/src

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Run migrations then the application
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
