# DRC 设计规则检查

## 1. 金属间距规则

### 1.1 最小间距
M2 与 M3 金属层的最小间距为 0.05um。DRC 阶段检查金属间距，违例记作 drc violation。

### 1.2 修复方式
金属间距违例通过 fix_drc（detail route 局部重绕）修复；修复后需重新跑 DRC 确认 0 违例。

## 2. 其它检查

### 2.1 LVS 与 IR Drop
除 DRC 外，还需做 LVS（版图与电路一致性）与 IR Drop 分析。IR Drop 阈值 5%，超标需优化电源网络。

### 2.2 违例归类
常见违例类型包括 drc、lvs、ir drop、congestion，均需在 signoff 前清零或达标。
