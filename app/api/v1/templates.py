"""格式规范模板 CRUD（require.md 2.2.1）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.format_template import FormatTemplate
from app.schemas.template import TemplateCreate, TemplateOut, TemplateUpdate

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("", response_model=TemplateOut)
def create_template(body: TemplateCreate, db: Session = Depends(get_db)) -> FormatTemplate:
    tpl = FormatTemplate(name=body.name, description=body.description, content=body.content.model_dump())
    # 首个模板自动设为默认
    if db.query(FormatTemplate).count() == 0:
        tpl.is_default = True
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.get("", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db)) -> list[FormatTemplate]:
    return list(db.scalars(select(FormatTemplate).order_by(FormatTemplate.id)))


@router.get("/{tpl_id}", response_model=TemplateOut)
def get_template(tpl_id: int, db: Session = Depends(get_db)) -> FormatTemplate:
    tpl = db.get(FormatTemplate, tpl_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail="模板不存在")
    return tpl


@router.put("/{tpl_id}", response_model=TemplateOut)
def update_template(tpl_id: int, body: TemplateUpdate, db: Session = Depends(get_db)) -> FormatTemplate:
    tpl = db.get(FormatTemplate, tpl_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail="模板不存在")
    if body.name is not None:
        tpl.name = body.name
    if body.description is not None:
        tpl.description = body.description
    if body.content is not None:
        tpl.content = body.content.model_dump()
    db.commit()
    db.refresh(tpl)
    return tpl


@router.delete("/{tpl_id}")
def delete_template(tpl_id: int, db: Session = Depends(get_db)) -> dict:
    tpl = db.get(FormatTemplate, tpl_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail="模板不存在")
    db.delete(tpl)
    db.commit()
    return {"ok": True}


@router.post("/{tpl_id}/set-default", response_model=TemplateOut)
def set_default_template(tpl_id: int, db: Session = Depends(get_db)) -> FormatTemplate:
    tpl = db.get(FormatTemplate, tpl_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail="模板不存在")
    db.execute(update(FormatTemplate).values(is_default=False))
    tpl.is_default = True
    db.commit()
    db.refresh(tpl)
    return tpl
