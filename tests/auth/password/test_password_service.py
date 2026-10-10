
from unittest.mock import create_autospec

import pytest

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from server.auth.password.password_service import PasswordService


def make_hasher() -> PasswordHasher:
    return create_autospec(PasswordHasher, instance=True)


def test_hash_password_delegates_to_configured_hasher() -> None:
    hasher = make_hasher()
    hasher.hash.return_value = "hashed-password"
    service = PasswordService(hasher)

    assert service.hash_password("a secure password") == "hashed-password"

    hasher.hash.assert_called_once_with("a secure password")


def test_verify_password_returns_hasher_result() -> None:
    hasher = make_hasher()
    hasher.verify.return_value = True
    service = PasswordService(hasher)

    assert service.verify_password("stored-hash", "a secure password") is True

    hasher.verify.assert_called_once_with("stored-hash", "a secure password")


@pytest.mark.parametrize("error", [VerifyMismatchError("mismatch"), ValueError("invalid hash")])
def test_verify_password_returns_false_for_invalid_or_mismatched_hashes(error: Exception) -> None:
    hasher = make_hasher()
    hasher.verify.side_effect = error
    service = PasswordService(hasher)

    assert service.verify_password("bad-hash", "a secure password") is False


def test_needs_rehash_returns_hasher_result() -> None:
    hasher = make_hasher()
    hasher.check_needs_rehash.return_value = True
    service = PasswordService(hasher)

    assert service.needs_rehash("stored-hash") is True

    hasher.check_needs_rehash.assert_called_once_with("stored-hash")


@pytest.mark.parametrize("error", [ValueError("invalid hash"), TypeError("invalid hash type")])
def test_needs_rehash_returns_false_for_invalid_hashes(error: Exception) -> None:
    hasher = make_hasher()
    hasher.check_needs_rehash.side_effect = error
    service = PasswordService(hasher)

    assert service.needs_rehash("bad-hash") is False
