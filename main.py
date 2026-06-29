"""Main entry point for the FastAPI application."""

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
import uvicorn
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from system.utility.logger import register_http_logging, logger
from system.utility.utils import get_env
from system.agents.finance_agent import agent
from system.utility.model import load_model
from Interface.routes import router

# Prepare environment
load_dotenv()

# Validate critical environment variables
GOOGLE_GENAI_API_KEY = get_env("GOOGLE_API_KEY")
API_KEY = get_env("API_KEY")

if not GOOGLE_GENAI_API_KEY:
    logger.error("Missing GOOGLE_GENAI_API_KEY environment variable")
    raise RuntimeError("GOOGLE_GENAI_API_KEY is required")

if not API_KEY:
    logger.warning("API_KEY is not set; requests will fail header validation")

# Configuration
APP_NAME = get_env("APP_NAME", "stock-analyst")
USER_ID = get_env("USER_ID", "default_user")
SESSION_ID = get_env("SESSION_ID", "default_session")
HOST = get_env("HOST", "0.0.0.0")
PORT = get_env("PORT", "8080")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown."""
    # Startup
    try:
        await load_model()
        logger.info("Model loaded successfully")

        session_service = InMemorySessionService()
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )
        
        agent_instance = agent.root_agent()
        runner = Runner(
            agent=agent_instance,
            app_name=APP_NAME,
            session_service=session_service,
        )

        app.state.session_service = session_service
        app.state.runner = runner
        app.state.user_id = USER_ID
        app.state.session_id = SESSION_ID
        
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

    # Mount static files directory for Vercel Speed Insights
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def root():
        """Serve the landing page with Vercel Speed Insights."""
        static_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
        if os.path.exists(static_file):
            return FileResponse(static_file)
        return {"message": "Stock Analyst API", "docs": "/docs"}

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok", "message": "Service is running"}

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        """Handle validation errors with helpful message."""
        msg = f"Input validation error: see documentation at http://{HOST}:{PORT}/docs"
        return PlainTextResponse(msg, status_code=422)

    # Include API routes
    app.include_router(router, prefix="/v1")

    return app


app = create_app()


if __name__ == '__main__':
    uvicorn.run('main:app', host=HOST, port=PORT)
