# -*- coding: utf-8 -*-
"""
agent/planner.py —— 任务规划与子任务拆解
=========================================

把自然语言请求拆成「有依赖关系的子任务序列」（对应 JD「任务规划、子任务拆解」）。
规则层：按标准 P&R flow（eda/flow.py）拆解，并按请求关键词过滤/裁剪；
LLM 层（可选）：对非标准请求做定制拆解。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from eda.flow import build_flow


@dataclass
class SubTask:
    stage: str
    tool: str
    desc: str
    deps: list[str] = field(default_factory=list)


class Planner:
    def __init__(self, llm=None):
        self.llm = llm

    def plan(self, task: str) -> list[SubTask]:
        """把请求拆成子任务（规则优先）。"""
        # 规则层：标准 P&R flow + 关键词裁剪
        stages = [SubTask(s.name, s.tool, s.desc, s.deps) for s in build_flow()]
        plan = self._filter_by_task(stages, task)

        # LLM 层（可选）：非标准请求的定制拆解（失败则退回规则结果）
        if self.llm is not None and self._needs_custom(task):
            try:
                plan = self._llm_plan(task, plan)
            except Exception:
                pass
        return plan

    # ---- 规则层 ----
    @staticmethod
    def _filter_by_task(stages: list[SubTask], task: str) -> list[SubTask]:
        """按请求关键词裁剪：如「只跑 sta」只保留 sta 及其依赖。"""
        mentions = {s.stage for s in stages if s.stage in task.lower()}
        if not mentions:          # 没点名具体阶段 → 跑完整 flow
            return stages
        keep = set()
        for s in stages:
            if s.stage in mentions:
                keep.add(s.stage)
                keep.update(s.deps)   # 保留依赖
        return [s for s in stages if s.stage in keep]

    @staticmethod
    def _needs_custom(task: str) -> bool:
        # 规则覆盖不了的关键词（如「优化功耗」「修 congestion」）才走 LLM
        return bool(re.search(r"功耗|congestion|拥塞|优化|自定义", task))

    def _llm_plan(self, task: str, fallback: list[SubTask]) -> list[SubTask]:
        import json
        prompt = ("你是数字后端 P&R 流程规划器。把请求拆成子任务，每个含 stage/tool/desc，"
                  "输出 JSON 数组。可用工具：floorplan/place/cts/route/sta/drc/ir_drop/"
                  "opt_design/fix_drc。\n请求：" + task + "\nJSON：")
        obj = self.llm.json(prompt)
        subs = [SubTask(t.get("stage", ""), t.get("tool", ""), t.get("desc", ""))
                for t in obj if isinstance(t, dict) and t.get("tool")]
        return subs or fallback
