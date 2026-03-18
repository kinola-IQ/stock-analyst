# ---------- Builder stage ----------
FROM python:3.11-slim AS builder

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
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

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# ---------- Runtime stage ----------
FROM python:3.11-slim AS runtime

# Install runtime deps (curl + ca-certificates needed for installer)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install Ollama as root (installer requires root privileges)
RUN curl -fsSL https://ollama.com/install.sh | sh

# Create non-root user and app dir
RUN useradd --create-home appuser
WORKDIR /home/appuser/app

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --from=builder /app /home/appuser/app

# Add entrypoint script (will start ollama and pull models at runtime)
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set ownership and switch to non-root user
RUN chown -R appuser:appuser /home/appuser/app
USER appuser

EXPOSE 8501
ENV PYTHONUNBUFFERED=1
ENV PORT=8501

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8501", "--loop", "uvloop", "--workers", "1"]