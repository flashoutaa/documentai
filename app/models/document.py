"""上传文档表（require.md §6 document）。"""
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Document(Base, TimestampMixin):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)  # 原始文件名
    stored_path: Mapped[str] = mapped_column(String(512), nullable=False)  # 存储路径
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("format_template.id"), nullable=True
    )
    uploader: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="uploaded", nullable=False)
    # uploaded | parsing | parsed | reviewing | reviewed | failed
