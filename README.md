# Stock Analyst

A lightweight AI-driven stock research and analysis agent. It offers
an API for running a finance research agent that combines data from
yfinance, optional Pinecone vector storage, and reusable analysis
tools.

**Highlights**
- FastAPI-based HTTP endpoint for requesting stock analysis
- Modular `finance_agent` with tool plugins and storage adapters
- In-memory defaults with optional Pinecone integration for vectors

**Quick file map**
- `main.py` — application entrypoint
- `Interface/routes.py` — HTTP route(s) (e.g. `/v1/analyze-stock/`)
- `system/agents/finance_agent/` — agent logic and tool wrappers
- `system/utility/` — logging, schemas, and result storage helpers

## Quickstart
1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate    # macOS / Linux
.\\.venv\\Scripts\\activate   # Windows (PowerShell/CMD)
```

2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Run the app (development):

```bash
python main.py
# Open: http://127.0.0.1:8501/v1/analyze-stock/
```

## API
POST `/v1/analyze-stock/` — submit JSON matching `UserInputSchema`.
Minimal payload example:

```json
{ "ticker": "AAPL" }
```

The response contains the agent's analysis and any stored results
depending on configuration.

## Environment variables
Set these in your environment when needed; do not store secrets in
source control:

- `PINECONE_API_KEY` — enable Pinecone vector storage
- `PINECONE_ENV` — Pinecone environment
- `PINECONE_INDEX` — Pinecone index name
- `APP_NAME`, `USER_ID`, `SESSION_ID` — optional runtime metadata

## Tests
Run tests from the repository root:

```bash
pytest -q
```

## Storage
- `system/agents/finance_agent/tools/storage_tool.py` — Pinecone adapter
  with an in-memory fallback.
- `system/utility/result_storage.py` — thread-safe in-memory store
  with optional JSON persistence.

## Contributing / Notes
- Keep secrets out of the repo; use environment variables or secret
  managers.
- Run `black` and `isort` before opening PRs for consistency.
- If you want, I can run tests and apply formatting across the repo.

---
Updated README for clarity and quick onboarding.
