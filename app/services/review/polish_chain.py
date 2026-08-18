"""句意优化链（require.md 2.4）。

- LLM 模式：结构化输出 PolishResult，保持原意、不动事实
- mock 模式：内置少量冗余句式规则（演示用）
"""
from __future__ import annotations

import logging
import re

from langchain_core.prompts import ChatPromptTemplate

from app.services.chunker import chunk_paragraphs
from app.services.review.base import PolishResult, ReviewIssue
from app.services.review.provider import get_chat_model
from app.services.review.typo_chain import _locate_paragraph

logger = logging.getLogger(__name__)

# mock 模式规则：正则为 (原文正则, 替换, 类型, 说明)
MOCK_POLISH_RULES: list[tuple[str, str, str, str]] = [
    (r"进行([\u4e00-\u9fa5]{2,8})", r"\1", "冗余啰嗦", "「进行」冗余，动词直接作谓语更简洁"),
    (r"非常非常", "非常", "冗余啰嗦", "「非常非常」重复，保留一个即可"),
    (r"以及等等", "等", "冗余啰嗦", "「以及等等」语义重复，保留「等」"),
]

SYSTEM_PROMPT = """你是一位资深公文写作专家。请优化用户提供的文档段落，使表达更流畅、正式、规范。

要求：
1. **保持原意不变**，不得增删事实性内容；
2. 对政策表述、法律条款等敏感内容，如无把握不要改动（可通过 type=衔接生硬 仅提示）；
3. 只优化确实存在问题（不通顺/冗余/口语化/逻辑不清/衔接生硬）的句子，不必每句都改；
4. 每条给出：原文片段 original、优化后 suggested、优化类型 type（语句不通/冗余啰嗦/口语化/逻辑不清/衔接生硬）、说明 reason；
5. 若无需要优化之处，返回空列表。

输出必须为 JSON。"""

HUMAN_TEMPLATE = """请优化以下文档段落（[N] 为段落编号）：
{chunk}"""


def _mock_check(text: str, para_idx: int) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    for pattern, repl, typ, reason in MOCK_POLISH_RULES:
        for m in re.finditer(pattern, text):
            original = m.group(0)
            suggested = re.sub(pattern, repl, original)
            if original != suggested:
                issues.append(
                    ReviewIssue(
                        review_type="polish",
                        original_text=original,
                        suggested_text=suggested,
                        reason=f"[{typ}] {reason}",
                        paragraph_index=para_idx,
                    )
                )
    return issues


def _llm_check(paragraph_texts: list[str], paragraph_indices: list[int], max_chars: int) -> list[ReviewIssue]:
    model = get_chat_model()
    if model is None:
        return []
    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("human", HUMAN_TEMPLATE)]
    )
    try:
        structured = model.with_structured_output(PolishResult, method="function_calling")
        chain = prompt | structured
        issues: list[ReviewIssue] = []
        for chunk in chunk_paragraphs(paragraph_texts, max_chars=max_chars):
            numbered = "\n".join(f"[{i}] {paragraph_texts[i]}" for i in chunk)
            result = chain.invoke({"chunk": numbered})
            for it in (result.issues if result else []):
                if not it.original or not it.suggested:
                    continue
                para_idx = _locate_paragraph(it.original, paragraph_texts, paragraph_indices)
                issues.append(
                    ReviewIssue(
                        review_type="polish",
                        original_text=it.original,
                        suggested_text=it.suggested,
                        reason=f"[{it.type}] {it.reason}",
                        paragraph_index=para_idx,
                    )
                )
        return issues
    except Exception as e:  # LLM 失败降级
        logger.warning("句意优化链 LLM 调用失败，降级 mock：%s", e)
        return _mock_check_all(paragraph_texts, paragraph_indices)


def _mock_check_all(paragraph_texts: list[str], paragraph_indices: list[int]) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    for text, idx in zip(paragraph_texts, paragraph_indices):
        issues.extend(_mock_check(text, idx))
    return issues


def check_polish(paragraph_texts: list[str], paragraph_indices: list[int], max_chars: int = 1200) -> list[ReviewIssue]:
    if get_chat_model() is None:
        return _mock_check_all(paragraph_texts, paragraph_indices)
    return _llm_check(paragraph_texts, paragraph_indices, max_chars)
