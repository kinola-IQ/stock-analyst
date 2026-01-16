"""module defining the FastAPI routes for stock analysis."""

import os

from fastapi import HTTPException, APIRouter, Request
from google.genai import types

# custom modules
from ..system.utility.schema import UserInputSchema, AgentOutputSchema
from ..system.utility.result_storage import ResultStorage
router = APIRouter()


@router.post("/analyze-stock/", response_model=AgentOutputSchema)
async def analyze_stock(ticker: UserInputSchema, request: Request):
    """Endpoint to analyze a stock based on its ticker symbol.

    Reads the runner and session identifiers from `request.app.state`.
    """
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
        result_store = ResultStorage()
        # Iterate through streamed agent responses
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content
        ):
            # saving results in memory
            result_store.save({event.content: event.content.parts[0].text})
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response_text = event.content.parts[0].text
                break

        return AgentOutputSchema(final_summary=final_response_text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
