#!/usr/bin/env bash
set -e

# Start ollama daemon in the background and wait for it to become available,
# then pull the model once at container startup.
# If Ollama binary uses root-only resources, adjust user/permissions accordingly.

ollama serve &            # start daemon in background
OLLAMA_SERVE_PID=$!

# simple wait loop: check until `ollama` responds (adjust timeout if necessary)
MAX_WAIT=30
WAITED=0
while ! ollama version >/dev/null 2>&1; do
  sleep 1
  WAITED=$((WAITED+1))
  if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    echo "Timeout waiting for ollama to start" >&2
    exit 1
  fi
done

# Pull model (idempotent; will skip if already present)
ollama pull qwen3:4b || echo "Model pull failed or already present"

# replace this shell with the command from CMD (uvicorn)
exec "$@"