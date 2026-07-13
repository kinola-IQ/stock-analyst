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

# Create non-root user and app dir
RUN useradd --create-home appuser
WORKDIR /home/appuser/app

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --from=builder /app /home/appuser/app

# Set ownership and switch to non-root user
RUN chown -R appuser:appuser /home/appuser/app
USER appuser

EXPOSE 8501
ENV PYTHONUNBUFFERED=1
ENV APP_NAME=stock-analyst
ENV USER_ID=default-user
ENV SESSION_ID=default-session
ENV HOST=0.0.0.0
ENV PORT=8501

CMD ["python", "main.py"]
