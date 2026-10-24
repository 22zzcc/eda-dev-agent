# -*- coding: utf-8 -*-
"""
mcp/client.py —— MCP 客户端（子进程 stdio + 进程内两种模式）
=============================================================

Agent 通过 MCP 客户端调用 EDA 工具，与工具链解耦：
    - subprocess：spawn `python -m mcp.server` 走标准 MCP stdio 协议（真 MCP 对接）；
    - inproc     ：进程内直连工具箱（演示/测试，免子进程开销）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from eda.mock_tools import EDAToolbox

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class MCPClient:
    """MCP 客户端：list_tools() / call_tool(name, args)。"""

    def __init__(self, mode: str = "inproc"):
        self.mode = mode
        self._proc = None
        if mode == "subprocess":
            self._proc = subprocess.Popen(
                [sys.executable, "-m", "mcp.server"],
                cwd=_PROJECT_ROOT, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, text=True, bufsize=1)
            self._request({"method": "initialize", "params": {}})
        else:
            self._toolbox = EDAToolbox()

    # ---- 子进程模式：JSON-RPC over stdio ----
    def _request(self, req: dict, req_id: int = 1) -> dict:
        req["id"] = req.get("id", req_id)
        req["jsonrpc"] = "2.0"
        self._proc.stdin.write(json.dumps(req) + "\n")
        self._proc.stdin.flush()
        resp = json.loads(self._proc.stdout.readline())
        if "error" in resp:
            raise RuntimeError(resp["error"])
        return resp.get("result", {})

    def list_tools(self) -> list[str]:
        if self.mode == "subprocess":
            r = self._request({"method": "tools/list"})
            return [t["name"] for t in r.get("tools", [])]
        return list(self._toolbox.registry().keys())

    def call_tool(self, name: str, args: dict | None = None) -> dict:
        """调用工具，返回 {ok, report, metrics}。"""
        args = args or {}
        if self.mode == "subprocess":
            r = self._request({"method": "tools/call",
                               "params": {"name": name, "arguments": args}})
            text = r["content"][0]["text"]
            return json.loads(text)
        # 进程内模式：直连工具箱
        fn = self._toolbox.registry()[name]
        result = fn(**args)
        return result.to_dict()

    def close(self) -> None:
        if self._proc:
            self._proc.terminate()
