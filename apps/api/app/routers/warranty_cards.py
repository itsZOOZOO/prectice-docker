"""Warranty card CRUD + WhatsApp send."""

from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import (
    Benefit,
    CardIssued,
    CardType,
    Client,
    ProductMembershipType,
    TermsCondition,
    User,
)
from app.schemas import OkResponse

router = APIRouter(tags=["warranty-cards"])

IST = timezone(timedelta(hours=5, minutes=30))

PRODUCT_CODES: dict[int, str] = {
    1: "ZI",
    2: "ME",
    3: "PF",
    4: "RC",
    8: "SL",
    9: "GL",
    10: "PL",
    11: "SL",
}


class WarrantyOption(BaseModel):
    id: int
    name: str


class WarrantyCardOptions(BaseModel):
    card_types: list[WarrantyOption]
    products: list[WarrantyOption]
    terms_conditions: list[WarrantyOption]
    benefits: list[WarrantyOption]


class CreateWarrantyCardBody(BaseModel):
    card_type_id: int
    product_id: int
    terms_conditions_id: int
    benefit_id: int
    number_of_units: int = Field(ge=1)
    warranty_period: int = Field(ge=1)
    date_of_purchase: date
    benefit_start_date: date
    note: str | None = None


class UpdateWarrantyCardBody(BaseModel):
    card_type_id: int
    terms_conditions_id: int
    benefit_id: int
    number_of_units: int = Field(ge=1)
    warranty_period: int = Field(ge=1)
    date_of_purchase: date
    benefit_start_date: date
    benefit_end_date: date
    note: str | None = None


def _client(db: Session, clinic_id: int, client_id: int) -> Client:
    client = (
        db.query(Client)
        .filter(Client.client_id == client_id, Client.clinic_id == clinic_id, Client.visible.is_(True))
        .first()
    )
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


def _card(db: Session, clinic_id: int, card_id: int) -> CardIssued:
    card = (
        db.query(CardIssued)
        .filter(CardIssued.id == card_id, CardIssued.clinic_id == clinic_id, CardIssued.visible.is_(True))
        .first()
    )
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warranty card not found")
    return card


def _assert_option(db: Session, model: type, oid: int, clinic_id: int, label: str) -> Any:
    row = db.get(model, oid)
    if not row or getattr(row, "clinic_id", None) != clinic_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {label}")
    return row


def _generate_unique_code(db: Session, product_id: int, start: date) -> str:
    prefix = PRODUCT_CODES.get(product_id, "XX")
    year = start.year
    for _ in range(20):
        item = secrets.token_hex(3).upper()[:6]
        code = f"{prefix}-{year}-{item}"
        exists = db.query(CardIssued.id).filter(CardIssued.unique_code == code).first()
        if not exists:
            return code
    raise HTTPException(status_code=500, detail="Could not allocate unique card code")


def _serialize_card(db: Session, card: CardIssued) -> dict[str, Any]:
    card_type = db.get(CardType, card.card_type_id)
    product = db.get(ProductMembershipType, card.product_id)
    created = card.created_at.isoformat() if card.created_at else None
    return {
        "card_id": card.id,
        "client_id": card.client_id,
        "card_type_id": card.card_type_id,
        "product_id": card.product_id,
        "product_name": product.name if product else "",
        "type_name": card_type.type_name if card_type else "",
        "unique_code": card.unique_code,
        "date_of_purchase": card.date_of_purchase.isoformat(),
        "benefit_start_date": card.benefit_start_date.isoformat(),
        "benefit_end_date": card.benefit_end_date.isoformat(),
        "terms_conditions_id": card.terms_conditions_id,
        "benefit_id": card.benefit_id,
        "number_of_units": card.number_of_units,
        "warranty_period": card.warranty_period,
        "note": card.note or "",
        "created_at": created,
    }


@router.get("/warranty-cards/options", response_model=OkResponse)
def list_options(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    clinic_id = user.clinic_id
    types = (
        db.query(CardType)
        .filter(CardType.clinic_id == clinic_id)
        .order_by(CardType.type_name.asc())
        .all()
    )
    products = (
        db.query(ProductMembershipType)
        .filter(ProductMembershipType.clinic_id == clinic_id)
        .order_by(ProductMembershipType.name.asc())
        .all()
    )
    terms = (
        db.query(TermsCondition)
        .filter(TermsCondition.clinic_id == clinic_id)
        .order_by(TermsCondition.name.asc())
        .all()
    )
    benefits = (
        db.query(Benefit)
        .filter(Benefit.clinic_id == clinic_id)
        .order_by(Benefit.name.asc())
        .all()
    )
    return OkResponse(
        data=WarrantyCardOptions(
            card_types=[WarrantyOption(id=r.id, name=r.type_name) for r in types],
            products=[WarrantyOption(id=r.id, name=r.name) for r in products],
            terms_conditions=[WarrantyOption(id=r.id, name=r.name) for r in terms],
            benefits=[WarrantyOption(id=r.id, name=r.name) for r in benefits],
        ).model_dump()
    )


@router.get("/clients/{client_id}/warranty-cards", response_model=OkResponse)
def list_client_cards(
    client_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    _client(db, user.clinic_id, client_id)
    rows = (
        db.query(CardIssued)
        .filter(
            CardIssued.client_id == client_id,
            CardIssued.clinic_id == user.clinic_id,
            CardIssued.visible.is_(True),
        )
        .order_by(CardIssued.date_of_purchase.asc(), CardIssued.id.asc())
        .all()
    )
    return OkResponse(data=[_serialize_card(db, r) for r in rows])


@router.post("/clients/{client_id}/warranty-cards", response_model=OkResponse, status_code=201)
def create_card(
    client_id: int,
    body: CreateWarrantyCardBody,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    _client(db, user.clinic_id, client_id)
    _assert_option(db, CardType, body.card_type_id, user.clinic_id, "card type")
    _assert_option(db, ProductMembershipType, body.product_id, user.clinic_id, "product")
    _assert_option(db, TermsCondition, body.terms_conditions_id, user.clinic_id, "terms")
    _assert_option(db, Benefit, body.benefit_id, user.clinic_id, "benefit")

    end = body.benefit_start_date + timedelta(days=body.warranty_period)
    code = _generate_unique_code(db, body.product_id, body.benefit_start_date)
    card = CardIssued(
        clinic_id=user.clinic_id,
        client_id=client_id,
        card_type_id=body.card_type_id,
        product_id=body.product_id,
        date_of_purchase=body.date_of_purchase,
        benefit_start_date=body.benefit_start_date,
        benefit_end_date=end,
        terms_conditions_id=body.terms_conditions_id,
        benefit_id=body.benefit_id,
        number_of_units=body.number_of_units,
        note=(body.note or "").strip() or None,
        unique_code=code,
        warranty_period=body.warranty_period,
        visible=True,
        user_id=user.user_id,
        created_at=datetime.now(IST),
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return OkResponse(data={"card_id": card.id, "unique_code": card.unique_code})


@router.get("/warranty-cards/{card_id}", response_model=OkResponse)
def get_card(
    card_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    card = _card(db, user.clinic_id, card_id)
    return OkResponse(data={"card": _serialize_card(db, card)})


@router.patch("/warranty-cards/{card_id}", response_model=OkResponse)
def update_card(
    card_id: int,
    body: UpdateWarrantyCardBody,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    card = _card(db, user.clinic_id, card_id)
    _assert_option(db, CardType, body.card_type_id, user.clinic_id, "card type")
    _assert_option(db, TermsCondition, body.terms_conditions_id, user.clinic_id, "terms")
    _assert_option(db, Benefit, body.benefit_id, user.clinic_id, "benefit")

    card.card_type_id = body.card_type_id
    card.terms_conditions_id = body.terms_conditions_id
    card.benefit_id = body.benefit_id
    card.number_of_units = body.number_of_units
    card.warranty_period = body.warranty_period
    card.date_of_purchase = body.date_of_purchase
    card.benefit_start_date = body.benefit_start_date
    card.benefit_end_date = body.benefit_end_date
    card.note = (body.note or "").strip() or None
    db.commit()
    return OkResponse(data={"card_id": card.id})


@router.delete("/warranty-cards/{card_id}", response_model=OkResponse)
def delete_card(
    card_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    card = _card(db, user.clinic_id, card_id)
    card.visible = False
    db.commit()
    return OkResponse(data={"card_id": card.id, "deleted": True})


@router.post("/warranty-cards/{card_id}/send-whatsapp", response_model=OkResponse)
def send_card_whatsapp(
    card_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    _card(db, user.clinic_id, card_id)
    from app import whatsapp as wa

    result = wa.send_warranty_card(
        db,
        clinic_id=user.clinic_id,
        user_id=user.user_id,
        card_id=card_id,
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(result.get("message") or "WhatsApp send failed"),
        )
    return OkResponse(
        data={
            "card_id": card_id,
            "wa_message_id": (result.get("response") or {}).get("wa_message_id")
            if isinstance(result.get("response"), dict)
            else None,
            "note_id": result.get("note_id"),
            "message": result.get("message") or "WhatsApp sent",
        }
    )
