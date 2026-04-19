"""module defining the FastAPI routes for stock analysis."""

import os
from typing import Optional
from datetime import datetime

from fastapi import HTTPException, APIRouter, Request, Depends, Header
from google.genai import types

# custom modules
from system.utility.schema import UserInputSchema, AgentOutputSchema
from system.utility.logger import logger
from system.utility.model import get_model
router = APIRouter()


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Verify the API key from request headers."""
    expected_key = os.getenv("API_KEY")
    if not expected_key:
        logger.error("API key not configured in environment")
        raise HTTPException(status_code=500, detail="Service configuration error")
    if x_api_key != expected_key:
        logger.warning("Invalid API key attempt", extra={"provided_key_length": len(x_api_key)})
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/analyze-stock/", response_model=AgentOutputSchema)
async def analyze_stock(ticker: UserInputSchema, request: Request, api_key: str = Depends(verify_api_key)):
    """Endpoint to analyze a stock based on its ticker symbol.

    Reads the runner and session identifiers from `request.app.state`.
    """
    # Validate input
    if not ticker.ticker or not ticker.ticker.strip():
        logger.warning("Empty ticker symbol provided")
        raise HTTPException(status_code=400, detail="Ticker symbol cannot be empty")
    
    ticker_symbol = ticker.ticker.strip().upper()
    
    # retrieve runner and session info from app state
    runner = getattr(request.app.state, "runner", None)
    if runner is None:
        raise RuntimeError(
            "Runner is not initialized; ensure the app startup "
            "completed successfully."
        )

    user_id = getattr(
        request.app.state, "user_id", os.getenv("USER_ID", "default_user")
    )
    session_id = getattr(
        request.app.state,
        "session_id",
        os.getenv("SESSION_ID", "default_session"),
    )
    
    logger.info("Starting stock analysis", extra={"ticker": ticker_symbol, "user_id": user_id})
    try:
        logger.debug("Analyzing ticker", extra={"ticker": ticker_symbol})

        # Package the user's query into ADK format
        content = types.Content(
            role="user", parts=[types.Part(text=ticker_symbol)]
        )

        final_response_text = "Agent did not produce a final response."
        # Iterate through streamed agent responses
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content
        ):
           # save final response when agent signals completion
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response_text = event.content.parts[0].text
                break

        logger.info("Stock analysis completed", extra={"ticker": ticker_symbol, "verdict": final_response_text[:50]})
        return AgentOutputSchema(final_summary=final_response_text, timestamp=datetime.now().isoformat())
    except Exception as exc:
        logger.error("Stock analysis failed", extra={"ticker": ticker_symbol, "error": type(exc).__name__})
        raise HTTPException(status_code=500, detail="Stock analysis failed. Please try again.") from exc


@router.get("/health_runner")
async def health_check(request: Request) -> dict:
    """Health check endpoint."""
    try:
        runner = getattr(request.app.state, "runner", None)
        if runner is None:
            logger.warning("Health check failed: runner not initialized")
            raise HTTPException(status_code=503, detail="Service not ready")

        return {
            "status": "healthy",
            "service": "stock-analyst",
            "runner_initialized": runner is not None
        }
    except Exception as exc:
        logger.error("Health check failed", extra={"error": type(exc).__name__})
        raise HTTPException(status_code=503, detail="Service health check failed") from exc


@router.get("/health_model")
def health_check_model() -> dict:
    """Health check endpoint for model."""
    try:
        model = get_model()
        return {
            "status": "healthy",
            "service": "stock-analyst",
            "model_loaded": model is not None
        }
    except Exception as exc:
        logger.error("Model health check failed", extra={"error": type(exc).__name__})
        raise HTTPException(status_code=503, detail="Model health check failed") from exc
