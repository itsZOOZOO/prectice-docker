from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, verify_password
from app.db import get_db
from app.models import Clinic, User
from app.schemas import LoginData, LoginRequest, OkResponse, SsoExchangeRequest, TokenUser
from app.sso import exchange_sso_code, sso_configured

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_login(db: Session, user: User, *, remember: bool) -> LoginData:
    clinic = db.get(Clinic, user.clinic_id)
    if not clinic or not clinic.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clinic inactive")

    user.last_login = datetime.now(timezone.utc)
    db.add(user)
    db.commit()

    token = create_access_token(
        user_id=user.user_id,
        clinic_id=user.clinic_id,
        role=user.role,
        remember=remember,
    )
    return LoginData(
        access_token=token,
        user=TokenUser.model_validate(user),
        clinic_name=clinic.clinic_name,
    )


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

    data = _issue_login(db, user, remember=body.remember)
    return OkResponse(data=data.model_dump())


@router.post("/sso/exchange", response_model=OkResponse)
def sso_exchange(body: SsoExchangeRequest, db: Annotated[Session, Depends(get_db)]) -> OkResponse:
    if not sso_configured():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SSO is not configured")

    code = body.code.strip()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Authorization code is required")

    try:
        exchange = exchange_sso_code(code)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    email = str(exchange.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="SSO account has no email")

    user = (
        db.query(User)
        .filter(func.lower(User.email) == email, User.active.is_(True))
        .order_by(User.user_id)
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No clinic account for this Google email",
        )

    data = _issue_login(db, user, remember=body.remember)
    payload = data.model_dump()
    payload["sso_email"] = email
    final_redirect = str(exchange.get("final_redirect") or "").strip()
    if final_redirect:
        payload["final_redirect"] = final_redirect
    return OkResponse(data=payload)


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
