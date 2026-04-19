"""Main entry point for the FastAPI application."""

import os
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.exceptions import RequestValidationError
import uvicorn
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from system.utility.logger import register_http_logging, logger
from system.agents.finance_agent.agent import root_agent
from system.utility.model import load_model
from Interface.routes import router
# prepare environment
load_dotenv()

# Configuration
APP_NAME = os.getenv("APP_NAME")
USER_ID = os.getenv("USER_ID")
SESSION_ID = os.getenv("SESSION_ID")
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown."""
    # Startup
    try:
        # making model name available on startup
        await load_model()
        logger.info('google genai client available for use')

        session_service = InMemorySessionService()
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )
        agent_instance = root_agent()
        runner = Runner(
            agent=agent_instance,
            app_name=APP_NAME,
            session_service=session_service,
        )

        app.state.session_service = session_service
        app.state.runner = runner
        app.state.user_id = USER_ID or "default_user"
        app.state.session_id = SESSION_ID or "default_session"
        logger.info("Application startup completed successfully")
    except Exception as err:
        logger.error(f"Failed to initialize application: {err}", exc_info=True)
        raise

    yield

    logger.info("Application shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""
    app = FastAPI(title=APP_NAME, lifespan=lifespan)
    register_http_logging(app)

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "ok",
            "message": "Fastapi app created and configured"}

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        """Handle validation errors with helpful message."""
        msg = f"Input validation error: see documentation at http://{HOST}:{PORT}/docs"
        return PlainTextResponse(msg, status_code=422)

    # Include API routes
    app.include_router(router, prefix="/v1")

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
