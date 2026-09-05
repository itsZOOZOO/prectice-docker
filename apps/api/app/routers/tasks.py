from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app import media as media_svc
from app.models import Client, Task, TaskNote, User
from app.schemas import OkResponse, TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])

IST = ZoneInfo("Asia/Kolkata")
OPEN_STATUSES = {"Open", "Pending"}
PANEL_FILTERS = frozenset(
    {"today", "overdue", "future", "pending", "completed_today", "all"}
)


def _today_ist() -> date:
    return datetime.now(IST).date()


def _date_ist(dt: datetime | None) -> date | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).date()


def _is_open(status: str) -> bool:
    return (status or "").strip() in OPEN_STATUSES


def _task_out(
    task: Task,
    *,
    client_name: str | None = None,
    assignee_name: str | None = None,
    created_by_name: str | None = None,
    notes: list[dict] | None = None,
) -> dict:
    # Column attrs only — avoid validating ORM `notes` relationship here.
    data = TaskOut.model_validate(
        {
            "task_id": task.task_id,
            "clinic_id": task.clinic_id,
            "client_id": task.client_id,
            "task_description": task.task_description,
            "attachment_url": task.attachment_url,
            "due_date": task.due_date,
            "status": task.status,
            "assignee_id": task.assignee_id,
            "created_by": task.created_by,
            "completed_at": task.completed_at,
            "created_at": task.created_at,
        }
    ).model_dump()
    data["due_date"] = task.due_date.isoformat() if task.due_date else None
    data["client_name"] = client_name
    data["assignee_name"] = assignee_name
    data["created_by_name"] = created_by_name
    key = (task.attachment_url or "").strip() or None
    data["attachment_url"] = media_svc.resolve_media_key(key) if key else None
    data["notes"] = notes
    return data


def _enrich(db: Session, rows: list[Task], *, with_notes: bool = False) -> list[dict]:
    client_ids = {t.client_id for t in rows if t.client_id}
    user_ids = {t.assignee_id for t in rows if t.assignee_id} | {
        t.created_by for t in rows if t.created_by
    }
    clients = {
        c.client_id: c.name
        for c in db.query(Client).filter(Client.client_id.in_(client_ids)).all()
    } if client_ids else {}
    users = {
        u.user_id: u.full_name
        for u in db.query(User).filter(User.user_id.in_(user_ids)).all()
    } if user_ids else {}

    notes_by_task: dict[int, list[dict]] = {}
    if with_notes and rows:
        task_ids = [t.task_id for t in rows]
        note_rows = (
            db.query(TaskNote)
            .filter(TaskNote.task_id.in_(task_ids))
            .order_by(TaskNote.created_at.desc())
            .all()
        )
        note_user_ids = {n.user_id for n in note_rows if n.user_id}
        note_users = {
            u.user_id: u.full_name
            for u in db.query(User).filter(User.user_id.in_(note_user_ids)).all()
        } if note_user_ids else {}
        for n in note_rows:
            key = (n.attachment_url or "").strip() or None
            notes_by_task.setdefault(n.task_id, []).append(
                {
                    "note_id": n.note_id,
                    "note_text": n.note_text,
                    "attachment_url": media_svc.resolve_media_key(key) if key else None,
                    "created_at": n.created_at,
                    "user_name": note_users.get(n.user_id) if n.user_id else None,
                }
            )

    return [
        _task_out(
            t,
            client_name=clients.get(t.client_id) if t.client_id else None,
            assignee_name=users.get(t.assignee_id) if t.assignee_id else None,
            created_by_name=users.get(t.created_by) if t.created_by else None,
            notes=notes_by_task.get(t.task_id, []) if with_notes else None,
        )
        for t in rows
    ]


def _matches_filter(task: Task, panel_date: date, filt: str, today: date) -> bool:
    due = task.due_date
    completed = _date_ist(task.completed_at)
    open_ = _is_open(task.status)
    completed_ = (task.status or "").strip() == "Completed"

    if filt == "today":
        return (open_ and due == panel_date) or (completed_ and completed == panel_date)
    if filt == "overdue":
        return open_ and due is not None and due < today
    if filt == "future":
        return open_ and due is not None and due > today
    if filt == "pending":
        return open_
    if filt == "completed_today":
        return completed_ and completed == panel_date
    return True


def _get_clinic_task(db: Session, clinic_id: int, task_id: int) -> Task:
    task = (
        db.query(Task)
        .filter(Task.task_id == task_id, Task.clinic_id == clinic_id, Task.visible.is_(True))
        .first()
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.get("", response_model=OkResponse)
def list_tasks(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
    client_id: int | None = None,
    panel_date: date | None = Query(default=None, alias="date"),
    panel_filter: str | None = Query(default=None, alias="filter"),
    scope: Literal["all", "mine"] = Query(default="all"),
) -> OkResponse:
    query = db.query(Task).filter(Task.clinic_id == user.clinic_id, Task.visible.is_(True))
    if status_filter:
        query = query.filter(Task.status == status_filter)
    if client_id:
        query = query.filter(Task.client_id == client_id)
    if scope == "mine":
        query = query.filter(Task.assignee_id == user.user_id)

    rows = query.order_by(Task.due_date.asc().nullslast(), Task.created_at.desc()).limit(500).all()

    filt = (panel_filter or "").strip().lower()
    if filt in PANEL_FILTERS:
        day = panel_date or _today_ist()
        today = _today_ist()
        rows = [t for t in rows if _matches_filter(t, day, filt, today)]
        # Pending first, then by due, then newest
        rows.sort(
            key=lambda t: (
                0 if _is_open(t.status) else 1,
                t.due_date.isoformat() if t.due_date else "9999-99-99",
                -(t.created_at.timestamp() if t.created_at else 0),
            )
        )

    return OkResponse(
        data={
            "items": _enrich(db, rows),
            "date": (panel_date or _today_ist()).isoformat() if filt in PANEL_FILTERS else None,
            "filter": filt if filt in PANEL_FILTERS else None,
            "scope": scope if filt in PANEL_FILTERS else None,
        }
    )


@router.get("/{task_id}", response_model=OkResponse)
def get_task(
    task_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    task = _get_clinic_task(db, user.clinic_id, task_id)
    return OkResponse(data=_enrich(db, [task], with_notes=True)[0])


@router.post("", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    body: TaskCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    if body.client_id:
        client = (
            db.query(Client)
            .filter(
                Client.client_id == body.client_id,
                Client.clinic_id == user.clinic_id,
                Client.visible.is_(True),
            )
            .first()
        )
        if not client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    if body.assignee_id:
        assignee = (
            db.query(User)
            .filter(User.user_id == body.assignee_id, User.clinic_id == user.clinic_id, User.active.is_(True))
            .first()
        )
        if not assignee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found")

    task = Task(
        clinic_id=user.clinic_id,
        client_id=body.client_id,
        task_description=body.task_description.strip(),
        due_date=body.due_date,
        status="Open",
        created_by=user.user_id,
        assignee_id=body.assignee_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return OkResponse(data=_enrich(db, [task])[0])


@router.patch("/{task_id}", response_model=OkResponse)
def update_task(
    task_id: int,
    body: TaskUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    task = _get_clinic_task(db, user.clinic_id, task_id)

    payload = body.model_dump(exclude_unset=True)
    if "status" in payload:
        status_val = payload["status"]
        if status_val not in {"Open", "Completed", "Cancelled"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")
        task.status = status_val
        task.completed_at = datetime.now(timezone.utc) if status_val == "Completed" else None
    if "task_description" in payload and payload["task_description"] is not None:
        task.task_description = payload["task_description"].strip()
    if "due_date" in payload:
        task.due_date = payload["due_date"]
    if "assignee_id" in payload:
        task.assignee_id = payload["assignee_id"]
    if "client_id" in payload:
        task.client_id = payload["client_id"]

    db.commit()
    db.refresh(task)
    return OkResponse(data=_enrich(db, [task], with_notes=True)[0])


@router.post("/{task_id}/notes", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
async def add_task_note(
    task_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    note_text: Annotated[str | None, Form()] = None,
    voice: Annotated[UploadFile | None, File()] = None,
) -> OkResponse:
    task = _get_clinic_task(db, user.clinic_id, task_id)
    text = (note_text or "").strip()

    attachment_key: str | None = None
    if voice is not None and voice.filename:
        raw = await voice.read()
        mime = media_svc.validate_task_voice(voice.content_type, len(raw), voice.filename or "voice.webm")
        attachment_key = media_svc.upload_task_voice(
            raw,
            filename=voice.filename or "voice.webm",
            content_type=mime,
        )

    if not text and not attachment_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Note text or voice is required",
        )
    if not text:
        text = "Voice note"

    note = TaskNote(
        task_id=task.task_id,
        user_id=user.user_id,
        note_text=text,
        attachment_url=attachment_key,
    )
    db.add(note)
    db.commit()
    db.refresh(task)
    return OkResponse(data=_enrich(db, [task], with_notes=True)[0])
