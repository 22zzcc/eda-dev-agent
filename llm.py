# -*- coding: utf-8 -*-
"""
llm.py —— 本地模型接口（Ollama + 规则降级）
===========================================

EDA Dev Agent 里，LLM 只做「增强」，不是「必需」：任务规划、实体抽取、反思都先走
规则层，LLM 作为兜底/精化。这样离线也能完整跑通（面试现场最稳）。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = "qwen3:4b"


class LLMError(RuntimeError):
    pass


class LLM:
    def __init__(self, model: str = MODEL, url: str = OLLAMA_URL, enabled: bool = True):
        self.model, self.url, self.enabled = model, url, enabled

    def complete(self, prompt: str, json_mode: bool = True, temperature: float = 0.1) -> str:
        if not self.enabled:
            raise LLMError("LLM 未启用（离线规则模式）")
        payload = {"model": self.model, "prompt": prompt, "stream": False,
                   "options": {"temperature": temperature}}
        if json_mode:
            payload["format"] = "json"
        req = urllib.request.Request(f"{self.url}/api/generate",
                                     data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                body = json.loads(r.read().decode())
        except urllib.error.URLError as e:
            raise LLMError(f"无法连接 Ollama：{e}") from e
        return (body.get("response") or "").strip()

    def json(self, prompt: str) -> dict:
        """要求 JSON 输出并解析；失败抛错（上层降级到规则）。"""
        raw = self.complete(prompt, json_mode=True)
        s, e = raw.find("{"), raw.rfind("}")
        return json.loads(raw[s:e + 1] if s != -1 and e > s else raw)
