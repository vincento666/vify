from fastapi import APIRouter

from app.core.responses import success

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
def health() -> dict[str, object]:
    return success(
        {
            "status": "UP",
            "components": {
                "app": "UP",
            },
        }
    )
