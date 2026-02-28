# YTXT Manual T0 Collaboration - 项目状态（已修正）

**更新时间**: 2026-02-28 17:30  
**版本**: v0.2.0  
**状态**: 开发中  
**阶段**: 需求变更

---

## 📊 整体进度

**完成度**: 40%

```
[████████------------] 40%
```

### 阶段划分

- ✅ **阶段 1: 需求分析** (100%) - 已完成（需求已修正）
- 🔄 **阶段 2: 仓位管理** (80%) - 进行中
- ⏳ **阶段 3: 台账记录** (0%) - 待开始
- ⏳ **阶段 4: 授权文件生成** (0%) - 待开始
- ⏳ **阶段 5: 真实持仓文件** (0%) - 待开始

---

## 🎯 修正后的项目目标

### 核心功能

**YTXT 项目定位**: 收盘后定时任务系统

**工作流程**:
```
收盘后（可配置时间）
    ↓
定时启动
    ↓
读取仓位数据（CCTJ 文件）
    ↓
记录台账
    ↓
计算真实持仓
    ↓
生成第二天的授权文件
    ↓
生成真实持仓文件
```

### 不做的事情

- ❌ **T0 交易逻辑** - 不需要实现
- ❌ **实时交易** - 只负责盘后处理
- ❌ **信号生成** - 不涉及

---

## 📋 详细功能需求

### 1. 定时启动 ⏰

**配置项**:
- 启动时间（默认：15:30，收盘后）
- 时区设置（默认：Asia/Shanghai）

**实现方式**:
- 系统 crontab
- 或 Python schedule 库

### 2. 读取仓位数据 📥

**输入**:
- GT 系统 CCTJ 仓位文件
- 支持格式：.cctj, .dbf, .xlsx, .csv

**功能**:
- 解析仓位文件
- 数据验证
- 错误处理

### 3. 记录台账 📝

**台账内容**:
- 日期
- 账户 ID
- 证券代码
- 持仓数量
- 成本价
- 当前价
- 市值
- 盈亏

**输出**:
- Excel 台账文件
- 或数据库记录

### 4. 计算真实持仓 📊

**计算逻辑**:
- 读取 CCTJ 仓位
- 计算实际持仓
- 计算可用仓位
- 计算冻结仓位

**输出**:
- 真实持仓数据结构
- 持仓汇总报表

### 5. 生成第二天授权文件 📄

**授权文件内容**:
- 证券代码
- 买入上限
- 卖出上限
- 仓位限制
- 风险参数

**输出格式**:
- DBF 文件（迅投系统）
- 或 Excel 文件

### 6. 生成真实持仓文件 📈

**持仓文件内容**:
- 账户 ID
- 证券代码
- 持仓数量
- 可用数量
- 成本价
- 当前价
- 市值
- 盈亏

**输出格式**:
- Excel 文件
- 或 CSV 文件

---

## 📁 项目结构（修正后）

```
YTXTManualT0Collaboration/
├── src/
│   ├── __init__.py
│   ├── cctj_parser.py      ✅ 已完成 - CCTJ 解析
│   ├── position.py         ✅ 已完成 - 持仓管理
│   ├── ledger.py           ⏳ 待创建 - 台账记录
│   ├── auth_generator.py   ⏳ 待创建 - 授权文件生成
│   ├── position_export.py  ⏳ 待创建 - 持仓文件导出
│   ├── main.py             ✅ 已完成 - 主入口
│   └── config.py           ⏳ 待创建 - 配置管理
├── tests/
│   ├── test_cctj_parser.py
│   └── ...
├── config/
│   └── schedule.yaml       ⏳ 待创建 - 定时配置
├── output/
│   ├── ledger/             ⏳ 台账输出
│   ├── auth/               ⏳ 授权文件
│   └── position/           ⏳ 持仓文件
├── docs/
│   ├── 设计文档
│   └── 使用说明
└── requirements.txt
```

---

## 🔧 配置项

### schedule.yaml

```yaml
# 定时配置
schedule:
  enabled: true
  time: "15:30"        # 启动时间
  timezone: "Asia/Shanghai"

# 输入配置
input:
  cctj_file_path: "/path/to/cctj"
  file_format: "auto"  # auto, cctj, dbf, xlsx, csv

# 输出配置
output:
  ledger_dir: "./output/ledger"
  auth_file_dir: "./output/auth"
  position_file_dir: "./output/position"
  format: "xlsx"       # xlsx, csv, dbf

# 风险配置
risk:
  max_position_ratio: 0.2
  max_total_value: 10000000
```

---

## ✅ 已完成功能

- [x] CCTJ 仓位文件解析模块 (`src/cctj_parser.py`)
- [x] 持仓管理器 (`src/position.py`)
- [x] 项目框架搭建

---

## ⏳ 待完成功能

### 高优先级（本周）
- [ ] 台账记录模块 (`src/ledger.py`)
- [ ] 授权文件生成器 (`src/auth_generator.py`)
- [ ] 持仓文件导出 (`src/position_export.py`)
- [ ] 配置管理 (`src/config.py`)

### 中优先级（下周）
- [ ] 定时启动功能
- [ ] 单元测试
- [ ] 使用文档

---

## 📅 里程碑

- ✅ **2026-02-28**: v0.1.0 - 项目启动
- 🎯 **2026-03-07**: v0.2.0 - 核心功能完成
- 🎯 **2026-03-14**: v1.0.0 - 正式发布

---

## 🔗 重要链接

### 设计文档（本地）
- **手动 T0 实施方案**: `docs/手动 T0 实施方案.docx` ✅
- **迅投 PB-DBF 参数说明**: `docs/迅投 PB-DBF 预埋单参数说明文档 V2.15.xlsx` ✅
- **文档说明**: `docs/README.md`

### 代码仓库
- **GitHub**: https://github.com/YoungManLin/YTXTManualT0Collaboration

---

**下次更新**: 完成台账记录模块后  
**负责人**: Strategy Team  
**联系方式**: linyoungman3@gmail.com
