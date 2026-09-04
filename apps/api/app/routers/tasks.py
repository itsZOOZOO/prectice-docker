from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Client, Task, User
from app.schemas import OkResponse, TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _task_out(task: Task, client_name: str | None = None, assignee_name: str | None = None) -> dict:
    data = TaskOut.model_validate(task).model_dump()
    data["due_date"] = task.due_date.isoformat() if task.due_date else None
    data["client_name"] = client_name
    data["assignee_name"] = assignee_name
    return data


def _enrich(db: Session, rows: list[Task]) -> list[dict]:
    client_ids = {t.client_id for t in rows if t.client_id}
    user_ids = {t.assignee_id for t in rows if t.assignee_id}
    clients = {
        c.client_id: c.name
        for c in db.query(Client).filter(Client.client_id.in_(client_ids)).all()
    } if client_ids else {}
    users = {
        u.user_id: u.full_name
        for u in db.query(User).filter(User.user_id.in_(user_ids)).all()
    } if user_ids else {}
    return [
        _task_out(t, clients.get(t.client_id) if t.client_id else None, users.get(t.assignee_id) if t.assignee_id else None)
        for t in rows
    ]


@router.get("", response_model=OkResponse)
def list_tasks(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
    client_id: int | None = None,
) -> OkResponse:
    query = db.query(Task).filter(Task.clinic_id == user.clinic_id, Task.visible.is_(True))
    if status_filter:
        query = query.filter(Task.status == status_filter)
    if client_id:
        query = query.filter(Task.client_id == client_id)
    rows = query.order_by(Task.created_at.desc()).limit(200).all()
    return OkResponse(data={"items": _enrich(db, rows)})


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
    task = (
        db.query(Task)
        .filter(Task.task_id == task_id, Task.clinic_id == user.clinic_id, Task.visible.is_(True))
        .first()
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

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
    return OkResponse(data=_enrich(db, [task])[0])
