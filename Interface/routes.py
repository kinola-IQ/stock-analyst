"""FastAPI routes for stock analysis."""

from datetime import datetime
from fastapi import HTTPException, APIRouter, Request, Depends, Header
from google.genai import types

from system.utility.schema import UserInputSchema, AgentOutputSchema
from system.utility.logger import logger
from system.utility.utils import get_env
from system.utility.model import get_model

router = APIRouter()


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Verify the API key from request headers."""
    expected_key = get_env("API_KEY")
    if not expected_key:
        logger.error("API key not configured in environment")
        raise HTTPException(status_code=500, detail="Service configuration error")
    if x_api_key != expected_key:
        logger.warning(f"Invalid API key attempt")
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/analyze-stock/", response_model=AgentOutputSchema)
async def analyze_stock(
    ticker: UserInputSchema, 
    request: Request, 
    api_key: str = Depends(verify_api_key)
):
    """Analyze a stock based on ticker symbol."""
    try:
        ticker_symbol = ticker.ticker.strip().upper()

        runner = getattr(request.app.state, "runner", None)
        if runner is None:
            logger.error("Runner not initialized in app state")
            raise RuntimeError("Runner not initialized")

        user_id = getattr(request.app.state, "user_id", "default_user")
        session_id = getattr(request.app.state, "session_id", "default_session")

        logger.info(f"Starting analysis: {ticker_symbol} (user={user_id})")
    except Exceptions as exc:
        logger.error(f"Analysis failed to start: {type(exc).__name__}: {str(exc)}")
        raise HTTPException(status_code=500, detail="Stock analysis failed") from exc


    try:
        # Package query for ADK
        content = types.Content(
            role="user", parts=[types.Part(text=ticker_symbol)]
        )

        final_response_text = "No response from agent"
        
        # Stream responses from runner
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content
        ):
            # Handle final response - check multiple possible properties
            is_final = (
                (hasattr(event, 'is_final_response') and callable(event.is_final_response) and event.is_final_response()) or
                (hasattr(event, 'is_final_response') and isinstance(event.is_final_response, bool) and event.is_final_response) or
                (hasattr(event, 'final_response') and event.final_response)
            )
            
            if is_final:
                if hasattr(event, 'content') and event.content:
                    if hasattr(event.content, 'parts') and event.content.parts:
                        final_response_text = event.content.parts[0].text
                    elif hasattr(event.content, 'text'):
                        final_response_text = event.content.text
                break
            
            # Also capture regular content in case event doesn't have final_response marker
            if hasattr(event, 'content') and event.content:
                if hasattr(event.content, 'parts') and event.content.parts:
                    text = event.content.parts[0].text
                    if text:
                        final_response_text = text
                elif hasattr(event.content, 'text'):
                    if event.content.text:
                        final_response_text = event.content.text

        if final_response_text == "No response from agent":
            logger.warning(f"No response from agent for {ticker_symbol}")
        else:
            logger.info(f"Analysis completed: {ticker_symbol} ({len(final_response_text)} chars)")
        
        return AgentOutputSchema(
            final_summary=final_response_text, 
            timestamp=datetime.now().isoformat()
        )
    except Exception as exc:
            logger.error(f"Analysis failed for {ticker_symbol}: {type(exc).__name__}: {str(exc)}")
            raise HTTPException(status_code=500, detail="Stock analysis failed") from exc


@router.get("/health_runner")
async def health_check_runner(request: Request) -> dict:
    """Health check for runner service."""
    try:
        runner = getattr(request.app.state, "runner", None)
        if runner is None:
            raise HTTPException(status_code=503, detail="Service not ready")
        return {"status": "healthy", "service": "stock-analyst", "runner": True}
    except Exception as exc:
        logger.error(f"Runner health check failed: {type(exc).__name__}")
        raise HTTPException(status_code=503, detail="Service unavailable") from exc


@router.get("/health_model")
def health_check_model() -> dict:
    """Health check for model service."""
    try:
        model = get_model()
        return {"status": "healthy", "service": "stock-analyst", "model": model}
    except Exception as exc:
        logger.error(f"Model health check failed: {type(exc).__name__}")
        raise HTTPException(status_code=503, detail="Model unavailable") from exc
