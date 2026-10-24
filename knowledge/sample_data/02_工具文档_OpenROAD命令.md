# 数字后端工具命令参考

## 1. OpenROAD 命令

### 1.1 布局布线
OpenROAD 提供 floorplan、place、cts、route 等命令，分别对应布局规划、标准单元布局、时钟树综合与布线。TritonRoute 用于 detail routing。

### 1.2 时序分析
OpenROAD 集成的 STA 引擎可报告 WNS/TNS；修复时序使用 repair_timing（等价于商业工具的 optDesign）。

## 2. 商业工具对照

### 2.1 Innovus 与 ICC2
Innovus 的 place_opt / route_opt 对应布局与布线优化；ICC2 的 clock_opt 对应时钟树综合。三者流程等价，命令名不同。

### 2.2 工具选型
本 flow 默认使用 OpenROAD（开源、可脚本化），必要时切换 Innovus/ICC2 商业工具。
