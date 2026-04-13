# Stock Analyst

A FastAPI application that leverages Google's Agent Development Kit (ADK) to run a multi-agent research workflow for comprehensive stock analysis. The system coordinates research, financial data analysis, and sentiment scoring to produce actionable buy/sell/hold recommendations.
## Features

- **Multi-agent system**: Research Coordinator agent orchestrates specialized sub-agents (ResearchAgent)
- **AI-powered analysis**: Google Gemini model with structured financial reasoning
- **Real-time financial data**: yfinance integration for stock prices, metrics, and historical data
- **Sentiment analysis**: VADER sentiment scoring on financial news headlines
- **Web research**: Google Search integration for company research
- **Structured output**: Buy/sell/hold verdicts with detailed metrics and reasoning
- **API key authentication**: Secure endpoint access with X-API-Key headers
- **Streaming responses**: Real-time event streaming from agent execution
- **Comprehensive test suite**: Unit tests for tools, routes, and utilities
- **Structured logging**: Request/response tracking and error diagnostics

## Quick Start

### Prerequisites
- Python 3.10+
- pip
- Google Gemini API key (for LLM inference)
- Google Search API credentials
- (Optional) Pinecone API key for vector storage

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

5. Run the application:
```bash
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8501
```

## Configuration

Create a `.env` file in the root directory with the following variables:

```env
# API Configuration
API_KEY=your-secret-api-key-here

# Google Services (Required)
GOOGLE_GENAI_API_KEY=your-google-gemini-api-key
GOOGLE_ADK_API_KEY=your-google-adk-api-key

# Application Settings
APP_NAME=stock-analyst
USER_ID=default-user
SESSION_ID=default-session
HOST=0.0.0.0
PORT=8501

# Optional: External Services
PINECONE_API_KEY=your-pinecone-key
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

- `POST /v1/analyze-stock/` - Analyze a stock ticker (requires X-API-Key header)
- `GET /health` - Basic health check
- `GET /v1/health_runner` - Runner service health check

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
  "final_summary": "BUY: Apple Inc. demonstrates strong financial fundamentals with positive market sentiment. Key metrics show...",
  "status": "success",
  "timestamp": "2024-04-13T10:30:45.123456"
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
docker build -t stock-analyst:latest .
docker run -p 8501:8501 --env-file .env stock-analyst:latest
```

The Docker image uses a multi-stage build (Python 3.11-slim) and runs as a non-root user for security.

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
├── main.py                 # FastAPI app with ADK runner initialization
├── requirements.txt        # Python dependencies
├── Dockerfile             # Multi-stage Docker build (Python 3.11-slim)
├── docker-entrypoint.sh   # Container startup script
├── tests/                 # Unit and integration tests
│   ├── test_ticker_tools.py    # yfinance & financial metrics tests
│   ├── test_tools.py           # Agent tool tests
│   ├── test_routes.py          # API endpoint tests
│   ├── test_utils.py           # Utility function tests
│   └── test_result_storage.py  # Storage layer tests
├── Interface/
│   └── routes.py          # FastAPI routes with API key verification
├── system/
│   ├── agents/
│   │   └── finance_agent/
│   │       ├── agent.py              # Root ResearchCoordinator agent
│   │       ├── tools.py              # Agent tool definitions (research, analysis)
│   │       └── tools_config/
│   │           └── ticker_tools.py   # Financial pipeline (fetch → analyze → decide)
│   └── utility/
│       ├── logger.py           # Structured logging configuration
│       ├── schema.py           # Pydantic request/response schemas
│       ├── result_storage.py   # In-memory session storage
│       ├── utils.py            # Retry logic and helpers
│       ├── model.py            # Gemini model loader
│       └── custom_exceptions.py # Custom exception types
└── notebook/
    ├── initial system audit report.ipynb  # System diagnostics
    └── pinecone_index.ipynb              # Vector DB experimentation
```

## Development

### Running Tests
```bash
pytest tests/ -v              # Run all tests with verbose output
pytest tests/ -k ticker_tools # Run specific test module
pytest tests/ --cov          # Generate coverage report
```

### Code Quality
```bash
pip install black flake8
black .           # Format code
flake8 .          # Lint code
```

### Adding New Features
1. **New ticker analysis tools**: Add functions to `system/agents/finance_agent/tools_config/ticker_tools.py`
2. **New agent tools**: Add tool definitions to `system/agents/finance_agent/tools.py` and wrap with `AgentTool` in `agent.py`
3. **New API endpoints**: Extend `Interface/routes.py` with FastAPI route decorators
4. **Tests**: Add corresponding test files in `tests/` directory following existing patterns
5. **Documentation**: Update this README and add docstrings to new functions

### Understanding the Agent Workflow
The root agent (`ResearchCoordinator`) orchestrates the following workflow:
1. **Research Phase**: Uses ResearchAgent with Google Search to find company information and news
2. **Analysis Phase**: Uses `analyse_ticker()` to compute financial metrics and sentiment scores
3. **Decision Phase**: Generates buy/sell/hold recommendation based on metrics and sentiment
4. **Logging**: Records key decisions and milestones for traceability

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

## Important Notes

### External Service Dependencies
- **Google Gemini API**: Required for LLM inference. Obtain API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Google Agent Development Kit (ADK)**: Provides the agent runtime and streaming capabilities. Requires valid Google Cloud credentials.
- **yfinance**: Free financial data source; no API key required
- **VADER Sentiment**: NLTK-based sentiment analysis; downloads lexicon on first use
- **Pinecone** (optional): For vector-based semantic search; configure only if needed

### Performance & Constraints
- Stock analysis typically completes in 10-30 seconds depending on agent reasoning depth
- Streaming responses allow real-time event monitoring during analysis
- API rate limits apply to Google services; configure retry logic as needed

### Security
- API key required in `X-API-Key` header for all `/v1/*` endpoints
- Docker container runs as non-root user for security
- Keep `.env` file secure; never commit to version control

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
```env
# Core Configuration
APP_NAME=stock-analyst
USER_ID=default_user
SESSION_ID=default_session
HOST=0.0.0.0
PORT=8501
API_KEY=your-secret-api-key-here

# Google Services (Required)
GOOGLE_GENAI_API_KEY=your-google-gemini-api-key
GOOGLE_ADK_API_KEY=your-google-adk-api-key

# Optional Services
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=stock-analysis
```

**OpenAPI & Swagger**
- When running the app, FastAPI exposes interactive docs at `/docs` (Swagger UI) and `/redoc` (ReDoc)
- Try the `/v1/analyze-stock/` endpoint directly in the UI
- Note: Headers tab required for X-API-Key authentication

**Running tests**
```bash
pip install pytest pytest-mock pytest-asyncio
pytest tests/ -v
```

**Troubleshooting**
- If you see "Runner is not initialized": Ensure app startup completed without errors. Check logs for credential issues.
- If sentiment analysis fails: VADER will auto-download NLTK data on first use (requires internet connection)
- If Google Search fails: Verify GOOGLE_GENAI_API_KEY is valid and has Search API enabled
- If agent hangs: Check OpenAI/Google rate limits; implement backoff in utils.py

