#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib


def main() -> int:
    parser = argparse.ArgumentParser(description="将就绪检查 JSON 渲染为 Markdown")
    parser.add_argument("readiness")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    data = json.loads(pathlib.Path(args.readiness).read_text(encoding="utf-8"))
    s = data["summary"]
    lines = [
        f"# 测试就绪检查 — {data['suite_id']}", "",
        f"**运行上下文：** `{data['context_id']}`", "",
        "## 汇总", "",
        f"- Case 总数：{s['total']}",
        f"- 可直接执行：{s['ready']}",
        f"- 可自动准备后执行：{s['provisionable']}",
        f"- 当前阻塞：{s['blocked']}",
        f"- 需求待澄清：{s['needs_clarification']}", "",
    ]

    if data.get("aggregated_gaps"):
        lines += ["## 待处理条件", ""]
        for gap in data["aggregated_gaps"]:
            lines.append(f"### `{gap['category']}:{gap['name']}` — {gap['resolution']}")
            lines.append("")
            lines.append(gap["reason"])
            lines.append("")
            lines.append("影响 Case：" + ", ".join(f"`{x}`" for x in gap["affected_case_ids"]))
            if gap.get("provisioner_ids"):
                lines.append("")
                lines.append("可用 Provisioner：" + ", ".join(f"`{x}`" for x in gap["provisioner_ids"]))
            lines.append("")

    lines += ["## Case 状态", ""]
    for row in data["case_readiness"]:
        lines.append(f"- `{row['case_id']}`：**{row['status']}**")

    pathlib.Path(args.out).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
