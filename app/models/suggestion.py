"""审查建议表（require.md §6 suggestion，核心交互表）。"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Suggestion(Base, TimestampMixin):
    __tablename__ = "suggestion"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("review_task.id"), nullable=False, index=True)
    # 定位信息 JSON：{"paragraph_index": 12, "page": 2, "start": 5, "end": 12}
    doc_position: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)  # 原文
    suggested_text: Mapped[str] = mapped_column(Text, nullable=False)  # 建议修改后
    review_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # typo | format | term | polish
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)  # 修改理由
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    # pending(待处理) | accepted(已接受) | rejected(已拒绝) | modified(已自行修改)
    modified_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # 用户自行修改后的文本
    handled_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
