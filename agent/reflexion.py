# -*- coding: utf-8 -*-
"""
agent/reflexion.py —— Reflexion 反思节点（自我批判 + 失败归因）
================================================================

对应 JD「Reflexion 范式」。执行完一轮后，反思节点做自我批判：
    1. 找出首轮失败的阶段、修复动作、复检结果；
    2. 判断是否还有「未解决」的问题（无修复动作或修复后仍失败）；
    3. 生成反思文本，供工作流决定「重规划」还是「进入报告」。
"""
from __future__ import annotations


class Reflector:
    def reflect(self, task: str, results: dict) -> dict:
        issues, fixed = [], []
        for stage, r in results.items():
            ok = r["result"]["ok"]
            if ok and r.get("fixed"):
                fixed.append(stage)          # 首轮失败但已修复
            elif not ok:
                issues.append(stage)         # 仍失败（未解决）

        reflection = self._compose(task, issues, fixed)
        return {"reflection": reflection, "issues": issues,
                "fixed": fixed, "need_fix": len(issues) > 0}

    @staticmethod
    def _compose(task: str, issues: list[str], fixed: list[str]) -> str:
        parts = [f"任务「{task}」反思："]
        if fixed:
            parts.append("首轮失败但已通过修复动作解决的阶段："
                         + "、".join(fixed) + "。")
        if issues:
            parts.append("仍存在未解决问题的阶段：" + "、".join(issues)
                         + "（需重规划或人工介入）。")
        if not issues and not fixed:
            parts.append("首轮全部通过，无需修复。")
        if not issues:
            parts.append("结论：流程可收敛，进入签核报告。")
        return "".join(parts)
