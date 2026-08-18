"""格式规范模板表（require.md 2.2.1：业务人员自行配置格式规范）。"""
from sqlalchemy import Boolean, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class FormatTemplate(Base, TimestampMixin):
    __tablename__ = "format_template"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 规范内容 JSON，结构示例见 app/schemas/template.py 的 TemplateContent
    content: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
