# -*- coding: utf-8 -*-
"""
graphrag/extract.py —— 实体与关系抽取（规则优先，LLM 可选精化）
================================================================

从 P&R 文档里抽 (head, relation, tail) 三元组，构建知识图谱。
规则层离线可跑；LLM 层做精化（可选）。

EDA 领域的实体/关系设计：
    - 实体：工具（OpenROAD/Innovus/ICC2/TritonRoute）、阶段（floorplan/…/sta/drc）、
            指标（clock_period/utilization/wns/drc_violation）、违例类型（DRC/LVS/IR Drop）。
    - 关系：uses（阶段→工具）、produces（阶段→报告/指标）、checks（阶段→违例类型）、
            before（阶段→阶段，流程依赖）。
"""
from __future__ import annotations

import re

# 领域词典：实体类型 → 关键词（匹配大小写不敏感）
ENTITIES = {
    "tool": ["OpenROAD", "Innovus", "ICC2", "TritonRoute", "Yosys", "Magic"],
    "stage": ["floorplan", "placement", "cts", "clock tree", "routing", "route",
              "sta", "静态时序", "drc", "设计规则", "ir drop", "signoff", "签核"],
    "metric": ["clock_period", "utilization", "利用率", "wns", "tns", "skew",
               "congestion", "拥塞", "drc violation", "setup", "hold"],
    "violation": ["drc", "lvs", "ir drop", "congestion", "timing", "时序违例"],
}


def extract_entities(text: str) -> dict[str, list[str]]:
    """从文本抽取实体（按词典），返回 {类型: [实体名]}。"""
    found = {k: [] for k in ENTITIES}
    lower = text.lower()
    for etype, kws in ENTITIES.items():
        for kw in kws:
            if kw in lower:
                found[etype].append(kw)
    return {k: sorted(set(v)) for k, v in found.items() if v}


def extract_triples(text: str) -> list[tuple[str, str, str]]:
    """从文本抽取 (head, relation, tail) 三元组（规则层）。"""
    ents = extract_entities(text)
    triples: list[tuple[str, str, str]] = []

    # 关系1：阶段 → uses → 工具（同一句话里同时出现 stage 与 tool）
    for st in ents.get("stage", []):
        for tool in ents.get("tool", []):
            triples.append((st, "uses", tool))

    # 关系2：阶段 → checks → 违例类型
    for st in ents.get("stage", []):
        for vio in ents.get("violation", []):
            triples.append((st, "checks", vio))

    # 关系3：阶段 → produces → 指标
    for st in ents.get("stage", []):
        for m in ents.get("metric", []):
            triples.append((st, "produces", m))

    # 关系4：P&R 流程依赖（阶段 → before → 阶段），按标准顺序
    order = [s for s in ["floorplan", "placement", "cts", "routing", "sta", "drc"]
             if s in [e for e in ents.get("stage", [])] or s in text.lower()]
    for i in range(len(order) - 1):
        triples.append((order[i], "before", order[i + 1]))

    return _dedup(triples)


def _dedup(triples: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    return list(dict.fromkeys(triples))


def extract_with_llm(text: str, llm=None) -> list[tuple[str, str, str]]:
    """LLM 精化抽取（可选）：规则层兜底 + LLM 补充。"""
    triples = extract_triples(text)
    if llm is None:
        return triples
    try:
        prompt = ("从下面的 EDA 文档里抽取 (实体, 关系, 实体) 三元组，关系限 uses/checks/"
                  "produces/before，输出 JSON 数组。\n文档：\n" + text[:1500] + "\nJSON：")
        obj = llm.json(prompt)
        extra = [(t.get("head", ""), t.get("relation", ""), t.get("tail", ""))
                 for t in obj if isinstance(t, dict) and t.get("head") and t.get("tail")]
        return _dedup(triples + extra)
    except Exception:
        return triples
