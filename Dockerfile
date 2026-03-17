# ---------- Builder stage ----------
FROM python:3.11-slim AS builder

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    Ollama \
    build-essential \
    gcc \
    libpq-dev \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only dependency files first for caching
COPY requirements.txt .

# Create virtualenv to isolate build artifacts
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Optional: run tests or build steps here
# RUN pytest -q

# ---------- Runtime stage ----------
FROM python:3.11-slim AS runtime

# Create non-root user
RUN useradd --create-home appuser
WORKDIR /home/appuser/app

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code (only what is needed)
COPY --from=builder /app /home/appuser/app

# Set permissions
RUN chown -R appuser:appuser /home/appuser/app
USER appuser

# pulling model
RUN Ollama pull qwen3:4b

# Expose port and set environment defaults
EXPOSE 8501
ENV PYTHONUNBUFFERED=1
ENV PORT=8501

# Default command: run Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8501", "--loop", "uvloop", "--workers", "1"]
