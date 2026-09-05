"""Bills + receipts — create, collect, cancel, delete (Next/PHP parity)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.datetime_local import parse_clinic_local_datetime
from app.db import get_db
from app.models import Bill, Client, MoneyReceipt, User
from app.schemas import BillCreate, BillOut, OkResponse, ReceiptCreate, ReceiptOut

router = APIRouter(tags=["billing"])

PAYMENT_MODES = {"Cash", "Online", "Cheque", "Other"}
COLLECTABLE = {"pending", "partial", "open"}


def _optional_clinic_datetime(value: str | None):
    try:
        return parse_clinic_local_datetime(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime: {value}",
        ) from exc


class CollectBillBody(BaseModel):
    amount: float = Field(gt=0)
    payment_mode: str = "Cash"
    description: str | None = None
    receipt_datetime: str | None = None


def _client(db: Session, clinic_id: int, client_id: int) -> Client:
    row = (
        db.query(Client)
        .filter(Client.client_id == client_id, Client.clinic_id == clinic_id, Client.visible.is_(True))
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return row


def _normalize_status(raw: str | None) -> str:
    s = (raw or "pending").strip().lower()
    if s == "open":
        return "pending"
    return s


def _bill_paid_total(db: Session, bill_id: int) -> Decimal:
    total = (
        db.query(func.coalesce(func.sum(MoneyReceipt.amount), 0))
        .filter(
            MoneyReceipt.bill_id == bill_id,
            MoneyReceipt.visible.is_(True),
        )
        .scalar()
    )
    return Decimal(str(total or 0))


def _linked_receipt_count(db: Session, bill_id: int) -> int:
    return int(
        db.query(func.count(MoneyReceipt.receipt_id))
        .filter(
            MoneyReceipt.bill_id == bill_id,
            MoneyReceipt.visible.is_(True),
        )
        .scalar()
        or 0
    )


def _compute_bill_status(db: Session, bill: Bill) -> str:
    """Derive status from payments; cancelled stays cancelled."""
    current = _normalize_status(bill.status)
    if current == "cancelled":
        return "cancelled"
    paid = _bill_paid_total(db, bill.bill_id)
    due = Decimal(str(bill.amount_due))
    if paid >= due:
        return "paid"
    if paid > 0:
        return "partial"
    return "pending"


def _sync_bill_status(db: Session, bill: Bill) -> str:
    bill.status = _compute_bill_status(db, bill)
    return bill.status


def _orphan_receipts(db: Session, bill_id: int) -> None:
    (
        db.query(MoneyReceipt)
        .filter(MoneyReceipt.bill_id == bill_id)
        .update({MoneyReceipt.bill_id: None}, synchronize_session=False)
    )


def _get_bill(db: Session, clinic_id: int, bill_id: int) -> Bill:
    bill = (
        db.query(Bill)
        .filter(Bill.bill_id == bill_id, Bill.clinic_id == clinic_id, Bill.visible.is_(True))
        .first()
    )
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return bill


def _bill_out(db: Session, bill: Bill) -> dict:
    data = BillOut.model_validate(bill).model_dump()
    data["amount_due"] = float(bill.amount_due)
    # Always reflect payment totals (heals stale status after soft-delete races).
    data["status"] = _compute_bill_status(db, bill)
    data["total_paid"] = float(_bill_paid_total(db, bill.bill_id))
    data["linked_receipt_count"] = _linked_receipt_count(db, bill.bill_id)
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
    return OkResponse(data=[_bill_out(db, r) for r in rows])


@router.post("/clients/{client_id}/bills", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_bill(
    client_id: int,
    body: BillCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    _client(db, user.clinic_id, client_id)
    issued_at = _optional_clinic_datetime(body.issued_datetime)
    bill = Bill(
        clinic_id=user.clinic_id,
        client_id=client_id,
        amount_due=Decimal(str(body.amount_due)),
        status="pending",
        description=body.description,
        user_id=user.user_id,
        **({"issued_at": issued_at} if issued_at else {}),
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return OkResponse(data=_bill_out(db, bill))


@router.post("/bills/{bill_id}/collect", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def collect_bill(
    bill_id: int,
    body: CollectBillBody,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    bill = _get_bill(db, user.clinic_id, bill_id)
    st = _normalize_status(bill.status)
    if st not in COLLECTABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot collect on a {st} bill",
        )
    if body.payment_mode not in PAYMENT_MODES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment mode")

    received_at = _optional_clinic_datetime(body.receipt_datetime)
    receipt = MoneyReceipt(
        clinic_id=user.clinic_id,
        client_id=bill.client_id,
        bill_id=bill.bill_id,
        amount=Decimal(str(body.amount)),
        payment_mode=body.payment_mode,
        description=(body.description or "").strip() or None,
        user_id=user.user_id,
        **({"received_at": received_at} if received_at else {}),
    )
    db.add(receipt)
    db.flush()
    bill_status = _sync_bill_status(db, bill)
    db.commit()
    db.refresh(receipt)
    return OkResponse(
        data={
            "receipt_id": receipt.receipt_id,
            "bill_status": bill_status,
            "receipt": _receipt_out(receipt),
            "bill": _bill_out(db, bill),
        }
    )


@router.post("/bills/{bill_id}/cancel", response_model=OkResponse)
def cancel_bill(
    bill_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    bill = _get_bill(db, user.clinic_id, bill_id)
    if _normalize_status(bill.status) == "cancelled":
        return OkResponse(data=_bill_out(db, bill))
    linked = _linked_receipt_count(db, bill.bill_id)
    if linked > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Delete {linked} linked receipt{'s' if linked != 1 else ''} first, "
                "then cancel this bill"
            ),
        )
    bill.status = "cancelled"
    db.commit()
    db.refresh(bill)
    return OkResponse(data=_bill_out(db, bill))


@router.delete("/bills/{bill_id}", response_model=OkResponse)
def delete_bill(
    bill_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    bill = _get_bill(db, user.clinic_id, bill_id)
    if _normalize_status(bill.status) != "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only cancelled bills can be deleted. Cancel the bill first.",
        )
    _orphan_receipts(db, bill.bill_id)
    db.delete(bill)
    db.commit()
    return OkResponse(data={"bill_id": bill_id, "deleted": True})


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
        if _normalize_status(bill.status) not in COLLECTABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot collect on a {_normalize_status(bill.status)} bill",
            )

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
    db.flush()
    if bill:
        _sync_bill_status(db, bill)
    db.commit()
    db.refresh(receipt)
    return OkResponse(data=_receipt_out(receipt))


@router.delete("/receipts/{receipt_id}", response_model=OkResponse)
def delete_receipt(
    receipt_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    receipt = (
        db.query(MoneyReceipt)
        .filter(
            MoneyReceipt.receipt_id == receipt_id,
            MoneyReceipt.clinic_id == user.clinic_id,
            MoneyReceipt.visible.is_(True),
        )
        .first()
    )
    if not receipt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    bill_id = receipt.bill_id
    receipt.visible = False
    # Session autoflush is off — flush so paid-total query excludes this receipt.
    db.flush()
    if bill_id:
        bill = db.get(Bill, bill_id)
        if bill and bill.clinic_id == user.clinic_id and bill.visible:
            _sync_bill_status(db, bill)
    db.commit()
    return OkResponse(data={"receipt_id": receipt_id, "deleted": True})


@router.get("/desk/receipts/today", response_model=OkResponse)
def receipts_today(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    on: date | None = Query(default=None),
) -> OkResponse:
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
    client_ids = {r.client_id for r in rows}
    names: dict[int, str] = {}
    if client_ids:
        for c in (
            db.query(Client.client_id, Client.name)
            .filter(Client.clinic_id == user.clinic_id, Client.client_id.in_(client_ids))
            .all()
        ):
            names[c.client_id] = c.name

    items = []
    for r in rows:
        item = _receipt_out(r)
        item["client_name"] = names.get(r.client_id) or f"Patient #{r.client_id}"
        items.append(item)

    total = float(sum((r.amount for r in rows), Decimal("0")))
    return OkResponse(
        data={
            "date": day.isoformat(),
            "total": total,
            "count": len(rows),
            "items": items,
        }
    )
