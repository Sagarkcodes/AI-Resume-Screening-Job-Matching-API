
import pytest
from pydantic import ValidationError

from app.schemas.auth import UserLogin, UserRegister


def test_registration_accepts_valid_data():
    user = UserRegister(
        email="candidate@example.com",
        password="SecurePass123!",
    )

    assert user.email == "candidate@example.com"


def test_registration_rejects_invalid_email():
    with pytest.raises(ValidationError):
        UserRegister(
            email="not-an-email",
            password="SecurePass123!",
        )


def test_registration_rejects_short_password():
    with pytest.raises(ValidationError):
        UserRegister(
            email="candidate@example.com",
            password="short",
        )


def test_login_accepts_valid_data():
    user = UserLogin(
        email="candidate@example.com",
        password="SecurePass123!",
    )

    assert user.password == "SecurePass123!"
