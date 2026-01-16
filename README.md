**Project Overview**
- **Name:**: Stock Analyst
- **Description:**: A FastAPI application that runs a finance analysis agent to analyze stock tickers using a streaming agent runner and various data tools (yfinance, Pinecone, sentiment analysis, etc.).

![image alt](https://github.com/kinola-IQ/stock-analyst/blob/ad987bedb2d20ec3e52e4923160e4f64bd57f1ca/Screenshot%202026-01-16%20111620.png)


**Quick Start**
- **Prerequisites:**: Python 3.10+ and pip
- **Install dependencies:**:

```bash
python -m pip install -r requirements.txt
```

- **Run locally:**:

```bash
uvicorn main:app --host 127.0.0.1 --port 8501
```

**Environment**
- **Common env vars:**: `APP_NAME`, `USER_ID`, `SESSION_ID`, `PORT` (defaults provided in `main.py`).

**API**
- **Endpoint:**: `POST /v1/analyze-stock/` — accepts JSON matching the `UserInputSchema` and returns `AgentOutputSchema`.
- **Example cURL:**:

```bash
curl -X POST http://127.0.0.1:8501/v1/analyze-stock/ \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL"}'
```

**Project Structure**
- **Root files:**: `main.py`, `requirements.txt`
- **API router:**: Interface/routes.py
- **Agents & tools:**: system/agents/finance_agent (agent, tools, tools_config)
- **Utilities:**: system/utility (logger, schema, result storage, tests)

**Notable Files**
- The FastAPI entry: [main.py](main.py)
- API routes: [Interface/routes.py](Interface/routes.py)
- Dependency list: [requirements.txt](requirements.txt)
- Agent implementation: [system/agents/finance_agent/agent.py](system/agents/finance_agent/agent.py)

**Testing & Development**
- There are unit tests under `system/utility` (`test_utils.py`, `test_result_storage.py`). Run tests with `pytest` (install `pytest` if needed).

**Notes & Next Steps**
- The project references Google ADK (`google.adk` imports) and the `google-genai` client; ensure appropriate credentials and API access are configured for agent execution.
- Pinecone and other external services are listed in `requirements.txt` — configure keys/secrets in environment variables or a secrets manager before running agent features that depend on them.

**Examples**
- **cURL:**

```bash
curl -X POST http://127.0.0.1:8501/v1/analyze-stock/ \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL"}'
```

- **Python (blocking, requests):**

```python
import requests

resp = requests.post(
    "http://127.0.0.1:8501/v1/analyze-stock/",
    json={"ticker": "AAPL"},
    timeout=60,
)
print(resp.status_code, resp.json())
```

- **Python (async, httpx):**

```python
import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://127.0.0.1:8501/v1/analyze-stock/",
            json={"ticker": "AAPL"},
            timeout=60,
        )
        print(resp.status_code, resp.json())

asyncio.run(main())
```

- **Example response (matches `AgentOutputSchema`)**:

```json
{
  "final_summary": "Apple (AAPL) shows positive momentum..."
}
```

**Environment (.env) template**
- Example variables to place in a `.env` file or set in your environment:

```
APP_NAME=stock-analyst
USER_ID=default_user
SESSION_ID=default_session
PORT=8501
GOOGLE_ADK_API_KEY=your_google_adk_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENV=your_pinecone_env_here
```

**OpenAPI & Swagger**
- When running the app, FastAPI exposes interactive docs at `/docs` (Swagger UI) and `/redoc` (ReDoc). Use these to inspect the request/response schemas and to try endpoints.

**Running tests**
- Install test dependencies and run:

```bash
pip install pytest
pytest -q
```

