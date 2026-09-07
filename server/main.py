import logging
from contextlib import asynccontextmanager

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
# from src.api.v1.routers import auth, properties, favorites, users
# from src.api.v1.internal.admin import router as admin_router
from src.core.config import settings
from src.core.metrics import setup_metrics
from src.core.database import init_db

# CONFIGURE LOGGINGS
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# APPLICATION LIFESPAN
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # STARTUP
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.APP_VERSION} in {settings.ENVIRONMENT} mode"
    )

    # INITAIALISE SENTRY IF DSN IS PROVIDED
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[
                FastApiIntegration(auto_enabling_instrumentations=False),
                LoggingIntegration(level=logging.INFO),
            ],
            traces_sample_rate=0.1,
            environment=settings.ENVIRONMENT,
        )
        logger.info("Sentry initialized Successfully")
    else:
        logger.info("Sentry DSN not provided. Sentry is disabled.")

    # INITIALISE DATABASE
    await init_db()

    logger.info("Application startup complete")

    yield

    # SHUTDOWN
    logger.info("Shutting down application")


# CREATE FASTAPI APPLICATION
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API for H2Ops - Water Quality Monitoring System",
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

cors_origins = settings.BACKEND_CORS_ORIGINS or [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,  # For Https Cookie forwarding
    allow_methods=["*"],
    allow_headers=["*"],
)

# ADD TRUSTED HOST SECURITY MIDDLEWARE
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else ["localhost", "127.0.0.1"],
)


# REQUEST LOGGING MIDDLEWARE
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response


# SETUP PROMETHEUS METRICS
setup_metrics(app)
logger.info("Prometheus metrics enabled")


# INCLUDE API ROUTERS WITH API VERSION PREFIX
# app.include_router(auth.router, prefix="/api/v1")

# Internal / Admin Routers
# app.include_router(admin_router, prefix="/api/v1/internal")


# HEALTHCHECK ENDPOINT
@app.get("/healthcheck", tags=["Health"])
async def healthcheck():
    return {"status": "healthy"}


# ROOT ENDPOINT
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }
