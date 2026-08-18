"""审查链共用数据结构。"""
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from app.schemas.common import ReviewType


@dataclass
class ReviewIssue:
    """一条审查建议（链输出 → DB suggestion 的中间结构）。"""

    review_type: str  # ReviewType 值
    original_text: str
    suggested_text: str
    reason: str = ""
    paragraph_index: int = 0
    start: int | None = None
    end: int | None = None
    position: dict = field(default_factory=dict)  # 扩展定位/结构化修复信息（格式链用）

    def to_doc_position(self) -> dict:
        pos = {"paragraph_index": self.paragraph_index}
        if self.start is not None:
            pos["start"] = self.start
        if self.end is not None:
            pos["end"] = self.end
        pos.update(self.position)
        return pos


# ============ LangChain 结构化输出模型 ============
# 每条链的 LLM 输出均定义为 Pydantic 模型，由 LangChain 输出解析器保证 JSON 稳定
# （require.md 5.3：结构化输出）


class TypoIssue(BaseModel):
    original: str = Field(description="原文中错误的文字片段")
    suggested: str = Field(description="修正后的文字")
    type: str = Field(description="错误类型：错别字/标点/多字/漏字/倒序")
    reason: str = Field(description="修改理由")


class TypoResult(BaseModel):
    issues: list[TypoIssue] = Field(default_factory=list)


class PolishIssue(BaseModel):
    original: str = Field(description="原文中需优化的句子或片段")
    suggested: str = Field(description="优化后的句子，保持原意不变")
    type: str = Field(description="优化类型：语句不通/冗余啰嗦/口语化/逻辑不清/衔接生硬")
    reason: str = Field(description="优化说明")


class PolishResult(BaseModel):
    issues: list[PolishIssue] = Field(default_factory=list)


class TermIssue(BaseModel):
    original: str = Field(description="文档中的不完整/不规范写法")
    suggested: str = Field(description="补全后的规范全称")
    full_name: str = Field(description="命中的专有名词规范全称")
    reason: str = Field(description="说明命中了哪个词库条目")


class TermResult(BaseModel):
    issues: list[TermIssue] = Field(default_factory=list)


class FormatIssue(BaseModel):
    position_desc: str = Field(description="问题位置描述，如 第3段")
    field: str = Field(description="不符合规范的字段，如 字体/字号/首行缩进/行距/对齐")
    expected: str = Field(description="规范要求")
    actual: str = Field(description="文档实际值")
    suggestion: str = Field(description="修改建议")


class FormatResult(BaseModel):
    issues: list[FormatIssue] = Field(default_factory=list)


# 各链输出模型注册表
CHAIN_RESULT_MODELS: dict[str, type[BaseModel]] = {
    ReviewType.TYPO.value: TypoResult,
    ReviewType.FORMAT.value: FormatResult,
    ReviewType.TERM.value: TermResult,
    ReviewType.POLISH.value: PolishResult,
}
