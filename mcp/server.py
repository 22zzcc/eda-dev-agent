# -*- coding: utf-8 -*-
"""
mcp/server.py —— MCP 服务器（stdio JSON-RPC，暴露 EDA 工具）
=============================================================

把 EDA 工具封装成 MCP（Model Context Protocol）工具，供任何 MCP 客户端调用。
这就是「MCP 工具开发，与业务系统及 EDA 工具链深度链接」的落点。

MCP 核心：一个 JSON-RPC 2.0 over stdio 的服务端，暴露三个方法：
    initialize   —— 握手，返回能力声明；
    tools/list   —— 列出可用工具 + 参数 schema；
    tools/call   —— 调用工具，返回结果。
"""
from __future__ import annotations

import json
import sys

from eda.mock_tools import EDAToolbox

# 工具 → 参数 schema（MCP inputSchema 格式）
TOOLS_SCHEMA = {
    "floorplan": {"core_util": "float=0.7 利用率", "macros": "int=4 宏单元数"},
    "place": {"cells": "int=500000 标准单元数"},
    "cts": {}, "route": {}, "sta": {}, "drc": {}, "ir_drop": {},
    "opt_design": {}, "fix_drc": {},
}


class MCPServer:
    """MCP 服务端：持有 EDA 工具箱，处理 JSON-RPC 请求。"""

    def __init__(self, toolbox: EDAToolbox | None = None):
        self.toolbox = toolbox or EDAToolbox()
        self.registry = self.toolbox.registry()

    def handle(self, req: dict) -> dict:
        method = req.get("method")
        req_id = req.get("id")
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": req_id, "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "eda-dev-agent", "version": "0.1.0"}}}
        if method == "tools/list":
            tools = [{"name": n, "description": f"EDA 工具 {n}",
                      "inputSchema": {"type": "object",
                                      "properties": {k: {"type": "string"} for k in v}}}
                     for n, v in TOOLS_SCHEMA.items()]
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}
        if method == "tools/call":
            params = req.get("params", {})
            name = params.get("name", "")
            args = params.get("arguments", {})
            return self._call(name, args, req_id)
        return {"jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601, "message": f"未知方法 {method}"}}

    def _call(self, name: str, args: dict, req_id):
        fn = self.registry.get(name)
        if fn is None:
            return {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32602, "message": f"未知工具 {name}"}}
        try:
            # 把字符串参数转成数值（MCP 参数经 JSON 传来常是字符串）
            cast = {k: (float(v) if "." in str(v) else int(v))
                    if isinstance(v, str) and str(v).replace(".", "", 1).isdigit()
                    else v for k, v in args.items()}
            result = fn(**cast)
            return {"jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text",
                                            "text": json.dumps(result.to_dict(),
                                                               ensure_ascii=False)}],
                               "isError": not result.ok}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32000, "message": str(e)}}

    def run_stdio(self) -> None:
        """标准 MCP 传输：从 stdin 逐行读 JSON-RPC，响应写 stdout。"""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError:
                continue
            sys.stdout.write(json.dumps(self.handle(req)) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    MCPServer().run_stdio()
