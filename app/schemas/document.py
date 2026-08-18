"""文档 schema。"""
from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    filename: str
    template_id: int | None
    uploader: int | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentDetailOut(DocumentOut):
    paragraph_count: int | None = None
    char_count: int | None = None
