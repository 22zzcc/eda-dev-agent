# -*- coding: utf-8 -*-
"""
graphrag/vector.py —— 向量检索（轻量实现，生产可换 Milvus/FAISS/ChromaDB）
==========================================================================

向量检索 = 语义相似召回。这里用一个**确定性哈希 embedding**（字符 n-gram 散列到
固定维 + L2 归一化）做离线演示，接口与生产向量库一致：

    add(texts) / search(query, top_k)

生产落地时，把 embedder 换成 BGE（sentence-transformers / Ollama），把存储换成
Milvus / FAISS / ChromaDB，调用方（GraphRAG 检索器）零改动——这就是「接口化」。
"""
from __future__ import annotations

import hashlib
import math
import re

try:
    import numpy as _np
except Exception:  # pragma: no cover
    _np = None

DIM = 512
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _ngrams(text: str, n: int = 2) -> list[str]:
    """字符 n-gram（含单字），中文/英文通用。"""
    t = text.lower()
    toks = list(t)
    grams = toks[:]
    for i in range(len(toks) - n + 1):
        grams.append("".join(toks[i:i + n]))
    return grams


class HashingEmbedder:
    """确定性哈希 embedding：n-gram 散列到 DIM 维，L2 归一化。"""

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * DIM
        for g in _ngrams(text):
            idx = int(hashlib.md5(g.encode("utf-8")).hexdigest(), 16) % DIM
            vec[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))  # 已归一化，点积即余弦


class VectorStore:
    """向量存储：add 文本、search top-k。"""

    def __init__(self, embedder: HashingEmbedder | None = None):
        self.embedder = embedder or HashingEmbedder()
        self.chunks: list[dict] = []
        self.vecs: list[list[float]] = []

    def add(self, text: str, meta: dict) -> None:
        self.chunks.append({"text": text, "meta": meta})
        self.vecs.append(self.embedder.embed(text))

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not self.vecs:
            return []
        qv = self.embedder.embed(query)
        scored = sorted(
            ((_cosine(qv, v), i) for i, v in enumerate(self.vecs)),
            reverse=True)
        return [{"chunk": self.chunks[i], "score": round(s, 4)}
                for s, i in scored[:top_k]]

    def __len__(self):
        return len(self.chunks)
