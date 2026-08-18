"""审查建议：查询 / 接受 / 拒绝 / 自行修改 / 批量（require.md 3.2 核心交互）。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.review_task import ReviewTask
from app.models.suggestion import Suggestion
from app.schemas.common import SuggestionStatus
from app.schemas.suggestion import BatchUpdate, SuggestionOut, SuggestionUpdate

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


@router.get("", response_model=list[SuggestionOut])
def list_suggestions(
    task_id: int,
    status: SuggestionStatus | None = None,
    review_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[Suggestion]:
    stmt = select(Suggestion).where(Suggestion.task_id == task_id).order_by(
        Suggestion.doc_position["paragraph_index"].as_integer(), Suggestion.id
    )
    if status:
        stmt = stmt.where(Suggestion.status == status.value)
    if review_type:
        stmt = stmt.where(Suggestion.review_type == review_type)
    return list(db.scalars(stmt))


@router.patch("/{sug_id}", response_model=SuggestionOut)
def update_suggestion(
    sug_id: int,
    body: SuggestionUpdate,
    user_id: int | None = None,
    db: Session = Depends(get_db),
) -> Suggestion:
    sug = db.get(Suggestion, sug_id)
    if sug is None:
        raise HTTPException(status_code=404, detail="建议不存在")

    if body.status == SuggestionStatus.MODIFIED and not body.modified_text:
        raise HTTPException(status_code=400, detail="自行修改必须提供 modified_text")

    sug.status = body.status.value
    sug.modified_text = body.modified_text if body.status == SuggestionStatus.MODIFIED else None
    sug.handled_by = user_id
    sug.handled_at = datetime.now()
    db.commit()
    db.refresh(sug)
    return sug


@router.post("/batch")
def batch_update(
    task_id: int,
    body: BatchUpdate,
    user_id: int | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """批量处理：不传 suggestion_ids 时处理该任务全部待处理建议。"""
    task = db.get(ReviewTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    stmt = select(Suggestion).where(Suggestion.task_id == task_id)
    if body.suggestion_ids:
        stmt = stmt.where(Suggestion.id.in_(body.suggestion_ids))
    else:
        stmt = stmt.where(Suggestion.status == SuggestionStatus.PENDING.value)

    rows = list(db.scalars(stmt))
    now = datetime.now()
    for sug in rows:
        sug.status = body.status.value
        sug.modified_text = None
        sug.handled_by = user_id
        sug.handled_at = now
    db.commit()
    return {"ok": True, "updated": len(rows)}
