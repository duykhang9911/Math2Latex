from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    ACCESS_COOKIE_NAME,
    ACCESS_TOKEN_TTL_MINUTES,
    AUTH_COOKIE_SECURE,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models import User
from app.schemas.auth import AuthCredentials, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_auth_cookie(response: Response, user: User) -> None:
    token = create_access_token(user.id)
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=token,
        max_age=ACCESS_TOKEN_TTL_MINUTES * 60,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/api",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    credentials: AuthCredentials,
    response: Response,
    db: Session = Depends(get_db),
):
    username = credentials.username.strip().lower()
    if db.query(User.id).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="Tên đăng nhập đã được sử dụng")

    user = User(username=username, password_hash=hash_password(credentials.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Tên đăng nhập đã được sử dụng") from None

    db.refresh(user)
    _set_auth_cookie(response, user)
    return user


@router.post("/login", response_model=UserResponse)
def login(
    credentials: AuthCredentials,
    response: Response,
    db: Session = Depends(get_db),
):
    username = credentials.username.strip().lower()
    user = db.query(User).filter(User.username == username).first()
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng")

    _set_auth_cookie(response, user)
    return user


@router.get("/me", response_model=UserResponse)
def get_session_user(user: User = Depends(get_current_user)):
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(
        key=ACCESS_COOKIE_NAME,
        path="/api",
        secure=AUTH_COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )