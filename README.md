# EDA Dev Agent · 面向数字后端 P&R 流程的 Agentic Flow

> 一句话：把数字后端的布局布线（P&R）流程封装成 **Agentic Flow**——发一句话，
> Agent 自动做**任务规划 → 子任务拆解 → ReAct 工具调度（经 MCP 对接 EDA 工具）→
> Reflexion 反思 → 签核报告**，知识检索走 **GraphRAG（向量 + 图）**。

---

## 架构

```
用户请求（"帮我跑 block 的 P&R 并检查时序收敛"）
   │
   ▼
┌─ agent/  Agent 工作流（LangGraph 风格状态图）────────────────────┐
│  planner   任务规划与子任务拆解（floorplan→place→cts→route→sta→drc→ir_drop）│
│  react     ReAct 循环：thought→action→observation，失败自动 fix+复检      │
│  reflexion Reflexion 反思：失败归因 + 决定重规划 or 报告                 │
│  graph     状态图：plan→execute→reflect→report（条件边支持回环）          │
└──────────────┬───────────────────────────────────────────────────┘
               │ 工具调度
┌──────────────▼───────────────────────────────────────────────────┐
│ mcp/  MCP 工具（Model Context Protocol）                           │
│   server   stdio JSON-RPC，暴露 EDA 工具（floorplan/…/opt_design/fix_drc）│
│   client   子进程 stdio / 进程内 两种模式                              │
└──────────────┬───────────────────────────────────────────────────┘
               │ 知识检索整合
┌──────────────▼───────────────────────────────────────────────────┐
│ graphrag/  GraphRAG（向量 + 图 融合）                              │
│   vector   向量检索（哈希 embedding，生产换 Milvus/FAISS/ChromaDB）    │
│   graph    图存储（邻接表，生产换 Neo4j/ArangoDB）                    │
│   extract  实体/关系抽取（规则 + 可选 LLM）                           │
│   retrieve 图检索 + 向量检索融合                                      │
└──────────────┬───────────────────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────────────────┐
│ knowledge/  知识库与数据管线                                        │
│   ingest   md/docx/pdf 解析 → 分块 → 构建 GraphRAG                  │
│   sample_data  时序约束/工具文档/DRC规则/流程SOP                    │
└──────────────────────────────────────────────────────────────────┘
```

## 快速开始

核心零硬依赖（LLM 走标准库 urllib；图/向量纯 Python；EDA 工具为确定性 mock）。

```bash
cd eda-dev-agent

# ① Agentic P&R Flow（离线规则模式，零 LLM）
python main.py run "帮我跑 demo_block 的数字后端 P&R 并检查时序收敛" --rule-only

# ② GraphRAG 检索（图 + 向量融合）
python main.py rag "STA 用了哪个工具？时序违例怎么修？" --rule-only

# ③ MCP 工具（inproc / subprocess 真 MCP stdio）
python main.py mcp list
python main.py run "跑 P&R" --mcp subprocess   # 真 MCP 子进程协议
```

## 对照 JD 逐条映射

| JD 要求 | 落地 |
| :--- | :--- |
| Agent 工作流设计（任务规划、子任务拆解、工具调度、知识检索整合） | `agent/`：planner 拆解 → react 调度 + GraphRAG 检索 → reflexion |
| LangChain/LangGraph Agent 系统 | `agent/graph.py` 状态图（节点+条件边），LangGraph 思想轻量实现 |
| GraphRAG、向量检索、图谱构建、知识增强 | `graphrag/`：vector + graph + extract + retrieve |
| MCP 工具与 EDA 工具链链接 | `mcp/`：server(stdio JSON-RPC) + client，EDA 工具封装为 MCP tools |
| 向量数据库 + 图数据库 | `vector.py`(可换 Milvus/FAISS/ChromaDB) + `graph.py`(可换 Neo4j/ArangoDB) |
| 文档清洗（md/pdf/docx）、数据管线 | `knowledge/ingest.py` |
| Agent 工作流范式（ReAct、Reflexion） | `agent/react.py` + `agent/reflexion.py` |
| P&R/数字后端（布局布线、时序、DRC/IR Drop/STA/Congestion） | `eda/`：flow 定义 + mock 工具（floorplan/place/cts/route/sta/drc/ir_drop/opt_design/fix_drc） |

## 设计要点（面试可讲）

- **Agent 与传统 EDA 工具对接 = 接口化**：mock 工具与真实工具（OpenROAD Python API /
  Innovus/ICC2 的 TCL/远程命令）共享同一 MCP 接口，换后端不换 Agent。
- **ReAct + Reflexion 闭环**：sta 首轮违例 → opt_design → 复检通过；drc 违例 → fix_drc →
  复检通过；reflexion 记录「首轮失败但已修复」并给出签核结论。
- **GraphRAG 的价值**：向量检索答「语义相似」，图检索答「关系型问题」
  （sta → uses → 工具、routing → produces → setup/hold），二者融合覆盖两类查询。
- **LangGraph 风格状态图**：plan→execute→reflect→report 节点化，条件边支持「反思→重规划」
  回环，便于扩展更多节点（如多 Agent 协作、长上下文执行）。

## 参考项目（GitHub）

- OpenROAD：https://github.com/The-OpenROAD-Project/OpenROAD
- LangGraph：https://github.com/langchain-ai/langgraph
- Milvus：https://github.com/milvus-io/milvus
- Neo4j：https://github.com/neo4j/neo4j
