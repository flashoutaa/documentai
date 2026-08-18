"""文档上传 / 查询 / 删除（require.md 3.1 流程起点）。"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.models.document import Document
from app.models.review_task import ReviewTask
from app.models.suggestion import Suggestion
from app.schemas.document import DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXT = {".docx"}


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    template_id: int | None = Form(default=None),
    user_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
) -> Document:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="仅支持 .docx 格式（require.md 4 兼容性）")

    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest = settings.upload_dir / stored_name
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    doc = Document(
        filename=file.filename or stored_name,
        stored_path=str(dest),
        template_id=template_id,
        uploader=user_id,
        status="uploaded",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)) -> list[Document]:
    stmt = select(Document).order_by(Document.created_at.desc())
    return list(db.scalars(stmt))


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: Session = Depends(get_db)) -> Document:
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return doc


@router.get("/{doc_id}/preview")
def preview_document(doc_id: int, db: Session = Depends(get_db)) -> dict:
    """预览文档内容：解析 docx，返回结构化段落文本与基础格式信息。"""
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    try:
        from app.services.docx_parser import parse_docx

        parsed = parse_docx(doc.stored_path)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"文档解析失败：{e}")

    return {
        "filename": doc.filename,
        "paragraph_count": len(parsed.paragraphs),
        "char_count": parsed.char_count,
        "paragraphs": [
            {
                "index": p.index,
                "text": p.text,
                "font": p.font,
                "size_pt": p.size_pt,
                "alignment": p.alignment,
                "is_heading": p.is_heading,
                "heading_level": p.heading_level,
            }
            for p in parsed.paragraphs
        ],
    }


@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)) -> dict:
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    # 手动级联删除：建议 → 任务 → 文档
    task_ids = list(db.scalars(select(ReviewTask.id).where(ReviewTask.document_id == doc_id)))
    if task_ids:
        db.query(Suggestion).filter(Suggestion.task_id.in_(task_ids)).delete()
        db.query(ReviewTask).filter(ReviewTask.id.in_(task_ids)).delete()
    db.delete(doc)
    db.commit()
    path = Path(doc.stored_path)
    if path.exists():
        path.unlink()
    return {"ok": True}
