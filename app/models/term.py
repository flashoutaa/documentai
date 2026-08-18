"""专有名词库表（require.md 2.3.1）。"""
from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Term(Base, TimestampMixin):
    __tablename__ = "term"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)  # 规范全称
    short_names: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # 允许的简称/不完整写法
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 分类，如 政治/政策
