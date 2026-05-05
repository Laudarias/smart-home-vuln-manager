from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models import get_db
from app.auth import (
    authenticate,
    create_access_token,
    hash_password,
    get_current_user,
    get_or_create_user,
)
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_default_password: bool


class AuthStatusResponse(BaseModel):
    is_default_password: bool


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate(db, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña incorrecta.",
        )
    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        is_default_password=bool(user.is_default_password),
    )


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.auth import verify_password
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La contraseña actual no es correcta.",
        )
    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La nueva contraseña debe tener al menos 8 caracteres.",
        )
    current_user.hashed_password = hash_password(body.new_password)
    current_user.is_default_password = False
    db.commit()
    return {"message": "Contraseña actualizada correctamente."}


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(
    current_user: User = Depends(get_current_user),
):
    return AuthStatusResponse(is_default_password=bool(current_user.is_default_password))