import jwt
from datetime import datetime, timedelta, timezone
import pytest

from app.core.config import settings

from app.core.security import(
    create_access_token,
    verify_access_token,
)


def test_create_access_token():
    token = create_access_token("123")

    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )

    assert payload["sub"] == "123"
    assert "exp" in payload
    

def test_verify_valid_access_token():
    token = create_access_token("123")

    payload = verify_access_token(token)

    assert payload["sub"] == "123"
    assert "exp" in payload


def test_verify_malformed_token():
    with pytest.raises(jwt.InvalidTokenError):
        verify_access_token("this-is-not-a-valid-jwt")


def test_verify_expired_token():
    expired_token = jwt.encode(
        {
            "sub": "123",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        verify_access_token(expired_token)


def test_verify_token_with_missing_subject():
    token = jwt.encode(
        {
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(jwt.MissingRequiredClaimError):
        verify_access_token(token)
