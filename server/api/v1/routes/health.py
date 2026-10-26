
from fastapi import Depends

from api.router import Router
from api.v1 import base_route
from service.health_service import HealthService


router = Router(
    prefix=base_route + "/health",
    tags=["health"],
)


@router.get("")
async def status(
    health_service: HealthService = Depends(HealthService),
) -> dict[str, bool]:
    return {
        "running": True,
        "database": await health_service.database_health_check(),
    }
