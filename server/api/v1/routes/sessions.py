
import logging

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from fastapi.responses import HTMLResponse

from api.authentication.dependencies import get_request_context
from api.decorators.authenticated import authenticated
from api.exceptions import UnauthorizedException
from api.router import Router
from api.v1 import base_route
from auth.authentication_service import AuthenticationService
from auth.dependencies import get_authentication_service, get_session_service
from auth.session.session_service import SessionService
from models.request_context import RequestContext
from users.dependencies import get_user_service
from users.user_service import UserService


logger = logging.getLogger(__name__)

router = Router(
    prefix=base_route + "/sessions",
)


@router.get("")
async def get_sessions(
    user_service: Annotated[UserService, Depends(get_user_service)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> HTMLResponse:
    sessions = await session_service.get_all()
    session_items: list[str] = []
    for session in sessions:
        user = await user_service.get_user(session.user_id)
        user_name = user.user_name if user else "User DNE"
        session_items.append("<li>" + session.id + ": " + user_name + "</li>")

    session_list = "\n".join(session_items)

    html_content = """
    <html>
        <body>
            <h1>Sessions</h1>
            <ul>
    """ + session_list + """
            </ul>
        </body>
    </html>
    """

    return HTMLResponse(content=html_content, status_code=200)


@dataclass
class LoginBody:
    user_name: str
    password: str


@router.post("/login")
async def login(
    credentials: LoginBody,
    authentication_service: Annotated[AuthenticationService, Depends(get_authentication_service)],
) -> str:
    session = await authentication_service.authenticate(credentials.user_name, credentials.password)
    return str(session.id)


@router.get("/logout")
@authenticated()
async def logout(
    request_context: Annotated[RequestContext, Depends(get_request_context)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> None:
    if not request_context.session_id:
        raise UnauthorizedException("No session found for logout")

    await session_service.end_session(request_context.session_id)
