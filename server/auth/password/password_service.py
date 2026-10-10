
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class PasswordService:
    """Application boundary around Argon2id password operations."""

    def __init__(self, hasher: PasswordHasher | None = None) -> None:
        self.hasher = hasher or PasswordHasher()

    def hash_password(self, password: str) -> str:
        return self.hasher.hash(password)

    def verify_password(self, password_hash: str, password: str) -> bool:
        try:
            return self.hasher.verify(password_hash, password)
        except (InvalidHashError, VerificationError, VerifyMismatchError, TypeError, ValueError):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        try:
            return self.hasher.check_needs_rehash(password_hash)
        except (InvalidHashError, VerificationError, TypeError, ValueError):
            return False
