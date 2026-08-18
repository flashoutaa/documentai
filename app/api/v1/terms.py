"""专有名词库 CRUD 与批量导入（require.md 2.3.1）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.term import Term
from app.schemas.term import TermBatchImport, TermCreate, TermImportResult, TermOut, TermUpdate

router = APIRouter(prefix="/terms", tags=["terms"])


@router.post("", response_model=TermOut)
def create_term(body: TermCreate, db: Session = Depends(get_db)) -> Term:
    if db.scalar(select(Term).where(Term.full_name == body.full_name)):
        raise HTTPException(status_code=400, detail=f"全称已存在：{body.full_name}")
    term = Term(full_name=body.full_name, short_names=body.short_names, category=body.category)
    db.add(term)
    db.commit()
    db.refresh(term)
    return term


@router.get("", response_model=list[TermOut])
def list_terms(category: str | None = None, db: Session = Depends(get_db)) -> list[Term]:
    stmt = select(Term).order_by(Term.id)
    if category:
        stmt = stmt.where(Term.category == category)
    return list(db.scalars(stmt))


@router.put("/{term_id}", response_model=TermOut)
def update_term(term_id: int, body: TermUpdate, db: Session = Depends(get_db)) -> Term:
    term = db.get(Term, term_id)
    if term is None:
        raise HTTPException(status_code=404, detail="词条不存在")
    if body.full_name is not None:
        term.full_name = body.full_name
    if body.short_names is not None:
        term.short_names = body.short_names
    if body.category is not None:
        term.category = body.category
    db.commit()
    db.refresh(term)
    return term


@router.delete("/{term_id}")
def delete_term(term_id: int, db: Session = Depends(get_db)) -> dict:
    term = db.get(Term, term_id)
    if term is None:
        raise HTTPException(status_code=404, detail="词条不存在")
    db.delete(term)
    db.commit()
    return {"ok": True}


@router.post("/import", response_model=TermImportResult)
def import_terms(body: TermBatchImport, db: Session = Depends(get_db)) -> TermImportResult:
    imported = 0
    skipped = 0
    errors: list[str] = []
    for item in body.items:
        if db.scalar(select(Term).where(Term.full_name == item.full_name)):
            skipped += 1
            continue
        try:
            db.add(Term(full_name=item.full_name, short_names=item.short_names, category=item.category))
            imported += 1
        except Exception as e:  # noqa: BLE001
            errors.append(f"{item.full_name}: {e}")
    db.commit()
    return TermImportResult(imported=imported, skipped=skipped, errors=errors)
