# Stock Analyst

A FastAPI application that runs a finance analysis agent to analyze stock tickers using a streaming agent runner and various data tools (yfinance, Pinecone, sentiment analysis, etc.).

![Design Plan](Originial%20Design%20Plan.png)

## Features

- AI-powered stock analysis with buy/sell/hold recommendations
- Real-time financial data extraction from yfinance
- Sentiment analysis of news headlines
- Vector database integration with Pinecone
- Structured logging and monitoring
- API key authentication
- Comprehensive test suite

## Quick Start

### Prerequisites
- Python 3.10+
- pip
- Ollama (for local LLM)
- API keys for external services

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd stock-analyst
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables (see Configuration section)

5. Start Ollama and pull the model:
```bash
ollama pull qwen3:4b
```

6. Run the application:
```bash
uvicorn main:app --host 127.0.0.1 --port 8501
```

## Configuration

Create a `.env` file in the root directory with the following variables:

```env
# API Configuration
API_KEY=your-secret-api-key-here

# External Service Keys
PINECONE_API_KEY=your-pinecone-key
GOOGLE_GENAI_API_KEY=your-google-genai-key

# Application Settings
APP_NAME=stock-analyst
USER_ID=default-user
SESSION_ID=default-session
PORT=8501

# Optional: Pinecone Configuration
PINECONE_INDEX_NAME=stock-analysis
```

## API Usage

### Authentication
All API requests require an API key in the `X-API-Key` header:

```bash
curl -X POST http://127.0.0.1:8501/v1/analyze-stock/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-here" \
  -d '{"ticker":"AAPL"}'
```

### Endpoints

- `POST /v1/analyze-stock/` - Analyze a stock ticker
- `GET /v1/health` - Health check

### Request/Response Format

**Request:**
```json
{
  "ticker": "AAPL"
}
```

**Response:**
```json
{
  "final_summary": "BUY: Apple Inc. shows strong financials with positive sentiment..."
}
```

## Testing

Run the test suite:

```bash
pip install pytest pytest-mock pytest-asyncio
pytest tests/
```

## Deployment

### Docker

Build and run with Docker:

```bash
docker build -t stock-analyst .
docker run -p 8501:8501 --env-file .env stock-analyst
```

### Production Deployment

1. Set up environment variables securely
2. Use a production WSGI server like gunicorn
3. Configure reverse proxy (nginx)
4. Set up monitoring and logging
5. Enable HTTPS

Example with gunicorn:
```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8501
```

## Project Structure

```
stock-analyst/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker configuration
├── tests/                 # Test suite
│   ├── test_ticker_tools.py
│   ├── test_tools.py
│   └── test_routes.py
├── Interface/
│   └── routes.py          # API routes and endpoints
├── system/
│   ├── agents/
│   │   └── finance_agent/
│   │       ├── agent.py   # Agent implementation
│   │       ├── tools.py   # Agent tools
│   │       └── tools_config/
│   │           └── ticker_tools.py  # Financial analysis tools
│   └── utility/
│       ├── logger.py      # Logging utilities
│       ├── schema.py      # Pydantic schemas
│       ├── result_storage.py  # In-memory storage
│       ├── utils.py       # Helper functions
│       └── test_*.py      # Unit tests
└── notebook/
    └── pinecone_index.ipynb  # Jupyter notebook for experimentation
```

## Development

### Running Tests
```bash
pytest tests/ -v
```

### Code Quality
```bash
pip install black flake8
black .
flake8 .
```

### Adding New Features
1. Add business logic to appropriate module in `system/`
2. Update API routes in `Interface/routes.py`
3. Add tests in `tests/`
4. Update documentation

## Monitoring

The application includes:
- Structured logging with request/response tracking
- Health check endpoint
- Error handling with detailed logging
- Request latency monitoring

Logs are output to stdout/stderr for containerized deployments.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

[Add license information here]
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

