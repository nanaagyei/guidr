"""Main FastAPI application."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from src.config import settings
from src.routes import auth
from src.middleware.rate_limiter import RateLimitMiddleware, RateLimitConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Guidr API",
    description="Backend API for Guidr - Graduate School Application Platform",
    version="0.0.1",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware (very lenient for development)
if settings.env == "development":
    # Almost no rate limiting in dev - allows rapid page navigation
    rate_limit_config = RateLimitConfig(
        requests_per_minute=600,      # 10 requests/second average
        requests_per_hour=10000,
        burst_limit=100,              # Allow large bursts for SPA page loads
        auth_requests_per_minute=60,
        ingestion_requests_per_minute=30,
    )
else:
    # Production limits
    rate_limit_config = RateLimitConfig(
        requests_per_minute=120,
        requests_per_hour=3000,
        burst_limit=30,
        auth_requests_per_minute=20,
        ingestion_requests_per_minute=10,
    )

app.add_middleware(
    RateLimitMiddleware,
    config=rate_limit_config,
    use_redis=settings.env == "production",
    redis_url=settings.redis_url,
    exclude_paths=["/health", "/docs", "/openapi.json", "/redoc", "/"],
)

# Include routers
app.include_router(auth.router)

from src.routes import profile, academic_records, schools, programs, documents, essays, two_factor, password_reset, recommendations, professors, data_ingestion, funding, research, pipeline, dossiers
from src.services.search_service import search_service
app.include_router(profile.router)
app.include_router(academic_records.router)
app.include_router(schools.router)
app.include_router(programs.router)
app.include_router(documents.router)
app.include_router(essays.router)
app.include_router(two_factor.router)
app.include_router(password_reset.router)
app.include_router(recommendations.router)
app.include_router(professors.router)
app.include_router(data_ingestion.router)
app.include_router(funding.router)
app.include_router(research.router)
app.include_router(pipeline.router)
app.include_router(dossiers.router)


@app.on_event("startup")
async def startup_event():
    """Initialize external services and validate configuration."""
    # Validate critical API keys
    missing = []
    if not settings.perplexity_api_key:
        missing.append("PERPLEXITY_API_KEY")
    if not settings.internal_api_key:
        missing.append("INTERNAL_API_KEY")
    if missing:
        logger.warning("Missing API keys (some features will be degraded): %s", ", ".join(missing))

    if settings.is_production and not settings.jwt_secret:
        logger.error("JWT_SECRET is not set — JWT tokens will be insecure in production")

    try:
        search_service.ensure_indexes()
    except Exception as exc:
        logger.warning("Failed to initialize Meilisearch indexes: %s", exc)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Guidr backend running",
        "env": settings.env,
        "version": "0.0.1"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}

