
from typing import Any

from fastapi import HTTPException, status


class UnauthorizedException(HTTPException):
    def __init__(self, detail: Any) -> None:
        self.status_code = status.HTTP_401_UNAUTHORIZED
        self.detail = detail


class ForbiddenException(HTTPException):
    def __init__(self, detail: Any) -> None:
        self.status_code = status.HTTP_403_FORBIDDEN
        self.detail = detail


class NotFoundException(HTTPException):
    def __init__(self, detail: Any) -> None:
        self.status_code = status.HTTP_404_NOT_FOUND
        self.detail = detail


class UnprocessableEntityException(HTTPException):
    def __init__(self, detail: Any) -> None:
        self.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        self.detail = detail


class InternalServerErrorException(HTTPException):
    def __init__(self, detail: Any) -> None:
        self.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        self.detail = detail
