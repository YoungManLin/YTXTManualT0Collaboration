# Claude Code 开发指南

## 📚 设计文档位置

**开发前必读**：

1. **手动 T0 实施方案** → `docs/手动 T0 实施方案.docx`
   - T0 交易整体方案
   - 仓位管理策略
   - 交易流程设计

2. **迅投 PB-DBF 参数说明** → `docs/迅投 PB-DBF 预埋单参数说明文档 V2.15.xlsx`
   - DBF 文件格式规范
   - 17 个字段定义
   - 数据格式要求

3. **项目状态** → `PROJECT_STATUS.md`
   - 当前进度
   - 待办事项
   - 下一步计划

---

## 🎯 核心概念

### 输入数据
- **CCTJ 仓位文件** (GT 系统) - 现有仓位数据
  - 真实持仓：实际持有的可卖出仓位
  - 虚拟持仓：T0 交易产生的临时仓位

### 业务逻辑
- **T0 交易**：日内交易
  - 先卖后买（融券 T0）
  - 先买后卖（融资 T0）
  - 开仓 → 平仓 → 盈亏计算

### 输出数据
- **DBF 预埋单** (迅投系统)
  - 基于仓位生成订单
  - 遵循 V2.15 规范

---

## 📋 开发顺序

### 阶段 1: 仓位管理（当前）
```python
# 1. CCTJ 文件解析
src/cctj_parser.py

# 2. 持仓数据结构
src/position.py
  - RealPosition (真实持仓)
  - VirtualPosition (虚拟持仓)
  - PositionManager (持仓管理器)
```

### 阶段 2: T0 交易
```python
# 3. T0 策略引擎
src/t0_strategy.py
  - T0OpenStrategy (开仓策略)
  - T0CloseStrategy (平仓策略)
  - SignalGenerator (信号生成)
```

### 阶段 3: 订单生成
```python
# 4. DBF 订单生成
src/order_generator.py
  - 字段映射
  - 数据验证
  - DBF 文件导出
```

### 阶段 4: 风险控制
```python
# 5. 风险控制
src/risk_manager.py
  - 仓位限额检查
  - 集中度检查
  - 止损/止盈检查
```

---

## 🔧 开发规范

### 代码风格
- Python 3.12+
- 类型注解
- 数据类优先
- 异常处理完善

### 测试要求
- 单元测试覆盖率 > 80%
- 边界条件测试
- 异常场景测试

### 提交规范
```bash
git add -A
git commit -m "feat: 实现 CCTJ 仓位文件解析

- 支持字段：[列出字段]
- 数据验证：[验证规则]
- 单元测试：[测试用例数]"
git push origin master
```

---

## ⚠️ 重要提醒

### 不要做
- ❌ 不要假设 CCTJ 文件格式（等待文档）
- ❌ 不要跳过设计文档直接编码
- ❌ 不要一次性实现多个模块
- ❌ 不要忽略数据验证

### 应该做
- ✅ 先阅读 `docs/` 下的设计文档
- ✅ 一次只实现一个模块
- ✅ 完成后立即提交
- ✅ 等待确认后再继续
- ✅ 有疑问先问，不要猜测

---

## 📝 常用命令

### 查看项目状态
```bash
cat PROJECT_STATUS.md
```

### 查看设计文档
```bash
ls docs/
```

### 运行测试
```bash
python -m pytest tests/
```

### 检查代码
```bash
python -m py_compile src/*.py
```

---

## 🎯 当前任务

**等待中**: CCTJ 仓位文件格式文档

**下一步**:
1. 收到 CCTJ 文档后，设计持仓数据结构
2. 实现 CCTJ 文件解析模块
3. 实现真实持仓/虚拟持仓管理

---

**项目仓库**: https://github.com/YoungManLin/YTXTManualT0Collaboration  
**最后更新**: 2026-02-28
