# -*- coding: utf-8 -*-
"""
agent/react.py —— ReAct 执行循环（thought → action → observation）
===================================================================

对应 JD「工具调度、知识检索整合」+「ReAct 范式」。每个子任务一轮 ReAct：
    1. Thought     —— 检索知识库（GraphRAG）理解该阶段要点；
    2. Action      —— 经 MCP 客户端调用对应 EDA 工具；
    3. Observation —— 观察结果；若失败且有修复动作，则 fix → 复检（再一轮）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from eda.flow import fix_action_for
from graphrag.retrieve import GraphRAG
from mcp.client import MCPClient


@dataclass
class ReActStep:
    stage: str
    thought: str
    action: str
    observation: str
    ok: bool


class ReActExecutor:
    def __init__(self, mcp: MCPClient, graphrag: GraphRAG):
        self.mcp = mcp
        self.graphrag = graphrag

    def run(self, subtasks) -> dict:
        """执行子任务序列，返回 {stage: {result, steps, fixed}}。"""
        results = {}
        for st in subtasks:
            steps: list[ReActStep] = []

            # Thought：检索知识（GraphRAG），理解该阶段约束/要点
            rag = self.graphrag.retrieve(st.stage + " " + st.desc)
            kg = rag["graph_context"]
            kg_note = "" if kg == "（图谱中无相关实体）" else f"；知识：{kg[:80]}"
            thought = f"执行 {st.stage}（{st.desc}）{kg_note}"

            # Action：经 MCP 调工具
            res = self.mcp.call_tool(st.tool)
            observation = res["report"]
            fixed = False

            # Observation：失败 → 修复动作 → 复检（ReAct 再一轮）
            if not res["ok"]:
                fix_tool = fix_action_for(st.stage)
                if fix_tool:
                    steps.append(ReActStep(st.stage, thought + "（首轮失败，触发修复）",
                                           fix_tool, "执行修复", False))
                    self.mcp.call_tool(fix_tool)
                    res = self.mcp.call_tool(st.tool)
                    observation = res["report"]
                    fixed = True

            steps.append(ReActStep(st.stage, thought, st.tool, observation, res["ok"]))
            results[st.stage] = {"result": res, "steps": steps, "fixed": fixed}
        return results
