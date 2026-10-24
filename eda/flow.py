# -*- coding: utf-8 -*-
"""
eda/flow.py —— 数字后端 P&R 流程定义
=====================================

把「布局布线到签核」拆成可调度的子任务序列，供 Agent 规划器做任务拆解。
这是「Agentic P&R Flow」的地基：Agent 不是瞎调工具，而是按流程 + 依赖关系编排。

标准数字后端 flow（简版）：
    floorplan → placement → CTS → routing → STA → DRC → IR Drop → signoff
"""
from __future__ import annotations

from dataclasses import dataclass

# 标准 P&R 阶段 → 依赖的前置阶段
FLOW_STAGES = [
    {"stage": "floorplan", "tool": "floorplan", "desc": "布局规划：core 面积、宏单元摆放", "deps": []},
    {"stage": "placement", "tool": "place", "desc": "标准单元布局", "deps": ["floorplan"]},
    {"stage": "cts", "tool": "cts", "desc": "时钟树综合", "deps": ["placement"]},
    {"stage": "routing", "tool": "route", "desc": "布线", "deps": ["cts"]},
    {"stage": "sta", "tool": "sta", "desc": "静态时序分析（setup/hold）", "deps": ["routing"]},
    {"stage": "drc", "tool": "drc", "desc": "设计规则检查", "deps": ["routing"]},
    {"stage": "ir_drop", "tool": "ir_drop", "desc": "IR Drop 分析", "deps": ["routing"]},
]

# 修复动作（在检查失败后由 Agent 决策触发）
FIX_ACTIONS = {
    "sta": {"tool": "opt_design", "desc": "时序违例 → 时序优化（插 buffer/调 size）"},
    "drc": {"tool": "fix_drc", "desc": "DRC 违例 → 局部重绕修复"},
}


@dataclass
class Stage:
    name: str
    tool: str
    desc: str
    deps: list[str]


def build_flow() -> list[Stage]:
    return [Stage(s["stage"], s["tool"], s["desc"], s["deps"]) for s in FLOW_STAGES]


def fix_action_for(stage: str) -> str | None:
    """某阶段失败时对应的修复工具名。"""
    return FIX_ACTIONS.get(stage, {}).get("tool")
