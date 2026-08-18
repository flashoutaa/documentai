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
from app.schemas.task import TaskCreate, TaskListItem, TaskOut, TaskProgressOut
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


@router.get("", response_model=list[TaskListItem])
def list_tasks(db: Session = Depends(get_db)) -> list[TaskListItem]:
    """任务列表（审查结果页）：按时间倒序，附带文档名与建议总数。"""
    tasks = list(db.scalars(select(ReviewTask).order_by(ReviewTask.created_at.desc())))
    doc_ids = {t.document_id for t in tasks}
    doc_names: dict[int, str] = {}
    if doc_ids:
        for d in db.scalars(select(Document).where(Document.id.in_(doc_ids))):
            doc_names[d.id] = d.filename
    rows = db.execute(
        select(Suggestion.task_id, func.count(Suggestion.id)).group_by(Suggestion.task_id)
    ).all()
    totals = dict(rows)

    out: list[TaskListItem] = []
    for t in tasks:
        out.append(
            TaskListItem(
                id=t.id,
                document_id=t.document_id,
                review_types=t.review_types,
                status=t.status,
                progress=t.progress,
                error=t.error,
                created_at=t.created_at,
                started_at=t.started_at,
                finished_at=t.finished_at,
                filename=doc_names.get(t.document_id),
                suggestion_total=totals.get(t.id, 0),
            )
        )
    return out


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


@router.get("/{task_id}/review")
def review_detail(task_id: int, db: Session = Depends(get_db)) -> dict:
    """审查详情：原文全文 + 每条建议在原文中的精确位置（用于内联对照展示）。

    - 文本类建议（typo/term/polish）：自动在对应段落文本中定位 start/end；
      定位失败（如 LLM 改写与原文不一致）时 start/end 为 null，按段落级展示
    - 格式类建议：无文本区间，段落级展示
    """
    task = db.get(ReviewTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    doc = db.get(Document, task.document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")

    from app.services.docx_parser import parse_docx

    parsed = parse_docx(doc.stored_path)
    paragraphs = [
        {
            "index": p.index,
            "text": p.text,
            "is_heading": p.is_heading,
            "heading_level": p.heading_level,
            "alignment": p.alignment,
            "font": p.font,
            "size_pt": p.size_pt,
        }
        for p in parsed.paragraphs
    ]

    sugs = list(
        db.scalars(
            select(Suggestion).where(Suggestion.task_id == task_id).order_by(Suggestion.id)
        )
    )
    out: list[dict] = []
    for s in sugs:
        para_idx = (s.doc_position or {}).get("paragraph_index", 0)
        item = {
            "id": s.id,
            "review_type": s.review_type,
            "original_text": s.original_text,
            "suggested_text": s.suggested_text,
            "modified_text": s.modified_text,
            "reason": s.reason,
            "status": s.status,
            "paragraph_index": para_idx,
            "start": None,
            "end": None,
        }
        if s.review_type != "format" and 0 <= para_idx < len(paragraphs):
            span = _locate_span(s, paragraphs[para_idx]["text"])
            if span:
                item["start"], item["end"] = span
        out.append(item)

    return {"filename": doc.filename, "paragraphs": paragraphs, "suggestions": out}


def _locate_span(sug, para_text: str) -> tuple[int, int] | None:
    """定位建议在段落文本中的区间：优先 doc_position 已有区间，否则按原文查找。"""
    pos = sug.doc_position or {}
    start, end = pos.get("start"), pos.get("end")
    if start is not None and end is not None:
        if 0 <= start < end <= len(para_text) and para_text[start:end] == sug.original_text:
            return start, end
    if not sug.original_text:
        return None
    p = para_text.find(sug.original_text)
    if p == -1:
        return None
    return p, p + len(sug.original_text)


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
