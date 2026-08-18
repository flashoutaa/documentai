"""全流程冒烟测试（上传 → 审查 → 建议 → 处理 → 导出）。

运行：.venv/bin/python -m app.scripts.smoke_test
依赖 mock 模式（无需 API Key）。
"""
from __future__ import annotations

import json
import sys

from fastapi.testclient import TestClient

from app.main import app
from app.scripts.make_sample_docx import build_sample


def main() -> int:
    sample_path = build_sample()
    failures: list[str] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        mark = "PASS" if cond else "FAIL"
        print(f"[{mark}] {name}" + (f"  {detail}" if detail else ""))
        if not cond:
            failures.append(name)

    with TestClient(app) as client:
        # 1. 健康检查
        r = client.get("/health")
        check("health", r.status_code == 200, r.text[:80])

        # 2. 默认模板与内置词库
        templates = client.get("/api/v1/templates").json()
        terms = client.get("/api/v1/terms").json()
        check("seed 默认模板", len(templates) >= 1, f"templates={len(templates)}")
        check("seed 内置词库", len(terms) >= 7, f"terms={len(terms)}")

        # 3. 上传文档
        with open(sample_path, "rb") as f:
            r = client.post(
                "/api/v1/documents/upload",
                files={"file": ("sample.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                data={"template_id": templates[0]["id"]},
            )
        check("上传文档", r.status_code == 200, r.text[:200])
        doc = r.json()
        doc_id = doc["id"]

        # 4. 创建审查任务（四类全开）
        r = client.post(
            "/api/v1/tasks",
            json={"document_id": doc_id, "review_types": ["typo", "format", "term", "polish"]},
        )
        check("创建任务", r.status_code == 200, r.text[:200])
        task = r.json()
        task_id = task["id"]

        # 5. 任务状态（BackgroundTasks 同步执行完）
        r = client.get(f"/api/v1/tasks/{task_id}")
        check("任务完成", r.status_code == 200 and r.json()["status"] == "completed", r.text[:300])

        # 6. 建议清单
        r = client.get(f"/api/v1/suggestions?task_id={task_id}")
        sugs = r.json()
        check("产生建议", len(sugs) >= 5, f"suggestions={len(sugs)}")
        by_type: dict[str, int] = {}
        for s in sugs:
            by_type[s["review_type"]] = by_type.get(s["review_type"], 0) + 1
        print("     类型分布:", by_type)
        for t in ("typo", "format", "term", "polish"):
            check(f"建议类型[{t}]", by_type.get(t, 0) >= 1, f"{by_type.get(t, 0)} 条")

        # 7. 处理建议：接受错别字 / 拒绝1条格式 / 自行修改1条句意 / 其余批量接受
        for sid in [s["id"] for s in sugs if s["review_type"] == "typo"]:
            r = client.patch(f"/api/v1/suggestions/{sid}", json={"status": "accepted"})
            check(f"接受建议 {sid}", r.status_code == 200, r.text[:120])
        reject_id = next(s["id"] for s in sugs if s["review_type"] == "format")
        r = client.patch(f"/api/v1/suggestions/{reject_id}", json={"status": "rejected"})
        check("拒绝格式建议", r.status_code == 200)
        modify_sug = next(s for s in sugs if s["review_type"] == "polish")
        r = client.patch(
            f"/api/v1/suggestions/{modify_sug['id']}",
            json={"status": "modified", "modified_text": "进一步加强管理"},
        )
        check("自行修改建议", r.status_code == 200)
        r = client.post(f"/api/v1/suggestions/batch?task_id={task_id}", json={"status": "accepted"})
        check("批量接受其余建议", r.status_code == 200 and r.json()["updated"] >= 1, r.text[:120])

        # 8. 导出修订版
        r = client.post(f"/api/v1/tasks/{task_id}/export")
        check("导出修订版", r.status_code == 200 and r.content[:2] == b"PK", f"bytes={len(r.content)}")
        export_path = None
        if r.status_code == 200:
            export_path = f"data/exports/task_{task_id}_sample_审查修订版.docx"
            with open(export_path, "wb") as f:
                f.write(r.content)

        # 9. 校验导出内容
        # mock 模式输出确定，可严格断言；LLM 模式输出非确定（整句重写），
        # 断言"错误形式已消除"与流程完整性
        if export_path:
            from app.core.config import settings as app_settings
            from app.services.docx_parser import parse_docx

            parsed = parse_docx(export_path)
            full_text = "\n".join(p.text for p in parsed.paragraphs)
            strict = app_settings.LLM_PROVIDER == "mock"

            check("导出错别字已修复", "必段" not in full_text and "举形" not in full_text)
            check("导出词补全(两个百年已消除)", "两个百年" not in full_text)
            # '特色社会主义' 是 '中国特色社会主义' 的子串，用带上下文的短语判断
            check(
                "导出词补全(特色社会主义已消除)",
                "按照特色社会主义" not in full_text,
            )
            if strict:
                check("导出含 两个一百年", "两个一百年" in full_text)
                check("导出含 优化后句式", "加强管理" in full_text)
            check("导出不含 非常非常(优化生效)", "非常非常" not in full_text)

    print("\n" + ("=" * 40))
    if failures:
        print(f"冒烟测试失败 {len(failures)} 项: {failures}")
        return 1
    print("冒烟测试全部通过 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
