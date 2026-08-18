"""专有名词库 schema（require.md 2.3.1）。"""
from datetime import datetime

from pydantic import BaseModel, Field


class TermBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=256)
    short_names: list[str] = Field(default_factory=list)
    category: str | None = None


class TermCreate(TermBase):
    pass


class TermUpdate(BaseModel):
    full_name: str | None = None
    short_names: list[str] | None = None
    category: str | None = None


class TermOut(TermBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TermBatchImport(BaseModel):
    """批量导入：支持 [{full_name, short_names, category}] 或 CSV 行。"""

    items: list[TermBase]


class TermImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
