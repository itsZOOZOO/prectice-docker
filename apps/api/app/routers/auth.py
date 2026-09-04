from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, verify_password
from app.db import get_db
from app.models import Clinic, User
from app.schemas import LoginData, LoginRequest, OkResponse, TokenUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=OkResponse)
def login(body: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> OkResponse:
    username = body.username.strip()
    user = (
        db.query(User)
        .filter(func.lower(User.username) == username.lower(), User.active.is_(True))
        .first()
    )
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    clinic = db.get(Clinic, user.clinic_id)
    if not clinic or not clinic.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clinic inactive")

    token = create_access_token(user_id=user.user_id, clinic_id=user.clinic_id, role=user.role)
    data = LoginData(
        access_token=token,
        user=TokenUser.model_validate(user),
        clinic_name=clinic.clinic_name,
    )
    return OkResponse(data=data.model_dump())


@router.get("/me", response_model=OkResponse)
def me(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    clinic = db.get(Clinic, user.clinic_id)
    return OkResponse(
        data={
            "user": TokenUser.model_validate(user).model_dump(),
            "clinic_name": clinic.clinic_name if clinic else None,
        }
    )


@router.get("/users", response_model=OkResponse)
def list_clinic_users(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    rows = (
        db.query(User)
        .filter(User.clinic_id == user.clinic_id, User.active.is_(True))
        .order_by(User.full_name)
        .all()
    )
    return OkResponse(data=[TokenUser.model_validate(r).model_dump() for r in rows])
