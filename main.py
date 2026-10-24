#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py —— EDA Dev Agent 入口
==============================

面向数字后端 P&R 流程的 Agentic Flow：任务规划 → ReAct 工具调度 → Reflexion 反思，
知识检索走 GraphRAG（向量 + 图），EDA 工具经 MCP 暴露。

用法（在项目根目录）：

    # 一句话驱动 Agentic P&R Flow（离线规则模式，零 LLM 依赖）
    python main.py run "帮我跑 demo_block 的数字后端 P&R 并检查时序收敛"

    # GraphRAG 检索演示（图 + 向量融合）
    python main.py rag "STA 用了哪个工具？时序违例怎么修？"

    # 列出 MCP 暴露的 EDA 工具
    python main.py mcp list

    # 真 MCP 协议（子进程 stdio）演示
    python main.py run "跑 P&R" --mcp subprocess
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def build(args):
    from knowledge.ingest import build_knowledge_base
    from mcp.client import MCPClient
    from agent.planner import Planner
    from agent.react import ReActExecutor
    from agent.reflexion import Reflector
    from agent.graph import AgentGraph
    from llm import LLM

    kb = build_knowledge_base(args.data)
    mcp = MCPClient(mode=args.mcp)
    llm = None if args.rule_only else LLM(enabled=True)
    graph = AgentGraph(Planner(llm), ReActExecutor(mcp, kb), Reflector())
    return graph, kb, mcp


def cmd_run(args) -> None:
    graph, kb, mcp = build(args)
    state = graph.run(args.request)

    print("=" * 70)
    print("规划的子任务（任务拆解）：")
    for st in state["plan"]:
        deps = f"（依赖 {','.join(st.deps)}）" if st.deps else ""
        print(f"  - {st.stage} [{st.tool}] {st.desc} {deps}")
    print("-" * 70)
    print("ReAct 执行轨迹：")
    for stage, r in state["results"].items():
        for s in r["steps"]:
            mark = "✓" if s.ok else "✗"
            print(f"  [{stage}] {mark} thought: {s.thought[:40]}")
            print(f"          action: {s.action}")
            print(f"          observe: {s.observation[:60]}")
    print("-" * 70)
    print("报告：")
    print(state["report"])


def cmd_rag(args) -> None:
    graph, kb, mcp = build(args)
    r = kb.retrieve(args.question)
    print("=" * 70)
    print(f"问题：{args.question}")
    print("-" * 70)
    print("图谱检索（实体关系）：")
    print(r["graph_context"])
    print(f"命中实体：{', '.join(r['entities']) or '无'}")
    print("-" * 70)
    print("向量检索 top-k：")
    for h in r["vector_hits"]:
        print(f"  [{h['score']}] {h['chunk']['meta'].get('doc','')} / "
              f"{h['chunk']['meta'].get('section','')}")
        print(f"       {h['chunk']['text'][:80]}")


def cmd_mcp(args) -> None:
    from mcp.client import MCPClient
    mcp = MCPClient(mode=args.mcp)
    print("MCP 暴露的 EDA 工具：")
    for name in mcp.list_tools():
        print(f"  - {name}")
    mcp.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="EDA Dev Agent：Agentic P&R Flow")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="运行 Agentic P&R Flow")
    p_run.add_argument("request", help="自然语言请求")
    p_run.add_argument("--data", default="knowledge/sample_data")
    p_run.add_argument("--mcp", default="inproc", choices=["inproc", "subprocess"])
    p_run.add_argument("--rule-only", action="store_true", help="离线规则模式（不加载 LLM）")
    p_run.set_defaults(func=cmd_run)

    p_rag = sub.add_parser("rag", help="GraphRAG 检索演示")
    p_rag.add_argument("question", help="问题")
    p_rag.add_argument("--data", default="knowledge/sample_data")
    p_rag.add_argument("--mcp", default="inproc", choices=["inproc", "subprocess"])
    p_rag.add_argument("--rule-only", action="store_true")
    p_rag.set_defaults(func=cmd_rag)

    p_mcp = sub.add_parser("mcp", help="MCP 工具")
    p_mcp.add_argument("action", choices=["list"])
    p_mcp.add_argument("--mcp", default="inproc", choices=["inproc", "subprocess"])
    p_mcp.set_defaults(func=cmd_mcp)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
