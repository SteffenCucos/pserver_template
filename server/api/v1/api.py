
from fastapi import APIRouter

from .routes import health, permissions, roles, sessions, users


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(users.router)
api_router.include_router(sessions.router)
api_router.include_router(permissions.router)
api_router.include_router(roles.router)
