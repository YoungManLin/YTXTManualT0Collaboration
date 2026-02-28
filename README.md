# YXT Manual T0 Collaboration - 策略团队仓位计算系统

## 项目简介

基于迅投 PB-DBF 预埋单格式的策略团队仓位计算系统，支持手动 T0 交易的仓位管理、风险控制和绩效分析。

## 核心功能

- ✅ DBF 预埋单文件解析
- ✅ 实时仓位计算
- ✅ T0 交易支持（日内交易）
- ✅ 多策略团队管理
- ✅ 风险控制检查
- ✅ 绩效分析报表

## 技术栈

- Python 3.12+
- pandas (数据处理)
- numpy (数值计算)
- pytest (单元测试)

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行示例
python src/main.py --data data/sample_orders.dbf

# 运行测试
pytest tests/ -v
```

## 项目结构

```
YTXTManualT0Collaboration/
├── src/                    # 源代码
│   ├── __init__.py
│   ├── dbf_parser.py      # DBF 文件解析
│   ├── position_calc.py   # 仓位计算核心
│   ├── t0_strategy.py     # T0 策略支持
│   ├── risk_check.py      # 风险控制
│   └── main.py            # 主入口
├── tests/                  # 测试代码
│   ├── __init__.py
│   ├── test_dbf_parser.py
│   ├── test_position_calc.py
│   └── test_t0_strategy.py
├── data/                   # 样例数据
│   └── sample_orders.xlsx
├── docs/                   # 文档
│   └── API.md
├── requirements.txt
└── README.md
```

## DBF 参数说明

基于迅投 PB-DBF 预埋单参数说明文档 V2.15：

| 字段名 | 类型 | 说明 | 必填 |
|--------|------|------|------|
| order_type | String | 下单类型 | Y |
| price_type | String | 委托价格类型 | Y |
| mode_price | String | 委托价格 | N |
| stock_code | String | 证券代码 | Y |
| volume | String | 委托数量 | Y |
| account_id | String | 下单资金账号 | Y |
| ... | ... | ... | ... |

详细参数说明请参考 `docs/DBF_PARAMS.md`

## 开发进度

- [x] 项目初始化
- [x] DBF 解析模块
- [ ] 仓位计算核心
- [ ] T0 策略支持
- [ ] 风险控制
- [ ] 单元测试
- [ ] GitHub 提交

## License

MIT
