import secrets

from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.core.security import hash_password, verify_password

def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()

def get_or_create_oauth_user(db: Session, email: str, full_name: str) -> User:
    """Return the local user for a Google account, creating one if needed.

    OAuth-created users get an unguessable random password (they sign in
    via Google, not with a password) and default to the security analyst
    role.
    """
    user = get_user_by_email(db, email)
    if user:
        return user
    random_password = secrets.token_urlsafe(16)

    # Bootstrap: the very first account created (via Google OAuth) becomes
    # the administrator, since no demo credentials exist anymore.
    role = (
        UserRole.ADMINISTRATOR
        if db.query(User).count() == 0
        else UserRole.SECURITY_ANALYST
    )
    user = User(
        full_name=full_name or email.split("@")[0],
        email=email,
        hashed_password=hash_password(random_password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_user(db: Session, user_in: UserCreate) -> User:
    user = User(
        full_name=user_in.full_name,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        role=user_in.role,
        employee_id=user_in.employee_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
