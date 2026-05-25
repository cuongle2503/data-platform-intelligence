from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from services.shared.config import settings
from services.shared.database import DatabasePool
from services.shared.logging import configure_logging, get_logger

from services.api.routers import indicators, search, chat
from prometheus_fastapi_instrumentator import Instrumentator

configure_logging()
logger = get_logger(__name__)

from services.ai.pipeline.orchestrator import rag_pipeline

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    logger.info("Starting up FastAPI application", environment=settings.environment)

    # Initialize DB connection pool
    try:
        await DatabasePool.connect()
    except Exception as e:
        logger.critical("Failed to connect to database. Failing fast.", error=str(e))
        raise RuntimeError(f"Database connection failed: {e}")

    yield

    # Teardown
    logger.info("Shutting down FastAPI application")
    await DatabasePool.disconnect()
    await rag_pipeline.close()

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="Intelligent Data Platform API",
    description="API for Economic Data querying and Graph-Augmented RAG",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Instrumentation - Move up to avoid being blocked by routers
Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

app.include_router(indicators.router)
app.include_router(search.router)
app.include_router(chat.router)

