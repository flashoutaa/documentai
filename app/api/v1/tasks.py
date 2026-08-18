"""审查任务：创建（后台执行）/ 状态 / 导出（require.md 3.1、3.3）。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.models.document import Document
from app.models.review_task import ReviewTask
from app.models.suggestion import Suggestion
from app.schemas.common import SuggestionStatus
from app.schemas.task import TaskCreate, TaskOut, TaskProgressOut
from app.services.docx_applier import apply_suggestions_to_docx
from app.services.review.orchestrator import run_review_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskOut)
def create_task(
    body: TaskCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ReviewTask:
    doc = db.get(Document, body.document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")

    review_types = [t.value if hasattr(t, "value") else str(t) for t in body.review_types]
    task = ReviewTask(
        document_id=body.document_id,
        review_types=review_types,
        template_id=body.template_id,
        status="pending",
        progress=0.0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 后台异步执行（require.md 4 性能：审查过程异步，页面可离开）
    background.add_task(run_review_task, task.id)
    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)) -> list[ReviewTask]:
    return list(db.scalars(select(ReviewTask).order_by(ReviewTask.created_at.desc())))


@router.get("/{task_id}", response_model=TaskProgressOut)
def get_task(task_id: int, db: Session = Depends(get_db)) -> TaskProgressOut:
    task = db.get(ReviewTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    rows = db.execute(
        select(
            Suggestion.review_type,
            Suggestion.status,
            func.count(Suggestion.id),
        ).where(Suggestion.task_id == task_id).group_by(Suggestion.review_type, Suggestion.status)
    ).all()

    counts: dict[str, int] = {}
    for review_type, status, cnt in rows:
        counts[f"{review_type}:{status}"] = cnt
    counts["total"] = sum(c for _, _, c in rows)

    out = TaskProgressOut.model_validate(task)
    out.suggestion_counts = counts
    return out


@router.post("/{task_id}/export")
def export_task(task_id: int, db: Session = Depends(get_db)) -> FileResponse:
    task = db.get(ReviewTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="任务未完成，无法导出")

    doc = db.get(Document, task.document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")

    suggestions = list(
        db.scalars(
            select(Suggestion)
            .where(
                Suggestion.task_id == task_id,
                Suggestion.status.in_([SuggestionStatus.ACCEPTED.value, SuggestionStatus.MODIFIED.value]),
            )
            .order_by(Suggestion.doc_position["paragraph_index"].as_integer())
        )
    )

    stem = doc.filename.rsplit(".", 1)[0]
    out_name = f"{stem}_审查修订版.docx"
    out_path = settings.export_dir / f"task_{task_id}_{out_name}"
    apply_suggestions_to_docx(doc.stored_path, suggestions, str(out_path))

    return FileResponse(
        path=str(out_path),
        filename=out_name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
