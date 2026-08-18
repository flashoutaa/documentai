"""专有名词补齐链（require.md 2.3）。

确定性匹配：基于专有名词库，将文档中的简称/不完整写法补全为规范全称。
- 规范全称本身不视为"待补全"（命中 full_name 的区间受保护）
- 简称命中且不在全称区间内 → 提示补全
"""
from __future__ import annotations

from app.models.term import Term
from app.services.review.base import ReviewIssue


def _protected_spans(text: str, full_names: list[str]) -> list[tuple[int, int]]:
    """全称出现的区间（受保护，不提示补全）。"""
    spans: list[tuple[int, int]] = []
    for name in full_names:
        start = 0
        while True:
            pos = text.find(name, start)
            if pos == -1:
                break
            spans.append((pos, pos + len(name)))
            start = pos + 1
    return spans


def _overlaps(pos: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(not (end <= s or pos >= e) for s, e in spans)


def check_terms(
    paragraph_texts: list[str],
    paragraph_indices: list[int],
    terms: list[Term],
) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    if not terms:
        return issues

    full_names = sorted({t.full_name for t in terms}, key=len, reverse=True)
    short_map: list[tuple[str, str]] = []  # (简称, 全称)
    for t in terms:
        for short in t.short_names or []:
            short = short.strip()
            if short and short != t.full_name:
                short_map.append((short, t.full_name))
    short_map.sort(key=lambda x: len(x[0]), reverse=True)  # 长简称优先

    for text, para_idx in zip(paragraph_texts, paragraph_indices):
        spans = _protected_spans(text, full_names)
        # 记录已占用的建议区间，避免重复/嵌套
        used: list[tuple[int, int]] = []
        for short, full in short_map:
            start = 0
            while True:
                pos = text.find(short, start)
                if pos == -1:
                    break
                end = pos + len(short)
                if not _overlaps(pos, end, spans) and not _overlaps(pos, end, used):
                    issues.append(
                        ReviewIssue(
                            review_type="term",
                            original_text=short,
                            suggested_text=full,
                            reason=f"专有名词不完整：{short} 应为规范全称「{full}」",
                            paragraph_index=para_idx,
                            start=pos,
                            end=end,
                        )
                    )
                    used.append((pos, end))
                start = pos + 1

    return issues
