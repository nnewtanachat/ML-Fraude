FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    for i in 1 2 3 4 5; do \
      pip install --no-cache-dir -r requirements.txt && break; \
      echo "Attempt $i failed, retrying..."; \
      sleep 5; \
    done

# Copy application code + model
COPY src/ ./src/
COPY model/ ./model/

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser \
    && chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default: run API server
CMD ["uvicorn", "src.serve.main:app", "--host", "0.0.0.0", "--port", "8000"]
