
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin


def register_user(
    db: Session,
    user_data: UserRegister,
) -> User:
    existing_user = db.scalar(
        select(User).where(User.email == str(user_data.email))
    )

    if existing_user:
        raise ValueError("Email already registered")

    new_user = User(
        email=str(user_data.email),
        password_hash=hash_password(user_data.password),
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception:
        db.rollback()
        raise

    return new_user

def authenticate_user(db:Session, user_data: UserLogin) -> str:
    user = db.scalar(
        select(User).where(User.email == str(user_data.email))
    )
    
    if user is None:
        raise ValueError("Incorrect email or passwprd")
    
    if not verify_password(user_data.password, user.password_hash):
        raise ValueError("Incorrect email or password")
    
    if not user.is_active:
        raise ValueError("Account is inactive")
    
    return create_access_token(subject=str(user.id))