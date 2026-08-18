"""格式审查链（require.md 2.2.2）。

采用确定性规则引擎：将解析出的段落样式与规范模板逐项比对。
格式检查不依赖 LLM（要求 100% 可复现，见 require.md 非功能需求）。
"""
from __future__ import annotations

from app.schemas.template import TemplateContent
from app.services.docx_parser import ParagraphMeta
from app.services.review.base import ReviewIssue

_ALIGN_LABEL = {
    "left": "左对齐",
    "center": "居中",
    "right": "右对齐",
    "justify": "两端对齐",
}


def _describe(value, kind: str) -> str:
    if value is None:
        return "未设置"
    if kind == "font":
        return str(value)
    if kind == "size":
        return f"{value:g}pt"
    if kind == "indent":
        return f"{value:g} 字符"
    if kind == "align":
        return _ALIGN_LABEL.get(str(value), str(value))
    return str(value)


def _fmt_issue(
    para: ParagraphMeta,
    field: str,
    expected: str,
    actual: str,
    suggestion: str,
) -> ReviewIssue:
    snippet = para.text[:60] + ("…" if len(para.text) > 60 else "")
    return ReviewIssue(
        review_type="format",
        original_text=snippet,
        suggested_text=suggestion,
        reason=f"第{para.index + 1}段：{field} 当前为「{actual}」，规范要求「{expected}」",
        paragraph_index=para.index,
        position={"format_field": field, "expected": expected},
    )


def check_format(paragraphs: list[ParagraphMeta], template: TemplateContent | None) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    if template is None:
        return issues

    body = template.body
    headings = template.headings or {}

    for para in paragraphs:
        if not para.text:
            continue  # 空段不检查

        # 标题段落优先使用对应级别规则，否则用正文规则
        rule = body
        if para.is_heading and para.heading_level is not None:
            rule = headings.get(str(para.heading_level), body)

        # 字体
        if rule.font and para.font and para.font != rule.font:
            issues.append(
                _fmt_issue(
                    para, "字体", rule.font, para.font,
                    f"将字体改为 {rule.font}",
                )
            )
        # 字号
        if rule.size_pt and para.size_pt and abs(para.size_pt - rule.size_pt) > 0.5:
            issues.append(
                _fmt_issue(
                    para, "字号", f"{rule.size_pt:g}pt", f"{para.size_pt:g}pt",
                    f"将字号改为 {rule.size_pt:g}pt",
                )
            )
        # 首行缩进
        if (
            rule.first_line_indent_chars is not None
            and para.first_line_indent_chars is not None
            and abs(para.first_line_indent_chars - rule.first_line_indent_chars) > 0.1
        ):
            issues.append(
                _fmt_issue(
                    para, "首行缩进",
                    f"{rule.first_line_indent_chars:g} 字符",
                    f"{para.first_line_indent_chars:g} 字符",
                    f"设置首行缩进 {rule.first_line_indent_chars:g} 字符",
                )
            )
        # 行距（固定磅值优先比较）
        if rule.line_spacing_pt and para.line_spacing_pt and abs(para.line_spacing_pt - rule.line_spacing_pt) > 0.5:
            issues.append(
                _fmt_issue(
                    para, "行距", f"固定 {rule.line_spacing_pt:g} 磅", f"{para.line_spacing_pt:g} 磅",
                    f"设置固定行距 {rule.line_spacing_pt:g} 磅",
                )
            )
        elif rule.line_spacing and para.line_spacing and abs(para.line_spacing - rule.line_spacing) > 0.05:
            issues.append(
                _fmt_issue(
                    para, "行距", f"{rule.line_spacing:g} 倍", f"{para.line_spacing:g} 倍",
                    f"设置行距 {rule.line_spacing:g} 倍",
                )
            )
        # 对齐方式
        if rule.alignment and para.alignment and para.alignment != rule.alignment:
            issues.append(
                _fmt_issue(
                    para, "对齐方式",
                    _ALIGN_LABEL.get(rule.alignment, rule.alignment),
                    _ALIGN_LABEL.get(para.alignment, para.alignment),
                    f"设置为{align_label(rule.alignment)}",
                )
            )
        # 标题加粗
        if para.is_heading and rule.bold is True and para.bold is False:
            issues.append(_fmt_issue(para, "加粗", "加粗", "未加粗", "将标题加粗"))

    return issues


def align_label(value: str | None) -> str:
    return _ALIGN_LABEL.get(str(value), str(value))
