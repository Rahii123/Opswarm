"""
OpsSwarm — FastAPI Application Entry Point
============================================
Initialises the application, configures middleware,
mounts all routers, and defines lifecycle events.
"""

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.exceptions import OpsSwarmError
from core.logging_config import bind_request_context, clear_request_context, configure_logging

import uuid

# Configure logging before anything else
configure_logging()
logger = structlog.get_logger(__name__)


# ─── LIFESPAN ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle manager."""
    # ── Startup ──────────────────────────────────────────────
    logger.info(
        "opsswarm_starting",
        app=settings.app_name,
        version=settings.app_version,
        env=settings.app_env,
    )

    # Validate critical config in production
    if settings.is_production:
        if "insecure" in settings.secret_key:
            raise RuntimeError("Insecure SECRET_KEY detected in production. Aborting.")

    logger.info("opsswarm_ready", host=settings.api_host, port=settings.api_port)

    yield

    # ── Shutdown ──────────────────────────────────────────────
    logger.info("opsswarm_shutting_down")


# ─── APP FACTORY ──────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="OpsSwarm API",
        description=(
            "Autonomous Incident Response & Root Cause Analysis Platform. "
            "Provides endpoints for incident ingestion, status tracking, "
            "RCA retrieval, and remediation management."
        ),
        version=settings.app_version,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────
    origins = ["http://localhost:3000", "http://localhost:8080"]
    if settings.is_production:
        origins = []  # Lock down in production — configure explicitly

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request Logging Middleware ────────────────────────────
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        bind_request_context(
            correlation_id=correlation_id,
            request_id=request_id,
        )

        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else "unknown",
        )

        try:
            response = await call_next(request)
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            logger.exception("request_failed", error=str(exc))
            raise
        finally:
            clear_request_context()

    # ── Global Exception Handler ──────────────────────────────
    @app.exception_handler(OpsSwarmError)
    async def opsswarm_exception_handler(
        request: Request, exc: OpsSwarmError
    ) -> JSONResponse:
        logger.warning(
            "opsswarm_error",
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
        )
        status_map = {
            "ERR_INC_404": 404,
            "ERR_DB_404": 404,
            "ERR_VEC_404": 404,
            "ERR_INC_409": 409,
            "ERR_INC_DUP": 409,
            "ERR_VAL_001": 422,
            "ERR_REM_APPROVAL": 403,
            "ERR_LLM_429": 429,
        }
        status_code = status_map.get(exc.error_code or "", 500)
        return JSONResponse(
            status_code=status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    # ── Routers ───────────────────────────────────────────────
    from api.routers import health, incidents

    app.include_router(health.router, tags=["Health"])
    app.include_router(incidents.router, prefix="/api/v1", tags=["Incidents"])

    return app


app = create_app()
