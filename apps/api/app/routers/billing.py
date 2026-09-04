from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Bill, Client, MoneyReceipt, User
from app.schemas import (
    BillCreate,
    BillOut,
    OkResponse,
    ReceiptCreate,
    ReceiptOut,
)

router = APIRouter(tags=["billing"])

PAYMENT_MODES = {"Cash", "Online", "Cheque", "Other"}


def _client(db: Session, clinic_id: int, client_id: int) -> Client:
    row = (
        db.query(Client)
        .filter(Client.client_id == client_id, Client.clinic_id == clinic_id, Client.visible.is_(True))
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return row


def _bill_out(bill: Bill) -> dict:
    data = BillOut.model_validate(bill).model_dump()
    data["amount_due"] = float(bill.amount_due)
    return data


def _receipt_out(receipt: MoneyReceipt) -> dict:
    data = ReceiptOut.model_validate(receipt).model_dump()
    data["amount"] = float(receipt.amount)
    return data


@router.get("/clients/{client_id}/bills", response_model=OkResponse)
def list_bills(
    client_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    _client(db, user.clinic_id, client_id)
    rows = (
        db.query(Bill)
        .filter(Bill.clinic_id == user.clinic_id, Bill.client_id == client_id, Bill.visible.is_(True))
        .order_by(Bill.issued_at.desc())
        .all()
    )
    return OkResponse(data=[_bill_out(r) for r in rows])


@router.post("/clients/{client_id}/bills", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_bill(
    client_id: int,
    body: BillCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    _client(db, user.clinic_id, client_id)
    bill = Bill(
        clinic_id=user.clinic_id,
        client_id=client_id,
        amount_due=Decimal(str(body.amount_due)),
        status="open",
        description=body.description,
        user_id=user.user_id,
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return OkResponse(data=_bill_out(bill))


@router.get("/clients/{client_id}/receipts", response_model=OkResponse)
def list_client_receipts(
    client_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    _client(db, user.clinic_id, client_id)
    rows = (
        db.query(MoneyReceipt)
        .filter(
            MoneyReceipt.clinic_id == user.clinic_id,
            MoneyReceipt.client_id == client_id,
            MoneyReceipt.visible.is_(True),
        )
        .order_by(MoneyReceipt.received_at.desc())
        .all()
    )
    return OkResponse(data=[_receipt_out(r) for r in rows])


@router.post("/clients/{client_id}/receipts", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_receipt(
    client_id: int,
    body: ReceiptCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    _client(db, user.clinic_id, client_id)
    if body.payment_mode not in PAYMENT_MODES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment mode")

    bill = None
    if body.bill_id:
        bill = (
            db.query(Bill)
            .filter(
                Bill.bill_id == body.bill_id,
                Bill.clinic_id == user.clinic_id,
                Bill.client_id == client_id,
                Bill.visible.is_(True),
            )
            .first()
        )
        if not bill:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    receipt = MoneyReceipt(
        clinic_id=user.clinic_id,
        client_id=client_id,
        bill_id=body.bill_id,
        amount=Decimal(str(body.amount)),
        payment_mode=body.payment_mode,
        description=body.description,
        user_id=user.user_id,
    )
    db.add(receipt)
    if bill:
        bill.status = "paid"
    db.commit()
    db.refresh(receipt)
    return OkResponse(data=_receipt_out(receipt))


@router.get("/desk/receipts/today", response_model=OkResponse)
def receipts_today(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    on: date | None = Query(default=None),
) -> OkResponse:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    day = on or datetime.now(ZoneInfo("Asia/Kolkata")).date()
    start = datetime.combine(day, datetime.min.time(), tzinfo=ZoneInfo("Asia/Kolkata"))
    end = datetime.combine(day, datetime.max.time(), tzinfo=ZoneInfo("Asia/Kolkata"))

    rows = (
        db.query(MoneyReceipt)
        .filter(
            MoneyReceipt.clinic_id == user.clinic_id,
            MoneyReceipt.visible.is_(True),
            MoneyReceipt.received_at >= start,
            MoneyReceipt.received_at <= end,
        )
        .order_by(MoneyReceipt.received_at.desc())
        .all()
    )
    total = float(sum((r.amount for r in rows), Decimal("0")))
    return OkResponse(
        data={
            "date": day.isoformat(),
            "total": total,
            "count": len(rows),
            "items": [_receipt_out(r) for r in rows],
        }
    )
