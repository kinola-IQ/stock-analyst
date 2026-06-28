# Stock Analyst

Stock Analyst is a FastAPI-based stock research service that uses an agent workflow to analyze a ticker symbol and return a structured research summary. The app combines financial data retrieval, sentiment analysis, and LLM-driven reasoning to produce a concise recommendation and supporting findings.
![workflow](https://github.com/kinola-IQ/stock-analyst/blob/82bde9feba0b952787e8d7a569c58d42a68a685c/Originial%20Design%20Plan.png)
## What this project does

- Accepts a stock ticker through a REST API
- Runs a research-and-analysis workflow powered by Google ADK and LiteLLM
- Pulls financial data from yfinance
- Scores recent news headlines with VADER sentiment analysis
- Returns a structured response with the analysis text and findings

## Features

- FastAPI application with health endpoints
- API-key protected analysis endpoint
- In-memory session and runner initialization for the agent workflow
- Structured logging and request/response middleware
- Test coverage for routes, utilities, ticker tools, and storage

## Requirements

- Python 3.10+
- pip
- A valid API key for the service
- A Google API key for the configured LLM runtime

## Quick start

1. Clone the repository

```bash
git clone <repository-url>
cd stock-analyst
```

2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Create a .env file in the project root

```env
API_KEY=your-secret-api-key
GOOGLE_API_KEY=your-google-api-key
APP_NAME=stock-analyst
USER_ID=default_user
SESSION_ID=default_session
HOST=0.0.0.0
PORT=8080
```

5. Start the app

```bash
python main.py
```

Or with Uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

## API usage

All analysis requests require the X-API-Key header.

### Analyze a ticker

```bash
curl -X POST http://127.0.0.1:8080/v1/analyze-stock/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key" \
  -d '{"ticker":"AAPL"}'
```

Example response:

```json
{
  "result": "A detailed analysis of the requested ticker.",
  "findings": "Key findings from the research run.",
  "status": "success",
  "timestamp": "2026-06-25T12:00:00"
}
```

### Endpoints

- POST /v1/analyze-stock/ - Run stock analysis for a ticker
- GET /health - Basic service health check
- GET /v1/health_runner - Verify that the agent runner is initialized
- GET /v1/health_model - Verify that the model layer is available

## Testing

Run the test suite with:

```bash
pytest tests/ -q
```

## Project structure

```text
stock-analyst/
├── main.py
├── requirements.txt
├── Dockerfile
├── docker-entrypoint.sh
├── Interface/
│   └── routes.py
├── system/
│   ├── agents/
│   │   └── finance_agent/
│   │       ├── agent.py
│   │       ├── tools.py
│   │       └── tools_config/
│   │           └── ticker_tools.py
│   └── utility/
│       ├── logger.py
│       ├── schema.py
│       ├── result_storage.py
│       ├── utils.py
│       ├── model.py
│       └── custom_exceptions.py
├── tests/
└── notebook/
```

## Notes

- The current implementation uses an in-memory session service and result store.
- The analysis workflow can take some time to complete because it streams agent output and performs external data lookups.
- The model loader is configured around LiteLLM, so the runtime depends on the provider credentials supplied via environment variables.

## Docker

Build and run the container with:

```bash
docker build -t stock-analyst:latest .
docker run -p 8080:8080 --env-file .env stock-analyst:latest
```

## License

This repository does not currently declare a license. Add one before public distribution or reuse.

