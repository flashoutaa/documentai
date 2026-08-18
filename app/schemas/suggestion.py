"""审查建议 schema（require.md 3.2 核心交互）。"""
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ReviewType, SuggestionStatus


class DocPosition(BaseModel):
    """定位：段落索引为主，页码/字符区间可选。"""

    paragraph_index: int = 0
    page: int | None = None
    start: int | None = None
    end: int | None = None


class SuggestionOut(BaseModel):
    id: int
    task_id: int
    doc_position: DocPosition
    original_text: str
    suggested_text: str
    review_type: ReviewType
    reason: str | None
    status: SuggestionStatus
    modified_text: str | None
    handled_at: datetime | None

    model_config = {"from_attributes": True}


class SuggestionUpdate(BaseModel):
    """接受 / 拒绝 / 自行修改。"""

    status: SuggestionStatus
    modified_text: str | None = Field(default=None, description="status=modified 时必填")


class BatchUpdate(BaseModel):
    status: SuggestionStatus = SuggestionStatus.ACCEPTED
    suggestion_ids: list[int] | None = None  # None 表示该任务全部待处理建议
