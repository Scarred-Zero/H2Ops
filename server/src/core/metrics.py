import os
import secrets

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from prometheus_fastapi_instrumentator import Instrumentator

load_dotenv(".env.dev.local")  # Load environment variables from .env file
security = HTTPBasic()


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    """Validates the username and password against secure environment variables."""
    correct_username = secrets.compare_digest(
        credentials.username, os.getenv("METRICS_USER")
    )  # settings.METRICS_USER
    correct_password = secrets.compare_digest(
        credentials.password, os.getenv("METRICS_PASSWORD")
    )  # settings.METRICS_PASSWORD

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect metrics username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# SETUP PROMETHEUS METRICS
def setup_metrics(app):
    """Setup Prometheus metrics and protect the endpoint with Basic Auth."""
    instrumentator = Instrumentator()

    # 1. Attach stopwatches to all of your application endpoints
    instrumentator.instrument(app)

    # 2. Expose the /metrics route behind our username/password check
    instrumentator.expose(
        app,
        endpoint="/metrics",
        dependencies=[Depends(get_current_username)],  # <-- Protects the route
    )
