# -*- coding: utf-8 -*-
"""
agent/graph.py —— Agent 工作流状态图（LangGraph 风格：节点 + 条件边）
=====================================================================

对应 JD「Agent 工作流设计 / LangGraph」。把 Agent 工作流建模成有向图：

        ┌──────┐   plan   ┌─────────┐   execute   ┌──────────┐
    start ──►│ plan │──────►│ execute │───────────►│ reflect  │
             └──────┘       └─────────┘            └────┬─────┘
                                                        │ reflect 判定
                                    need_fix=False ─────┼─────► report → end
                                    need_fix=True  ─────┘（回到 plan 重规划，上限 max_iters）

每个节点 = 一个纯函数：读 state、写 state；边 = 状态转移。这是 LangGraph 的
「StateGraph + 条件边」思想的轻量实现，演示「任务规划→工具调度→反思→重规划」闭环。
"""
from __future__ import annotations

from .planner import Planner
from .react import ReActExecutor
from .reflexion import Reflector


class AgentGraph:
    """P&R Agent 工作流状态图。"""

    def __init__(self, planner: Planner, executor: ReActExecutor,
                 reflector: Reflector, max_iters: int = 2):
        self.planner = planner
        self.executor = executor
        self.reflector = reflector
        self.max_iters = max_iters

    # ---- 节点 ----
    def _plan_node(self, state: dict) -> dict:
        state["plan"] = self.planner.plan(state["task"])
        return state

    def _execute_node(self, state: dict) -> dict:
        state["results"] = self.executor.run(state["plan"])
        return state

    def _reflect_node(self, state: dict) -> dict:
        r = self.reflector.reflect(state["task"], state["results"])
        state["reflection"] = r["reflection"]
        state["need_fix"] = r["need_fix"]
        state["fixed"] = r["fixed"]
        return state

    def _report_node(self, state: dict) -> dict:
        lines = [f"任务：{state['task']}"]
        for stage, r in state["results"].items():
            mark = "✅" if r["result"]["ok"] else "❌"
            lines.append(f"  {mark} {stage}: {r['result']['report']}")
        lines.append("反思：" + state["reflection"])
        state["report"] = "\n".join(lines)
        return state

    # ---- 运行（节点 + 条件边） ----
    def run(self, task: str) -> dict:
        state = {"task": task}
        for _ in range(self.max_iters):
            self._plan_node(state)
            self._execute_node(state)
            self._reflect_node(state)
            if not state["need_fix"]:
                break
            # need_fix=True → 条件边回到 plan，用反思作为额外约束重规划
            state["task"] = task + "（上一轮未解决：" + ",".join(state["issues"] if "issues" in state else []) + "）"
        self._report_node(state)
        return state
