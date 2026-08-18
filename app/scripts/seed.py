"""初始化数据：默认格式规范模板 + 内置专有名词（幂等，可重复执行）。"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.format_template import FormatTemplate
from app.models.term import Term

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATE_CONTENT = {
    "body": {
        "font": "宋体",
        "size_pt": 12.0,  # 小四
        "first_line_indent_chars": 2.0,
        "line_spacing_pt": 28.0,
        "alignment": "justify",
        "bold": False,
    },
    "headings": {
        "1": {"font": "黑体", "size_pt": 16.0, "alignment": "center", "bold": True},
        "2": {"font": "黑体", "size_pt": 14.0, "bold": True},
        "3": {"font": "黑体", "size_pt": 12.0, "bold": True},
    },
    "other": {"description": "示例：正文宋体小四、首行缩进2字符、固定行距28磅、两端对齐；一级标题黑体三号居中加粗"},
}

BUILTIN_TERMS: list[dict] = [
    {"full_name": "中国特色社会主义", "short_names": ["特色社会主义", "中特社"], "category": "政治"},
    {"full_name": "中华人民共和国", "short_names": ["中华人共和国"], "category": "机构"},
    {"full_name": "两个一百年", "short_names": ["两个百年"], "category": "政治"},
    {"full_name": "全面建设社会主义现代化国家", "short_names": ["全面建设社会主义现代化"], "category": "政治"},
    {"full_name": "高质量发展", "short_names": ["高质发展", "高质量的发展"], "category": "政策"},
    {"full_name": "新质生产力", "short_names": ["新质生产"], "category": "政策"},
    {"full_name": "习近平新时代中国特色社会主义思想", "short_names": ["习思想", "习近平新时代思想"], "category": "政治"},
]


def ensure_seed_data(db: Session | None = None) -> None:
    own_session = db is None
    session = db or SessionLocal()
    try:
        if session.scalar(select(FormatTemplate).limit(1)) is None:
            session.add(
                FormatTemplate(
                    name="示例公文规范模板",
                    description="正文宋体小四、首行缩进2字符、固定行距28磅、两端对齐（示例，请按业务实际调整）",
                    content=DEFAULT_TEMPLATE_CONTENT,
                    is_default=True,
                )
            )
            logger.info("已创建默认格式规范模板")
        for item in BUILTIN_TERMS:
            if session.scalar(select(Term).where(Term.full_name == item["full_name"])):
                continue
            session.add(Term(**item))
        session.commit()
    finally:
        if own_session:
            session.close()


if __name__ == "__main__":
    ensure_seed_data()
    print("seed done")
