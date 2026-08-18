"""审查编排器（require.md 3.1 总体流程的核心执行逻辑）。

在后台任务中执行：
1. 加载任务/文档/规范模板/专有名词库
2. 解析 docx → 结构化段落
3. 按 require.md 2.5 的默认顺序执行所选审查链
4. 汇总、去重、落库
5. 更新任务进度与状态
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.document import Document
from app.models.review_task import ReviewTask
from app.models.suggestion import Suggestion
from app.models.term import Term
from app.schemas.common import ReviewType
from app.schemas.template import TemplateContent
from app.services.docx_parser import parse_docx
from app.services.review import format_chain, polish_chain, term_chain, typo_chain
from app.services.review.provider import resolve_provider

logger = logging.getLogger(__name__)

# 默认执行顺序（require.md 2.5：先保用词准确，再查格式、做润色）
DEFAULT_ORDER = [
    ReviewType.TERM.value,
    ReviewType.TYPO.value,
    ReviewType.FORMAT.value,
    ReviewType.POLISH.value,
]


def _template_content(db: Session, task: ReviewTask) -> TemplateContent | None:
    """取任务生效的规范模板（优先任务指定，其次文档关联，缺省用默认模板）。"""
    template_id = task.template_id
    doc = db.get(Document, task.document_id)
    if template_id is None and doc is not None:
        template_id = doc.template_id
    if template_id is None:
        from app.models.format_template import FormatTemplate

        tpl = db.query(FormatTemplate).filter(FormatTemplate.is_default.is_(True)).first()
        if tpl:
            template_id = tpl.id
    if template_id is None:
        return None
    from app.models.format_template import FormatTemplate

    tpl = db.get(FormatTemplate, template_id)
    if tpl is None:
        return None
    try:
        return TemplateContent.model_validate(tpl.content)
    except Exception:
        logger.warning("规范模板 %s 内容解析失败，按无模板处理", template_id)
        return None


def run_review_task(task_id: int) -> None:
    """后台执行审查任务（同步函数，由 BackgroundTasks 调用）。"""
    with SessionLocal() as db:
        task = db.get(ReviewTask, task_id)
        if task is None:
            logger.error("任务 %s 不存在", task_id)
            return
        doc = db.get(Document, task.document_id)
        if doc is None:
            task.status = "failed"
            task.error = "文档不存在"
            db.commit()
            return

        task.status = "running"
        task.started_at = __import__("datetime").datetime.now()
        task.llm_config = {"provider": resolve_provider(), "model": settings.LLM_MODEL}
        db.commit()

        try:
            _execute(db, task, doc)
        except Exception as e:  # noqa: BLE001
            logger.exception("审查任务 %s 失败", task_id)
            task.status = "failed"
            task.error = str(e)[:500]
            doc.status = "failed"
            db.commit()
            return

        task.progress = 100.0
        task.finished_at = __import__("datetime").datetime.now()
        task.status = "completed"
        doc.status = "reviewed"
        db.commit()


def _execute(db: Session, task: ReviewTask, doc: Document) -> None:
    parsed = parse_docx(doc.stored_path)
    texts = parsed.body_texts()
    indices = list(range(len(parsed.paragraphs)))
    terms = db.query(Term).all()
    template = _template_content(db, task)
    task.progress = 30.0
    db.commit()

    selected = [t for t in DEFAULT_ORDER if t in (task.review_types or [])]
    phase = 0
    total_phases = max(len(selected), 1)

    for review_type in selected:
        if review_type == ReviewType.TYPO.value:
            issues = typo_chain.check_typo(texts, indices, settings.CHUNK_MAX_CHARS)
        elif review_type == ReviewType.TERM.value:
            issues = term_chain.check_terms(texts, indices, terms)
        elif review_type == ReviewType.FORMAT.value:
            issues = format_chain.check_format(parsed.paragraphs, template)
        elif review_type == ReviewType.POLISH.value:
            issues = polish_chain.check_polish(texts, indices, settings.CHUNK_MAX_CHARS)
        else:
            continue

        _save_issues(db, task.id, issues)
        phase += 1
        task.progress = 30.0 + phase * (60.0 / total_phases)
        db.commit()


def _save_issues(db: Session, task_id: int, issues: list) -> None:
    """去重后写入建议表。去重键：段落 + 类型 + 原文 + 建议。"""
    seen: set[tuple] = set()
    for it in issues:
        key = (it.paragraph_index, it.review_type, it.original_text, it.suggested_text)
        if key in seen:
            continue
        seen.add(key)
        db.add(
            Suggestion(
                task_id=task_id,
                doc_position=it.to_doc_position(),
                original_text=it.original_text,
                suggested_text=it.suggested_text,
                review_type=it.review_type,
                reason=it.reason,
            )
        )
    db.commit()
