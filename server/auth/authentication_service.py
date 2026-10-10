
from api.exceptions import UnauthorizedException
from auth.password.password_service import PasswordService
from auth.session.session import Session
from auth.session.session_service import SessionService
from users.user_service import UserService


class AuthenticationService:
    def __init__(
        self,
        user_service: UserService,
        password_service: PasswordService,
        session_service: SessionService,
    ) -> None:
        self.user_service = user_service
        self.password_service = password_service
        self.session_service = session_service

    async def authenticate(self, user_name: str, password: str) -> Session:
        user = await self.user_service.get_user_by_name(user_name)
        if not user:
            raise UnauthorizedException("Incorrect user name or password")
        
        valid = bool(user) and self.password_service.verify_password(
            user.password_hash if user else "", password
        )
        if not valid:
            raise UnauthorizedException("Incorrect user name or password")

        if self.password_service.needs_rehash(user.password_hash):
            await self.user_service.update_password_hash(
                user, self.password_service.hash_password(password)
            )
        return await self.session_service.create_session(user)
