"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import router
from src.config import get_settings
from src.database.session import close_db, init_db
from src.observability import setup_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — setup and teardown."""
    settings = get_settings()
    setup_logging(settings.log_level)
    logger = get_logger(__name__)

    logger.info("application_starting", env=settings.app_env.value)

    # Initialize database tables (dev mode)
    if settings.is_development:
        try:
            await init_db()
            logger.info("database_initialized")
        except Exception as e:
            logger.warning("database_init_skipped", error=str(e))

    yield

    # Cleanup
    await close_db()
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    logger = get_logger(__name__)

    app = FastAPI(
        title="ContentPilot",
        description="Self-evaluating agentic content generation system",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Structured Exception Handlers ---

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Log validation errors clearly and return readable error responses."""
        error_items = []
        for err in exc.errors():
            loc_str = " -> ".join(str(item) for item in err.get("loc", []))
            msg = err.get("msg", "")
            err_type = err.get("type", "")
            error_items.append(f"{loc_str}: {msg} [{err_type}]")

        summary_msg = "; ".join(error_items)
        logger.error(
            "request_validation_failed",
            url=str(request.url),
            method=request.method,
            client=request.client.host if request.client else "unknown",
            errors=exc.errors(),
            summary=summary_msg,
        )

        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "message": summary_msg,
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Log HTTP exceptions with context."""
        logger.warning(
            "http_exception",
            url=str(request.url),
            method=request.method,
            status_code=exc.status_code,
            detail=exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "HTTP Error", "message": exc.detail, "detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Log unhandled 500 errors with full trace."""
        import traceback
        tb = traceback.format_exc()
        logger.error(
            "unhandled_server_error",
            url=str(request.url),
            method=request.method,
            error=str(exc),
            traceback=tb,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "message": str(exc)},
        )

    # API routes
    app.include_router(router, prefix="/api")
    app.include_router(router, prefix="/api/v1")

    # Serve static UI files
    try:
        app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
    except Exception:
        pass  # UI directory may not exist in all environments

    return app


app = create_app()
