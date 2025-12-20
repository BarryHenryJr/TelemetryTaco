FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry (version range for security updates while maintaining compatibility)
# Using pip install instead of curl-pipe pattern for integrity verification
# pip automatically verifies package checksums from PyPI
# Version range allows patch updates (1.8.x) for security fixes while preventing
# breaking changes from minor/major version updates
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_CACHE_DIR=/opt/poetry-cache
RUN pip install --no-cache-dir "poetry>=1.8.3,<1.9.0" \
    && poetry --version

# Configure Poetry: Don't create virtual environment, install dependencies to system
RUN poetry config virtualenvs.create false

# Copy Poetry files
# poetry.lock is required for reproducible builds
COPY pyproject.toml poetry.lock /app/

# Install dependencies
RUN poetry install --no-interaction --no-ansi

# Copy application code
COPY . /app/

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose.yml)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]