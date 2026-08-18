"""错别字审查链（require.md 2.1）。

- LLM 模式：结构化输出 TypoResult
- mock 模式：内置常见错别字表规则匹配（演示全流程，无需 API Key）
"""
from __future__ import annotations

import logging

from langchain_core.prompts import ChatPromptTemplate

from app.services.chunker import chunk_paragraphs
from app.services.review.base import ReviewIssue, TypoResult
from app.services.review.provider import get_chat_model

logger = logging.getLogger(__name__)

# 常见错别字表（mock 模式；也可作为 LLM 的参考样例）
MOCK_TYPO_MAP: dict[str, str] = {
    "必段": "必须",
    "举形": "举行",
    "布署": "部署",
    "做用": "作用",
    "已以": "以及",
    "帐号": "账号",
    "既将": "即将",
    "按装": "安装",
    "迫不急待": "迫不及待",
    "不径而走": "不胫而走",
    "一愁莫展": "一筹莫展",
    "甘败下风": "甘拜下风",
}

SYSTEM_PROMPT = """你是一位严谨的中文公文校对专家。请审查用户提供的文档段落，找出**错别字**（含易混淆字、标点误用、多字、漏字、字序颠倒）。

要求：
1. 只报告确定无疑的文字错误，宁缺毋滥；
2. 专有名词、人名、地名、机构名不得误判为错别字；
3. 每条给出：原文片段 original、修正后 suggested、错误类型 type（错别字/标点/多字/漏字/倒序）、修改理由 reason；
4. 若无错误，返回空列表。

输出必须为 JSON。"""

HUMAN_TEMPLATE = """请审查以下文档段落（[N] 为段落编号）：
{chunk}"""


def _mock_check(text: str, para_idx: int) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    for wrong, right in MOCK_TYPO_MAP.items():
        if wrong in text:
            issues.append(
                ReviewIssue(
                    review_type="typo",
                    original_text=wrong,
                    suggested_text=right,
                    reason=f"错别字：{wrong} 应为 {right}",
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
        # DeepSeek 等 OpenAI 兼容 API 不支持 response_format=json_schema，
        # 显式使用 function calling 获取结构化输出
        structured = model.with_structured_output(TypoResult, method="function_calling")
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
                        review_type="typo",
                        original_text=it.original,
                        suggested_text=it.suggested,
                        reason=f"[{it.type}] {it.reason}",
                        paragraph_index=para_idx,
                    )
                )
        return issues
    except Exception as e:  # LLM 失败降级，保证流程不断
        logger.warning("错别字链 LLM 调用失败，降级 mock：%s", e)
        return _mock_check_all(paragraph_texts, paragraph_indices)


def _locate_paragraph(original: str, paragraph_texts: list[str], paragraph_indices: list[int]) -> int:
    for text, idx in zip(paragraph_texts, paragraph_indices):
        if original and original in text:
            return idx
    return paragraph_indices[0] if paragraph_indices else 0


def _mock_check_all(paragraph_texts: list[str], paragraph_indices: list[int]) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    for text, idx in zip(paragraph_texts, paragraph_indices):
        issues.extend(_mock_check(text, idx))
    return issues


def check_typo(paragraph_texts: list[str], paragraph_indices: list[int], max_chars: int = 1200) -> list[ReviewIssue]:
    if get_chat_model() is None:
        return _mock_check_all(paragraph_texts, paragraph_indices)
    return _llm_check(paragraph_texts, paragraph_indices, max_chars)
