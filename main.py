"""main entry point for the FastAPI application."""

import os
import uvicorn
from fastapi import FastAPI
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService


# FASTAPI logging utility
from .system.utility.logger import register_http_logging
from .system.agents.finance_agent.agent import root_agent


# Configuration (read from environment with sensible defaults)
APP_NAME = os.getenv("APP_NAME", "stock-analyst")
USER_ID = os.getenv("USER_ID", "default_user")
SESSION_ID = os.getenv("SESSION_ID", "default_session")


def create_app() -> FastAPI:
    """Create and configure the FastAPI app and attach runner to app.state."""
    app = FastAPI()
    register_http_logging(app)

    # session service and runner will be created on startup
    app.state._session_service = InMemorySessionService()
    app.state._root_agent_factory = root_agent
    app.state.user_id = USER_ID
    app.state.session_id = SESSION_ID

    # include routes (router will read runner from app.state at request time)
    from .Interface.routes import router
    app.include_router(router, prefix="/v1")

    @app.on_event("startup")
    async def startup_event():
        # create a session and runner on startup
        await app.state._session_service.create_session(
            app_name=APP_NAME,
            user_id=app.state.user_id,
            session_id=app.state.session_id,
        )
        # instantiate the runner with an agent instance
        agent_instance = app.state._root_agent_factory()
        app.state.runner = Runner(
            agent=agent_instance,
            app_name=APP_NAME,
            session_service=app.state._session_service,
        )

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", 8501)))
