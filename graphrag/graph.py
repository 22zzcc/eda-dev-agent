# -*- coding: utf-8 -*-
"""
graphrag/graph.py —— 图存储（邻接表实现，生产可换 Neo4j/ArangoDB）
==================================================================

知识图谱的存储与查询：节点（实体）+ 边（关系）。用邻接表做轻量实现，
提供邻居查询与两跳路径查询，接口与图数据库一致，生产可无缝换 Neo4j/ArangoDB。
"""
from __future__ import annotations

from collections import defaultdict, deque


class Graph:
    """有向知识图谱：{head: [(relation, tail), ...]}。"""

    def __init__(self):
        self.adj: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self.nodes: set[str] = set()

    def add_edge(self, head: str, relation: str, tail: str) -> None:
        self.adj[head].append((relation, tail))
        self.nodes.add(head)
        self.nodes.add(tail)

    def neighbors(self, node: str) -> list[tuple[str, str]]:
        """某个实体的一跳邻居 [(relation, tail)]。"""
        return self.adj.get(node, [])

    def subgraph(self, node: str, depth: int = 2) -> list[str]:
        """某个实体 depth 跳内的子图节点（BFS），用于图谱上下文构建。"""
        seen, q = {node}, deque([(node, 0)])
        while q:
            cur, d = q.popleft()
            if d >= depth:
                continue
            for rel, nxt in self.adj.get(cur, []):
                if nxt not in seen:
                    seen.add(nxt)
                    q.append((nxt, d + 1))
        return sorted(seen)

    def to_triples(self) -> list[tuple[str, str, str]]:
        return [(h, r, t) for h in self.adj for r, t in self.adj[h]]

    def __len__(self):
        return len(self.nodes)
