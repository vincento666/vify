from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Gauge, generate_latest
from fastapi import APIRouter, Response

from app.core.config import get_settings
from app.core.responses import success

router = APIRouter(tags=["runtime"])

_registry = CollectorRegistry()
_app_info = Gauge("hify_app_info", "Hify application info", ("app",), registry=_registry)
_app_info.labels(app="hify").set(1)


@router.get("/readyz")
def readiness() -> dict[str, object]:
    settings = get_settings()
    components = {
        "app": "UP",
        "database": "CONFIGURED" if settings.database_url else "NOT_CONFIGURED",
        "redis": "CONFIGURED" if settings.redis_url else "NOT_CONFIGURED",
    }
    return success(
        {
            "status": "UP" if components["app"] == "UP" else "DOWN",
            "components": components,
        }
    )


@router.get("/metrics")
def metrics() -> Response:
    return Response(content=generate_latest(_registry), media_type=CONTENT_TYPE_LATEST)
