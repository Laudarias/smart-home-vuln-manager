from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import (
    verify_password,
    hash_password,
    create_token,
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
    user = get_or_create_user(db)
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    return {
        "access_token": create_token({"sub": user.id}),
        "token_type": "bearer",
        "is_default_password": user.is_default_password,
    }


@router.post("/change-password")
def change_password(body: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")
    current_user.hashed_password = hash_password(body.new_password)
    current_user.is_default_password = False
    db.commit()
    return {"message": "Contraseña actualizada"}

@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "is_default_password": current_user.is_default_password}