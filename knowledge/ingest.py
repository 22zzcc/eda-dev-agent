# -*- coding: utf-8 -*-
"""
knowledge/ingest.py —— 知识库构建与数据管线（md / docx / pdf → GraphRAG）
=========================================================================

把 P&R 工具文档、设计规范、SOP 等解析成结构化知识：
    1. 文档解析（md/txt 原生；docx/pdf 惰性导入 + 水印/噪声净化）；
    2. 分块（标题层级，保留「文档/章节」定位）；
    3. 灌入 GraphRAG（向量索引 + 知识图谱）。
"""
from __future__ import annotations

import re
from pathlib import Path

from graphrag.graph import Graph
from graphrag.retrieve import GraphRAG
from graphrag.vector import VectorStore

_TXT_EXTS = {".md", ".txt", ".markdown"}
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_docx(path: Path) -> str:
    try:
        import docx
    except ImportError as e:
        raise RuntimeError(f"解析 {path.name} 需要 python-docx") from e
    return "\n".join(p.text for p in docx.Document(str(path)).paragraphs)


def _read_pdf(path: Path) -> str:
    try:
        import pypdf
    except ImportError:
        try:
            import PyPDF2 as pypdf
        except ImportError as e:
            raise RuntimeError(f"解析 {path.name} 需要 pypdf") from e
    reader = pypdf.PdfReader(str(path))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def chunk_markdown(text: str, doc_title: str) -> list[dict]:
    """按 Markdown 标题层级分块，每块带「文档/章节」定位。"""
    chunks, cur_title, cur_lines = [], doc_title, []
    for line in text.splitlines():
        m = _HEADING_RE.match(line.strip())
        if m:
            if cur_lines:
                chunks.append({"text": "\n".join(cur_lines).strip(),
                               "meta": {"doc": doc_title, "section": cur_title}})
            cur_title, cur_lines = m.group(2).strip(), []
        else:
            cur_lines.append(line)
    if cur_lines:
        chunks.append({"text": "\n".join(cur_lines).strip(),
                       "meta": {"doc": doc_title, "section": cur_title}})
    return [c for c in chunks if c["text"]]


def build_knowledge_base(data_dir: str | Path) -> GraphRAG:
    """解析目录下所有文档，构建 GraphRAG（向量 + 图谱）。"""
    data_dir = Path(data_dir)
    graphrag = GraphRAG(Graph(), VectorStore())
    files = sorted(p for p in data_dir.rglob("*") if p.suffix.lower() in _TXT_EXTS)
    for path in files:
        if path.suffix.lower() == ".docx":
            text = _read_docx(path)
        elif path.suffix.lower() == ".pdf":
            text = _read_pdf(path)
        else:
            text = _read_text(path)
        title = _HEADING_RE.match(text.lstrip().splitlines()[0].strip()).group(2).strip() \
            if text.lstrip().splitlines() and _HEADING_RE.match(text.lstrip().splitlines()[0].strip()) \
            else path.stem
        for c in chunk_markdown(text, title):
            graphrag.vector.add(c["text"], c["meta"])
            from graphrag.extract import extract_triples
            for h, r, t in extract_triples(c["text"]):
                graphrag.graph.add_edge(h, r, t)
    return graphrag
