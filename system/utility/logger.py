"""module to log system events"""
import logging
import time

# instantiating logger
logger = logging.getLogger("uvicorn.error")


# keep track of responsiveness across endpoints
def register_http_logging(app):
    """Processing time logger for HTTP requests and response status."""

    @app.middleware("http")
    async def log_process_time(request, call_next):
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            elapsed = time.perf_counter() - start
            # Log exception with traceback and request context
            msg = (
                f"{request.method} {request.url.path} failed "
                f"in {elapsed:.3f}s"
            )
            logger.exception(msg)
            raise

        elapsed = time.perf_counter() - start
        status = getattr(response, "status_code", "?")
        msg = (
            f"{request.method} {request.url.path} {status} "
            f"completed in {elapsed:.3f}s"
        )
        logger.info(msg)
        return response
