#!/usr/bin/env python3
"""主入口 - 简化版"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dbf_parser import DBFParser
from position_calc import PositionCalculator
from t0_strategy import T0Strategy
from risk_check import RiskChecker


def main():
    parser = argparse.ArgumentParser(description='策略团队仓位计算系统')
    parser.add_argument('--input', '-i', required=True, help='输入文件路径')
    parser.add_argument('--output', '-o', default='reports/report.xlsx', help='输出报告')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("YXT Manual T0 Collaboration - 策略团队仓位计算系统")
    print("=" * 60)
    
    # 解析文件
    print(f"\n[1/4] 解析输入：{args.input}")
    dbf_parser = DBFParser(args.input)
    orders = dbf_parser.parse()
    summary = dbf_parser.get_summary()
    print(f"  订单数：{summary['total_orders']}")
    
    # 计算仓位
    print(f"\n[2/4] 计算仓位...")
    calc = PositionCalculator()
    calc.load_orders(orders)
    positions = calc.calculate()
    pos_summary = calc.get_summary()
    print(f"  仓位数：{pos_summary['total_positions']}")
    print(f"  总市值：¥{pos_summary['total_market_value']:,.2f}")
    
    # T0 策略
    print(f"\n[3/4] T0 策略分析...")
    t0 = T0Strategy()
    t0.generate_signals(positions, {})
    print(f"  信号数：{t0.get_signal_summary()['total_signals']}")
    
    # 风险检查
    print(f"\n[4/4] 风险检查...")
    risk = RiskChecker()
    risk.check(positions)
    print(f"  状态：{risk.get_alert_summary()['status']}")
    
    # 导出
    print(f"\n[Export] 导出报告：{args.output}")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    calc.export_report(args.output)
    
    print("\n" + "=" * 60)
    print("完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
