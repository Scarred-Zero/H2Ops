import logging
import asyncio

from typing import AsyncGenerator
from contextlib import asynccontextmanager

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from src.core.config import settings
from src.utils import mqtt_subscriber
from src.workers import simulator
from src.api.v1.routes import auth as auth_router
from src.api.v1.routes import ws as ws_router
from src.api.v1.routes import devices as devices_router
from src.api.v1.routes import telemetry as telemetry_router  
from src.core.metrics import setup_metrics
from src.core.database import init_db

# CONFIGURE LOGGINGS
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("h2ops.main")


# APPLICATION LIFESPAN
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    App lifespan manager:
      - starts MQTT subscriber background task
      - starts simulator worker
      - ensures graceful shutdown and cancellation
    """
    # STARTUP
    mqtt_task = asyncio.create_task(mqtt_subscriber.run_subscriber_loop())
    sim_task = asyncio.create_task(simulator.run_simulator_loop())
    logger.info(f"Starting MQTT subscriber and simulator background tasks in {settings.ENVIRONMENT}  mode")

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
    try:
        yield
    finally:
        # Cancel tasks and wait for them to finish
        for task, name in ((mqtt_task, "mqtt_subscriber"), (sim_task, "simulator")):
            if not task.done():
                logger.info("Cancelling %s", name)
                task.cancel()
        # Give tasks a short window to finish cleanup
        await asyncio.gather(mqtt_task, sim_task, return_exceptions=True)
        # SHUTDOWN
        logger.info("Background tasks shut down")


# CREATE FASTAPI APPLICATION
def create_app() -> FastAPI:
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
    app.include_router(ws_router.router, prefix="/api/v1/ws", tags=["websockets"])
    app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(devices_router.router, prefix="/api/v1/devices", tags=["devices"])
    app.include_router(telemetry_router.router, prefix="/api/v1/telemetry", tags=["telemetry"])

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

    return app



app = create_app()

