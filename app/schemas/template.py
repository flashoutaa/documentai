"""格式规范模板 schema（require.md 2.2.1 配置项）。"""
from datetime import datetime

from pydantic import BaseModel, Field


class FontRule(BaseModel):
    """字体规则。"""

    font: str | None = None  # 如 "宋体" / "黑体"
    size_pt: float | None = None  # 字号（pt），小四=12


class ParagraphRule(BaseModel):
    """某类段落的格式要求。"""

    font: str | None = None
    size_pt: float | None = None
    first_line_indent_chars: float | None = None  # 首行缩进（字符），如 2
    line_spacing: float | None = None  # 行距倍数，如 1.5；或固定值(磅)见 line_spacing_pt
    line_spacing_pt: float | None = None  # 固定行距（磅），如 28
    space_before_pt: float | None = None
    space_after_pt: float | None = None
    alignment: str | None = None  # left | center | right | justify
    bold: bool | None = None


class TemplateContent(BaseModel):
    """规范内容整体结构（JSON 存储）。"""

    body: ParagraphRule = Field(default_factory=ParagraphRule)  # 正文规则
    headings: dict[str, ParagraphRule] = Field(  # 各级标题规则: {"1": {...}, "2": {...}}
        default_factory=dict
    )
    other: dict = Field(default_factory=dict)  # 预留：页边距/页眉页脚等扩展


class TemplateCreate(BaseModel):
    name: str
    description: str | None = None
    content: TemplateContent = Field(default_factory=TemplateContent)


class TemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    content: TemplateContent | None = None


class TemplateOut(BaseModel):
    id: int
    name: str
    description: str | None
    content: TemplateContent
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}
