# 数字后端 P&R 流程 SOP

## 1. 标准流程

### 1.1 流程顺序
数字后端标准流程按依赖顺序执行：floorplan → placement → cts → routing → sta → drc → ir_drop → signoff。前序阶段未完成不得进入后序。

### 1.2 阶段说明
floorplan 做布局规划（core 面积、宏单元摆放）；placement 做标准单元布局；cts 做时钟树综合；routing 做布线。

## 2. 检查与签核

### 2.1 检查阶段
routing 之后进入检查阶段：sta 查时序（WNS/TNS）、drc 查设计规则、ir_drop 查压降。任一检查失败需修复后重跑。

### 2.2 签核
所有检查通过（sta 收敛、drc 0 违例、ir_drop 达标）后进入 signoff，输出 GDS 与报告。
