# Stock Analyst

Stock Analyst is a FastAPI-based stock research service that uses Google ADK and LiteLLM to analyze a ticker symbol and return a structured research summary. The app combines yfinance market data, VADER sentiment scoring, and an agent-driven workflow to deliver a concise analysis with a buy/sell/hold recommendation.

![system workflow diagram](https://github.com/kinola-IQ/stock-analyst/blob/d49f1bd61ee9b940cc9f447150f37e8311757d7b/docs/sytem%20workflow%20diagram.png)

## Current version overview

- Single-ticker research service via `POST /v1/analyze-stock/`
- Root `ResearchCoordinator` LLM agent orchestrates analysis
- `analyse_ticker` tool fetches yfinance data, extracts financial metrics, scores news sentiment, generates a Python analysis script, and computes a verdict
- `research_agent` sub-agent is available for web-based research and findings storage
- `coding_agent` sub-agent is a available for performing analytics according to available skills.
- In-memory session and result storage
- API-key protected endpoint plus health checks

## Key features

- FastAPI application with startup/shutdown lifecycle
- API key validation using `X-API-Key`
- Health endpoints for service & model readiness
- Rotating file logging (`app.log` with backups)
- In-memory result storage with basic LRU eviction
- Test coverage for routes, utilities, ticker tools, and storage
- Docker multi-stage image for container runtime

## Requirements

- Python 3.10+
- `pip`
- `requirements.txt`
- `API_KEY` environment variable for request authentication
- `GOOGLE_API_KEY` environment variable for Google ADK / LiteLLM

## Dependencies

- fastapi
- uvicorn
- yfinance
- nest_asyncio
- vaderSentiment
- protobuf==5.29.6
- google-adk
- litellm
- pytest
- pytest-mock
- pytest-asyncio
- pytest-benchmark

## Quick start

1. Clone the repository:

```bash
git clone <repository-url>
cd stock-analyst
```

2. Create and activate a virtual environment:

On macOS/Linux:

```bash
python -m venv venv
source venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root:

```env
API_KEY=your-secret-api-key
GOOGLE_API_KEY=your-google-api-key
APP_NAME=stock-analyst
USER_ID=default_user
SESSION_ID=default_session
HOST=0.0.0.0
PORT=8080
```

5. Start the application:

```bash
python main.py
```

Or start with Uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

> Note: the Docker image exposes port `8501` internally, while local development uses the `PORT` environment variable (default `8080`).

## API usage

All analysis requests require the `X-API-Key` header.

### Analyze a ticker

```bash
curl -X POST http://127.0.0.1:8080/v1/analyze-stock/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key" \
  -d '{"ticker":"AAPL"}'
```

Request body schema:

```json
{
  "ticker": "AAPL"
}
```

Example response schema:

```json
{
  "result": "<analysis text>",
  "findings": "<research findings>",
  "status": "success",
  "timestamp": "2026-06-25T12:00:00"
}
```

### Health endpoints

- `GET /health` - basic service health
- `GET /v1/health_runner` - runner initialization status
- `GET /v1/health_model` - model readiness status

## Project structure

```text
stock-analyst/
├── main.py
├── requirements.txt
├── Dockerfile
├── Interface/
│   └── routes.py
├── system/
│   ├── agents/
│   │   ├── finance_agent/
│   │   │   ├── agent.py
│   │   │   ├── tools.py
│   │   │   ├── sub_agents.py
│   │   │   ├── __init__.py
│   │   │   ├── skills/
│   │   │   │   ├── financial_analysis.md
│   │   │   │   ├── standard guide.md
│   │   │   │   └── visualizations.md
│   │   │   └── tools_config/
│   │   │       └── ticker_tools.py
│   └── utility/
│       ├── custom_exceptions.py
│       ├── logger.py
│       ├── model.py
│       ├── result_storage.py
│       ├── schema.py
│       └── utils.py
├── tests/
└── docs/
```

## Notes and limitations

- The service uses an in-memory session service and result storage.
- `API_KEY` is required for authenticated requests.
- `GOOGLE_API_KEY` must be present at startup or the app fails to initialize.
- Ticker input is validated as alphabetic only and limited to 6 characters.
- Agent output is streamed, so analysis may take several seconds.
- Docker defaults to `8501` inside the container.
- `docs/PROJECT_ANALYSIS.md` contains a more detailed design and status assessment.

## Testing

Run the test suite with:

```bash
pytest tests/ -q
```

## Docker

Build and run the container:

```bash
docker build -t stock-analyst:latest .
docker run -p 8501:8501 --env-file .env stock-analyst:latest
```

## License

This repository does not currently declare a license. Add one before public distribution or reuse.

