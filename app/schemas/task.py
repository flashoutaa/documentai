"""审查任务 schema。"""
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ReviewType


class TaskCreate(BaseModel):
    document_id: int
    review_types: list[ReviewType] = Field(
        default_factory=lambda: [t.value for t in ReviewType]
    )
    template_id: int | None = None  # 覆盖文档的格式规范


class TaskOut(BaseModel):
    id: int
    document_id: int
    review_types: list[str]
    status: str
    progress: float
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class TaskProgressOut(TaskOut):
    suggestion_counts: dict[str, int] = Field(default_factory=dict)  # 各类型建议数


class TaskListItem(TaskOut):
    """任务列表项（审查结果页）：附带文档名与建议总数。"""

    filename: str | None = None
    suggestion_total: int = 0
