"""审查任务表（require.md §6 review_task）。"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ReviewTask(Base, TimestampMixin):
    __tablename__ = "review_task"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), nullable=False, index=True)
    # 任务级格式规范（可覆盖文档关联的模板，require.md 3.1）
    template_id: Mapped[int | None] = mapped_column(ForeignKey("format_template.id"), nullable=True)
    # 审查类型: ["typo","format","term","polish"] 可组合（require.md 2.5）
    review_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    # pending | running | completed | failed
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0-100
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 执行时使用的模型配置快照
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
