"""Warranty template lookups + issued cards list for desk settings."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
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
from app.setup_access import require_setup_unlock

router = APIRouter(tags=["settings-warranty"])

UnlockDep = Annotated[None, Depends(require_setup_unlock)]

Kind = Literal["card-types", "products", "terms", "benefits"]

KIND_MODELS: dict[str, type] = {
    "card-types": CardType,
    "products": ProductMembershipType,
    "terms": TermsCondition,
    "benefits": Benefit,
}


class WarrantyTemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    note: str | None = None
    detail: str | None = None


class WarrantyTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    note: str | None = None
    detail: str | None = None


def _serialize_template(kind: str, row: Any) -> dict[str, Any]:
    if kind == "card-types":
        return {"id": row.id, "name": row.type_name, "note": row.note or ""}
    if kind == "products":
        return {"id": row.id, "name": row.name, "note": row.note or ""}
    if kind == "terms":
        return {
            "id": row.id,
            "name": row.name,
            "note": row.note or "",
            "detail": row.detailed_condition or "",
        }
    return {
        "id": row.id,
        "name": row.name,
        "note": row.note or "",
        "detail": row.detailed_benefit or "",
    }


def _resolve_kind(kind: str) -> type:
    model = KIND_MODELS.get(kind)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid kind; use card-types|products|terms|benefits",
        )
    return model


def _get_row(db: Session, model: type, clinic_id: int, row_id: int) -> Any:
    row = db.get(model, row_id)
    if not row or getattr(row, "clinic_id", None) != clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return row


def _is_referenced(db: Session, kind: str, row_id: int, clinic_id: int) -> bool:
    q = db.query(CardIssued.id).filter(CardIssued.clinic_id == clinic_id)
    if kind == "card-types":
        q = q.filter(CardIssued.card_type_id == row_id)
    elif kind == "products":
        q = q.filter(CardIssued.product_id == row_id)
    elif kind == "terms":
        q = q.filter(CardIssued.terms_conditions_id == row_id)
    elif kind == "benefits":
        q = q.filter(CardIssued.benefit_id == row_id)
    else:
        return False
    return q.first() is not None


@router.get("/settings/warranty-templates", response_model=OkResponse)
def list_warranty_templates(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    clinic_id = user.clinic_id
    card_types = (
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
        data={
            "templates": {
                "card-types": [_serialize_template("card-types", r) for r in card_types],
                "products": [_serialize_template("products", r) for r in products],
                "terms": [_serialize_template("terms", r) for r in terms],
                "benefits": [_serialize_template("benefits", r) for r in benefits],
            }
        }
    )


@router.post("/settings/warranty-templates/{kind}", response_model=OkResponse, status_code=201)
def create_warranty_template(
    kind: Kind,
    body: WarrantyTemplateIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],

    _: UnlockDep,
) -> OkResponse:
    _resolve_kind(kind)
    name = body.name.strip()
    note = (body.note or "").strip() or None
    detail = (body.detail or "").strip() or None

    if kind == "card-types":
        row = CardType(clinic_id=user.clinic_id, type_name=name, note=note, user_id=user.user_id)
    elif kind == "products":
        row = ProductMembershipType(clinic_id=user.clinic_id, name=name, note=note, user_id=user.user_id)
    elif kind == "terms":
        row = TermsCondition(
            clinic_id=user.clinic_id,
            name=name,
            note=note,
            detailed_condition=detail,
            user_id=user.user_id,
        )
    else:
        row = Benefit(
            clinic_id=user.clinic_id,
            name=name,
            note=note,
            detailed_benefit=detail,
            user_id=user.user_id,
        )

    db.add(row)
    db.commit()
    db.refresh(row)
    return OkResponse(data=_serialize_template(kind, row))


@router.patch("/settings/warranty-templates/{kind}/{template_id}", response_model=OkResponse)
def update_warranty_template(
    kind: Kind,
    template_id: int,
    body: WarrantyTemplateUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],

    _: UnlockDep,
) -> OkResponse:
    model = _resolve_kind(kind)
    row = _get_row(db, model, user.clinic_id, template_id)
    data = body.model_dump(exclude_unset=True)

    if "name" in data and data["name"] is not None:
        name = data["name"].strip()
        if kind == "card-types":
            row.type_name = name
        else:
            row.name = name
    if "note" in data:
        row.note = (data["note"] or "").strip() or None
    if "detail" in data:
        detail = (data["detail"] or "").strip() or None
        if kind == "terms":
            row.detailed_condition = detail
        elif kind == "benefits":
            row.detailed_benefit = detail

    db.commit()
    db.refresh(row)
    return OkResponse(data=_serialize_template(kind, row))


@router.delete("/settings/warranty-templates/{kind}/{template_id}", response_model=OkResponse)
def delete_warranty_template(
    kind: Kind,
    template_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],

    _: UnlockDep,
) -> OkResponse:
    model = _resolve_kind(kind)
    row = _get_row(db, model, user.clinic_id, template_id)
    if _is_referenced(db, kind, template_id, user.clinic_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Template is referenced by issued warranty cards",
        )
    db.delete(row)
    db.commit()
    return OkResponse(data={"id": template_id, "deleted": True})


@router.get("/settings/issued-warranty-cards", response_model=OkResponse)
def list_issued_warranty_cards(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str | None, Query()] = None,
) -> OkResponse:
    clinic_id = user.clinic_id
    query = (
        db.query(CardIssued, Client, CardType, ProductMembershipType)
        .join(Client, Client.client_id == CardIssued.client_id)
        .outerjoin(CardType, CardType.id == CardIssued.card_type_id)
        .outerjoin(ProductMembershipType, ProductMembershipType.id == CardIssued.product_id)
        .filter(CardIssued.clinic_id == clinic_id, CardIssued.visible.is_(True))
    )
    term = (q or "").strip()
    if term:
        like = f"%{term}%"
        query = query.filter(
            or_(
                Client.name.ilike(like),
                CardIssued.unique_code.ilike(like),
                CardType.type_name.ilike(like),
                ProductMembershipType.name.ilike(like),
            )
        )
    rows = query.order_by(CardIssued.date_of_purchase.desc(), CardIssued.id.desc()).all()
    cards = [
        {
            "id": card.id,
            "card_id": card.id,
            "client_id": card.client_id,
            "client_name": client.name if client else "",
            "product": product.name if product else "",
            "product_name": product.name if product else "",
            "type": card_type.type_name if card_type else "",
            "type_name": card_type.type_name if card_type else "",
            "unique_code": card.unique_code,
            "date_of_purchase": card.date_of_purchase.isoformat(),
            "benefit_start_date": card.benefit_start_date.isoformat(),
            "benefit_end_date": card.benefit_end_date.isoformat(),
            "number_of_units": card.number_of_units,
            "warranty_period": card.warranty_period,
        }
        for card, client, card_type, product in rows
    ]
    return OkResponse(data={"cards": cards})
