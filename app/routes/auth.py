"""Routes are thin: parse input (via schemas), call a service, shape output."""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.config import Settings
from app.dependencies import get_current_user, get_db, get_settings, get_token
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserOut
from app.services import auth_service

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user = auth_service.authenticate(db, body.username, body.password)
    token = auth_service.start_session(db, user, settings.session_expire_minutes)
    return TokenResponse(access_token=token)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(token: str = Depends(get_token), db: Session = Depends(get_db)):
    auth_service.end_session(db, token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return auth_service.list_users(db)


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),  # only logged-in users can add users
):
    return auth_service.create_user(db, body.username, body.password)
