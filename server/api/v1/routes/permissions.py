
import logging

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from api.router import Router
from api.v1 import base_route
from auth.authorization_service import AuthorizationService
from auth.dependencies import get_authorization_service


logger = logging.getLogger(__name__)

router = Router(
    prefix=base_route + "/permissions",
)

@dataclass
class PermissionRequest:
    description: str
    permission: str

@router.post("")
async def create_permission(
    permission_request: PermissionRequest,
    authorization_service: Annotated[AuthorizationService, Depends(get_authorization_service),]
) -> str:
    permission = await authorization_service.create_permission(
        description=permission_request.description,
        key=permission_request.permission,
    )
    return str(permission.id)
