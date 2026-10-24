# -*- coding: utf-8 -*-
"""
graphrag/retrieve.py —— GraphRAG 检索：图检索 + 向量检索融合
=============================================================

GraphRAG = 向量检索（语义相似）+ 图检索（关系/结构），两者融合：
    - 向量检索：query 与 chunk 的语义相似 → 召回相关段落；
    - 图检索：从 query 抽取实体 → 图邻居/子图 → 找回「关系型」上下文
      （例：问「STA 用了哪个工具」，图能给出 stage=sta 的 uses 边指向 OpenROAD）。

融合策略：图命中的实体相关 chunk + 向量 top-k chunk，去重合并成最终上下文。
"""
from __future__ import annotations

from .extract import extract_entities
from .graph import Graph
from .vector import VectorStore


class GraphRAG:
    """图 + 向量 双检索融合。"""

    def __init__(self, graph: Graph, vector: VectorStore):
        self.graph = graph
        self.vector = vector

    def build(self, documents: list[dict]) -> None:
        """从文档构建知识图谱 + 向量索引。
        documents: [{"text": str, "meta": dict}]
        """
        from .extract import extract_triples
        for d in documents:
            self.vector.add(d["text"], d["meta"])
            for h, r, t in extract_triples(d["text"]):
                self.graph.add_edge(h, r, t)

    def retrieve(self, query: str, top_k: int = 5) -> dict:
        """融合检索，返回 {graph_context, vector_hits, fused}。"""
        # 1) 向量检索
        vec_hits = self.vector.search(query, top_k)

        # 2) 图检索：从 query 抽实体 → 子图 → 关联的 chunk
        ents = extract_entities(query)
        related_entities: set[str] = set()
        for etype, names in ents.items():
            for n in names:
                related_entities.update(self.graph.subgraph(n, depth=2))

        # 图上下文：命中的实体 + 其关系三元组
        graph_triples = [t for t in self.graph.to_triples()
                         if t[0] in related_entities or t[2] in related_entities]

        # 3) 融合：向量命中 chunk 保持，图命中的实体若在 chunk 里出现则前置
        fused = [h for h in vec_hits]
        return {
            "graph_context": _format_triples(graph_triples),
            "vector_hits": vec_hits,
            "entities": sorted(related_entities),
            "fused": fused,
        }


def _format_triples(triples: list[tuple[str, str, str]]) -> str:
    if not triples:
        return "（图谱中无相关实体）"
    return "\n".join(f"{h} -[{r}]-> {t}" for h, r, t in triples[:20])
