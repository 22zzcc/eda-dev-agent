# -*- coding: utf-8 -*-
"""
eda/mock_tools.py —— 模拟 EDA 工具（P&R 各阶段的确定性结果）
=============================================================

没有真实 EDA 工具环境时，用「行为一致的 mock」演示 Agent 与工具链的对接。
每个工具返回结构化报告 + pass/fail 信号，Agent 据此决策（Reflexion 靠这个信号）。

真实落地时，把这里的实现替换成对真实工具的调用即可（TCL 脚本 / OpenROAD Python API /
Innovus/ICC2 的远程命令），接口不变——这就是「Agent 与传统 EDA 流程/脚本高效对接」的
接口化思路。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class ToolResult:
    """一次 EDA 工具调用的结果。"""
    tool: str
    ok: bool                      # 是否通过（DRC/STA 的 pass/fail）
    report: str                   # 人类可读报告
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"tool": self.tool, "ok": self.ok, "report": self.report,
                "metrics": self.metrics}


# ---------------------------------------------------------------------------
# 确定性 mock：同一输入同一输出（便于演示 Reflexion 的「失败→修复→通过」闭环）
# ---------------------------------------------------------------------------
class EDAToolbox:
    """一组模拟的数字后端 P&R 工具（有状态：记录了是否做过优化）。"""

    def __init__(self, design: str = "demo_block", node: str = "7nm",
                 clock_period_ns: float = 1.0):
        self.design = design
        self.node = node
        self.clock_period_ns = clock_period_ns
        self.opt_done = False       # 是否做过时序优化（决定 STA 是否收敛）
        self.drc_fixed = False      # 是否修过 DRC

    # ---- P&R 各阶段 ----
    def floorplan(self, core_util: float = 0.7, macros: int = 4) -> ToolResult:
        area = round(1.0 / core_util * 0.8, 2)   # 反推面积，纯演示
        return ToolResult("floorplan", True,
                          f"[floorplan] {self.design} @ {self.node}：core 面积 {area}mm²，"
                          f"宏单元 {macros} 个已摆放。",
                          {"core_area_mm2": area, "macros": macros})

    def place(self, cells: int = 500_000) -> ToolResult:
        util = 0.72
        return ToolResult("place", True,
                          f"[place] 标准单元 {cells} 个已布局，利用率 {util:.0%}。",
                          {"cells": cells, "utilization": util})

    def cts(self) -> ToolResult:
        return ToolResult("cts", True,
                          "[cts] 时钟树综合完成：32 级，skew 45ps。",
                          {"levels": 32, "skew_ps": 45})

    def route(self) -> ToolResult:
        return ToolResult("route", True,
                          "[route] 布线完成：金属层 M1~M5，wire 长度 8.2m。",
                          {"metal_layers": "M1-M5", "wirelen_m": 8.2})

    def sta(self) -> ToolResult:
        """静态时序分析：setup 是否收敛取决于是否做过 opt_design。"""
        if not self.opt_done:
            return ToolResult("sta", False,
                              "[sta] ⚠ setup 违例：WNS -0.12ns，TNS -1.8ns（需优化时序）。",
                              {"wns_ns": -0.12, "tns_ns": -1.8, "hold_ok": True})
        return ToolResult("sta", True,
                          "[sta] ✅ 时序收敛：WNS +0.05ns，hold +0.02ns。",
                          {"wns_ns": 0.05, "tns_ns": 0.0, "hold_ok": True})

    def drc(self) -> ToolResult:
        """设计规则检查：金属间距违例需 fix_drc。"""
        if not self.drc_fixed:
            return ToolResult("drc", False,
                              "[drc] ⚠ 金属间距违例 3 处（M2/M3）。",
                              {"violations": 3, "layers": ["M2", "M3"]})
        return ToolResult("drc", True, "[drc] ✅ 0 违例。", {"violations": 0})

    def ir_drop(self) -> ToolResult:
        drop = 0.045 if self.opt_done else 0.062
        ok = drop < 0.05
        return ToolResult("ir_drop", ok,
                          f"[ir_drop] 最大压降 {drop*100:.2f}%（阈值 5%）"
                          f"{'' if ok else ' ⚠ 超标'}。",
                          {"max_drop": drop})

    # ---- 修复动作 ----
    def opt_design(self) -> ToolResult:
        """时序优化（等价于 Innovus optDesign / OpenROAD repair_timing）。"""
        self.opt_done = True
        return ToolResult("opt_design", True, "[opt_design] 时序优化完成（插 buffer/调整 size）。")

    def fix_drc(self) -> ToolResult:
        self.drc_fixed = True
        return ToolResult("fix_drc", True, "[fix_drc] 已修复金属间距违例（detail route 局部重绕）。")

    # ---- 工具注册表（供 MCP / Agent 调度）----
    def registry(self) -> dict[str, callable]:
        return {
            "floorplan": self.floorplan, "place": self.place, "cts": self.cts,
            "route": self.route, "sta": self.sta, "drc": self.drc,
            "ir_drop": self.ir_drop, "opt_design": self.opt_design,
            "fix_drc": self.fix_drc,
        }
