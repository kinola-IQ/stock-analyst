"""module defining the FastAPI routes for stock analysis."""

import os

from fastapi import HTTPException, APIRouter, Request, Depends, Header
from google.genai import types

# custom modules
from ..system.utility.schema import UserInputSchema, AgentOutputSchema
from ..system.utility.result_storage import ResultStorage
from ..system.utility.logger import logger
router = APIRouter()


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Verify the API key from request headers."""
    expected_key = os.getenv("API_KEY")
    if not expected_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    if x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/analyze-stock/", response_model=AgentOutputSchema)
async def analyze_stock(ticker: UserInputSchema, request: Request, api_key: str = Depends(verify_api_key)):
    """Endpoint to analyze a stock based on its ticker symbol.

    Reads the runner and session identifiers from `request.app.state`.
    """
    logger.info("Starting stock analysis", ticker=ticker.ticker, user_id=request.app.state.user_id)
    try:
        print(f"\n>>> ticker: {ticker}")

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

        # Package the user's query into ADK format
        content = types.Content(
            role="user", parts=[types.Part(text=ticker.ticker)]
        )

        final_response_text = "Agent did not produce a final response."
        # Iterate through streamed agent responses
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content
        ):
            # saving results in memory
            ResultStorage.save({event.content: event.content.parts[0].text})
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response_text = event.content.parts[0].text
                break

        logger.info("Stock analysis completed", ticker=ticker.ticker, verdict=final_response_text[:50])
        return AgentOutputSchema(final_summary=final_response_text)
    except Exception as exc:
        logger.error("Stock analysis failed", ticker=ticker.ticker, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "stock-analyst"}
