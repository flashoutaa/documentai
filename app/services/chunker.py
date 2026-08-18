"""长文本分块（require.md 5.3：超上下文窗口的文档按段落分块审查）。

按段落边界聚合，保证：
- 每块不超过 max_chars（超长单段则按句切分）
- 相邻块保留少量重叠，避免审查盲区
"""
from __future__ import annotations


def chunk_paragraphs(paragraphs: list[str], max_chars: int = 1200, overlap_chars: int = 80) -> list[list[int]]:
    """返回每个块的段落索引列表。

    Args:
        paragraphs: 段落文本列表（与文档段落一一对应）
        max_chars: 单块最大字符数
        overlap_chars: 跨块重叠字符数（取上一块末尾段落补入）
    """
    chunks: list[list[int]] = []
    current: list[int] = []
    current_chars = 0

    for i, text in enumerate(paragraphs):
        # 超长单段：按句切分
        if len(text) > max_chars:
            if current:
                chunks.append(current)
                current, current_chars = [], 0
            for sub in _split_long_paragraph(text, max_chars):
                chunks.append([i])
            continue

        if current_chars + len(text) > max_chars and current:
            chunks.append(current)
            current, current_chars = [], 0
        current.append(i)
        current_chars += len(text)

    if current:
        chunks.append(current)

    # 重叠：把上一块末尾段落并入下一块开头（去重）
    if overlap_chars > 0 and len(chunks) > 1:
        merged: list[list[int]] = []
        for ci, chunk in enumerate(chunks):
            if ci > 0:
                prev = chunks[ci - 1]
                tail: list[int] = []
                tail_chars = 0
                for pi in reversed(prev):
                    tail.insert(0, pi)
                    tail_chars += len(paragraphs[pi])
                    if tail_chars >= overlap_chars:
                        break
                chunk = tail + chunk
            merged.append(sorted(set(chunk)))
        chunks = merged

    return chunks


def _split_long_paragraph(text: str, max_chars: int) -> list[str]:
    """超长段落按句子切分。"""
    import re

    sentences = re.split(r"(?<=[。！？；])", text)
    parts: list[str] = []
    buf = ""
    for s in sentences:
        if s and len(s) > max_chars:  # 超长句强制截断
            while s:
                parts.append(s[:max_chars])
                s = s[max_chars:]
            continue
        if len(buf) + len(s) > max_chars and buf:
            parts.append(buf)
            buf = s
        else:
            buf += s
    if buf:
        parts.append(buf)
    return parts
