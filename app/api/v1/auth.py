from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.schemas.user import UserCreate, UserOut, UserUpdate, Token
from app.services.auth_service import (
    create_user,
    get_user_by_email,
    authenticate_user,
    get_or_create_oauth_user,
)
from app.core.security import create_access_token, hash_password

from app.core.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.services.google_oauth import (
    build_auth_url,
    exchange_code,
    is_configured,
    verify_state,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, user_in.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return create_user(db, user_in)

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token(data={"sub": user.email, "role": user.role.value})
    return Token(access_token=token)

@router.get("/google/login")
def google_login():
    """Return the Google consent URL for the frontend to redirect to."""
    if not is_configured():
        raise HTTPException(
            status_code=400,
            detail="Google OAuth is not configured (set GOOGLE_CLIENT_ID, "
            "GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI in .env)",
        )
    return {"auth_url": build_auth_url()}

@router.get("/google/callback")
def google_callback(
    code: str = Query(...),
    state: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """
    Handle Google's redirect: exchange the code, provision the user, and
    send the browser back to the frontend with a JWT in the URL fragment.
    """
    frontend = settings.frontend_url.rstrip("/")

    if not verify_state(state):
        return RedirectResponse(
            f"{frontend}/oauth/callback#error=invalid_state", status_code=302
        )

    try:
        profile = exchange_code(code)
    except Exception:
        return RedirectResponse(
            f"{frontend}/oauth/callback#error=token_exchange_failed",
            status_code=302,
        )

    email = (profile.get("email") or "").strip().lower()
    if not email:
        return RedirectResponse(
            f"{frontend}/oauth/callback#error=no_email", status_code=302
        )

    name = (profile.get("name") or "").strip()
    user = get_or_create_oauth_user(db, email, name)
    token = create_access_token(
        data={"sub": user.email, "role": user.role.value}
    )
    return RedirectResponse(
        f"{frontend}/oauth/callback#access_token={token}", status_code=302
    )

@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Return profile details for the currently logged-in user."""
    return current_user

@router.put("/me", response_model=UserOut)
def update_current_user_profile(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update profile details (name, email, password) for the logged-in user."""
    if user_in.full_name is not None:
        current_user.full_name = user_in.full_name
    if user_in.email is not None and user_in.email != current_user.email:
        if get_user_by_email(db, user_in.email):
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = user_in.email
    if user_in.password:
        current_user.hashed_password = hash_password(user_in.password)


    db.commit()
    db.refresh(current_user)
    return current_user
