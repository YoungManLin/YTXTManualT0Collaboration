"""
风险控制模块

提供仓位风险检查功能：
- 总仓位限额检查
- 单票集中度检查
- T0 频率控制
- 止损检查
- 现金头寸检查
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict


class RiskLevel(Enum):
    """风险等级"""
    INFO = "INFO"         # 提示
    WARNING = "WARNING"   # 警告
    ERROR = "ERROR"       # 错误（禁止交易）


class RiskType(Enum):
    """风险类型"""
    POSITION_LIMIT = "POSITION_LIMIT"           # 仓位限额
    CONCENTRATION = "CONCENTRATION"             # 集中度
    T0_FREQUENCY = "T0_FREQUENCY"               # T0 频率
    STOP_LOSS = "STOP_LOSS"                     # 止损
    CASH_SHORTAGE = "CASH_SHORTAGE"             # 现金不足
    POSITION_TOO_HIGH = "POSITION_TOO_HIGH"     # 持仓过高
    SINGLE_STOCK_LIMIT = "SINGLE_STOCK_LIMIT"   # 单票限额
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"       # 日亏损限额


@dataclass
class RiskAlert:
    """
    风险警报

    表示一项风险检查结果
    """
    level: RiskLevel              # 风险等级
    risk_type: RiskType           # 风险类型
    code: str                     # 警报代码
    message: str                  # 警报信息
    account_id: Optional[str] = None   # 相关账户
    stock_code: Optional[str] = None   # 相关股票
    current_value: Optional[float] = None  # 当前值
    limit_value: Optional[float] = None    # 限制值
    suggestion: Optional[str] = None       # 建议措施
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'level': self.level.value,
            'risk_type': self.risk_type.value,
            'code': self.code,
            'message': self.message,
            'account_id': self.account_id,
            'stock_code': self.stock_code,
            'current_value': self.current_value,
            'limit_value': self.limit_value,
            'suggestion': self.suggestion,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class RiskCheckParams:
    """
    风险检查参数配置

    用于自定义各项风险检查的阈值
    """
    # 仓位限额
    max_total_position_ratio: float = 0.95      # 最大总仓位比例（相对于总资产）
    min_cash_ratio: float = 0.05                # 最小现金比例

    # 集中度限制
    max_single_stock_ratio: float = 0.30        # 单票最大持仓比例
    max_top3_stocks_ratio: float = 0.60         # 前三大持仓最大比例
    max_top5_stocks_ratio: float = 0.80         # 前五大持仓最大比例

    # T0 限制
    max_t0_trades_per_day: int = 10             # 单票每日最大 T0 次数
    max_t0_volume_ratio: float = 2.0            # T0 数量相对于底仓的最大倍数
    min_t0_interval_minutes: int = 5            # T0 最小间隔（分钟）

    # 止损限制
    max_single_stock_loss_ratio: float = -0.10  # 单票最大亏损比例
    max_total_loss_ratio: float = -0.05         # 总账户最大亏损比例
    max_daily_loss_ratio: float = -0.02         # 单日最大亏损比例

    # 价格限制
    max_price_deviation: float = 0.10           # 委托价相对市价最大偏离

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'max_total_position_ratio': self.max_total_position_ratio,
            'min_cash_ratio': self.min_cash_ratio,
            'max_single_stock_ratio': self.max_single_stock_ratio,
            'max_top3_stocks_ratio': self.max_top3_stocks_ratio,
            'max_top5_stocks_ratio': self.max_top5_stocks_ratio,
            'max_t0_trades_per_day': self.max_t0_trades_per_day,
            'max_t0_volume_ratio': self.max_t0_volume_ratio,
            'min_t0_interval_minutes': self.min_t0_interval_minutes,
            'max_single_stock_loss_ratio': self.max_single_stock_loss_ratio,
            'max_total_loss_ratio': self.max_total_loss_ratio,
            'max_daily_loss_ratio': self.max_daily_loss_ratio,
            'max_price_deviation': self.max_price_deviation,
        }


class RiskChecker:
    """
    风险检查器

    对持仓和交易进行多维度风险检查
    """

    def __init__(self, params: Optional[RiskCheckParams] = None):
        """
        初始化检查器

        Args:
            params: 风险检查参数配置
        """
        self.params = params or RiskCheckParams()
        self.alerts: List[RiskAlert] = []
        self.trade_records: List[Dict[str, Any]] = []  # 交易记录
        self.t0_trade_counts: Dict[str, int] = defaultdict(int)  # 单票 T0 计数

    def clear_alerts(self):
        """清空警报"""
        self.alerts = []

    def add_alert(self, alert: RiskAlert):
        """添加警报"""
        self.alerts.append(alert)

    def add_alerts(self, alerts: List[RiskAlert]):
        """批量添加警报"""
        self.alerts.extend(alerts)

    def check_position_limit(self, positions, total_assets: float) -> List[RiskAlert]:
        """
        检查仓位限额

        Args:
            positions: PositionManager 对象
            total_assets: 总资产（包括现金）

        Returns:
            风险警报列表
        """
        alerts = []
        summary = positions.get_summary()

        total_market_value = summary.get('total_market_value', 0)
        if total_assets <= 0:
            return alerts

        position_ratio = total_market_value / total_assets

        # 检查总仓位是否超限
        if position_ratio > self.params.max_total_position_ratio:
            alerts.append(RiskAlert(
                level=RiskLevel.ERROR,
                risk_type=RiskType.POSITION_LIMIT,
                code="PL001",
                message=f"总仓位超限：{position_ratio:.2%} > {self.params.max_total_position_ratio:.2%}",
                current_value=position_ratio,
                limit_value=self.params.max_total_position_ratio,
                suggestion="降低仓位至限制以内",
            ))

        # 检查现金比例是否过低
        cash_ratio = 1 - position_ratio
        if cash_ratio < self.params.min_cash_ratio:
            alerts.append(RiskAlert(
                level=RiskLevel.WARNING,
                risk_type=RiskType.CASH_SHORTAGE,
                code="CS001",
                message=f"现金比例过低：{cash_ratio:.2%} < {self.params.min_cash_ratio:.2%}",
                current_value=cash_ratio,
                limit_value=self.params.min_cash_ratio,
                suggestion="保留足够的现金储备",
            ))

        return alerts

    def check_concentration(self, positions) -> List[RiskAlert]:
        """
        检查持仓集中度

        Args:
            positions: PositionManager 对象

        Returns:
            风险警报列表
        """
        alerts = []

        # 按账户检查
        for account_id, account in positions.accounts.items():
            if account.total_market_value <= 0:
                continue

            # 计算各股票持仓比例
            stock_ratios = []
            for stock_code, pos in account.positions.items():
                ratio = pos.market_value / account.total_market_value if account.total_market_value > 0 else 0
                stock_ratios.append((stock_code, pos.stock_name, ratio, pos.market_value))

            # 按持仓比例排序
            stock_ratios.sort(key=lambda x: x[2], reverse=True)

            # 检查单票集中度
            for stock_code, stock_name, ratio, mv in stock_ratios:
                if ratio > self.params.max_single_stock_ratio:
                    alerts.append(RiskAlert(
                        level=RiskLevel.WARNING,
                        risk_type=RiskType.CONCENTRATION,
                        code="CC001",
                        message=f"账户 {account_id} 单票 {stock_code} 集中度过高：{ratio:.2%}",
                        account_id=account_id,
                        stock_code=stock_code,
                        current_value=ratio,
                        limit_value=self.params.max_single_stock_ratio,
                        suggestion=f"降低 {stock_code} 持仓至{self.params.max_single_stock_ratio:.0%}以内",
                    ))

            # 检查前三大持仓集中度
            if len(stock_ratios) >= 3:
                top3_ratio = sum(r[2] for r in stock_ratios[:3])
                if top3_ratio > self.params.max_top3_stocks_ratio:
                    alerts.append(RiskAlert(
                        level=RiskLevel.INFO,
                        risk_type=RiskType.CONCENTRATION,
                        code="CC002",
                        message=f"账户 {account_id} 前三大持仓集中度过高：{top3_ratio:.2%}",
                        account_id=account_id,
                        current_value=top3_ratio,
                        limit_value=self.params.max_top3_stocks_ratio,
                        suggestion="适度分散投资",
                    ))

            # 检查前五大持仓集中度
            if len(stock_ratios) >= 5:
                top5_ratio = sum(r[2] for r in stock_ratios[:5])
                if top5_ratio > self.params.max_top5_stocks_ratio:
                    alerts.append(RiskAlert(
                        level=RiskLevel.INFO,
                        risk_type=RiskType.CONCENTRATION,
                        code="CC003",
                        message=f"账户 {account_id} 前五大持仓集中度过高：{top5_ratio:.2%}",
                        account_id=account_id,
                        current_value=top5_ratio,
                        limit_value=self.params.max_top5_stocks_ratio,
                        suggestion="适度分散投资",
                    ))

        return alerts

    def check_t0_frequency(self, positions, stock_code: str,
                           account_id: str, volume: int) -> List[RiskAlert]:
        """
        检查 T0 交易频率

        Args:
            positions: PositionManager 对象
            stock_code: 证券代码
            account_id: 账户 ID
            volume: T0 数量

        Returns:
            风险警报列表
        """
        alerts = []
        key = f"{account_id}_{stock_code}"

        # 检查每日 T0 次数
        t0_count = self.t0_trade_counts.get(key, 0)
        if t0_count >= self.params.max_t0_trades_per_day:
            alerts.append(RiskAlert(
                level=RiskLevel.ERROR,
                risk_type=RiskType.T0_FREQUENCY,
                code="TF001",
                message=f"账户 {account_id} 股票 {stock_code} 今日 T0 次数已达上限：{t0_count}",
                account_id=account_id,
                stock_code=stock_code,
                current_value=t0_count,
                limit_value=self.params.max_t0_trades_per_day,
                suggestion="暂停该股票的 T0 交易",
            ))

        # 检查 T0 数量相对于底仓的倍数
        pos = positions.get_position(account_id, stock_code)
        if pos and pos.total_volume > 0:
            volume_ratio = volume / pos.total_volume
            if volume_ratio > self.params.max_t0_volume_ratio:
                alerts.append(RiskAlert(
                    level=RiskLevel.WARNING,
                    risk_type=RiskType.T0_FREQUENCY,
                    code="TF002",
                    message=f"T0 数量过大：{volume} / {pos.total_volume} = {volume_ratio:.2f}倍",
                    account_id=account_id,
                    stock_code=stock_code,
                    current_value=volume_ratio,
                    limit_value=self.params.max_t0_volume_ratio,
                    suggestion="降低 T0 交易数量",
                ))

        return alerts

    def record_t0_trade(self, account_id: str, stock_code: str, volume: int):
        """
        记录 T0 交易

        Args:
            account_id: 账户 ID
            stock_code: 证券代码
            volume: 交易数量
        """
        key = f"{account_id}_{stock_code}"
        self.t0_trade_counts[key] += 1
        self.trade_records.append({
            'account_id': account_id,
            'stock_code': stock_code,
            'volume': volume,
            'type': 'T0',
            'timestamp': datetime.now(),
        })

    def check_stop_loss(self, positions) -> List[RiskAlert]:
        """
        检查止损

        Args:
            positions: PositionManager 对象

        Returns:
            风险警报列表
        """
        alerts = []

        # 按账户检查
        for account_id, account in positions.accounts.items():
            # 检查单票止损
            for stock_code, pos in account.positions.items():
                if pos.cost_amount <= 0:
                    continue

                loss_ratio = pos.profit_loss / pos.cost_amount
                if loss_ratio < self.params.max_single_stock_loss_ratio:
                    alerts.append(RiskAlert(
                        level=RiskLevel.WARNING,
                        risk_type=RiskType.STOP_LOSS,
                        code="SL001",
                        message=f"账户 {account_id} 股票 {stock_code} 触及止损线：{loss_ratio:.2%}",
                        account_id=account_id,
                        stock_code=stock_code,
                        current_value=loss_ratio,
                        limit_value=self.params.max_single_stock_loss_ratio,
                        suggestion="考虑减仓或止损",
                    ))

            # 检查总账户止损
            if account.total_cost > 0:
                total_loss_ratio = account.total_profit_loss / account.total_cost
                if total_loss_ratio < self.params.max_total_loss_ratio:
                    alerts.append(RiskAlert(
                        level=RiskLevel.ERROR,
                        risk_type=RiskType.STOP_LOSS,
                        code="SL002",
                        message=f"账户 {account_id} 总亏损触及止损线：{total_loss_ratio:.2%}",
                        account_id=account_id,
                        current_value=total_loss_ratio,
                        limit_value=self.params.max_total_loss_ratio,
                        suggestion="立即降低仓位，控制风险",
                    ))

        return alerts

    def check_daily_loss(self, positions, yesterday_value: float) -> List[RiskAlert]:
        """
        检查日亏损限额

        Args:
            positions: PositionManager 对象
            yesterday_value: 昨日账户总值

        Returns:
            风险警报列表
        """
        alerts = []

        if yesterday_value <= 0:
            return alerts

        today_value = sum(acc.total_market_value for acc in positions.accounts.values())
        daily_change = (today_value - yesterday_value) / yesterday_value

        if daily_change < self.params.max_daily_loss_ratio:
            alerts.append(RiskAlert(
                level=RiskLevel.ERROR,
                risk_type=RiskType.DAILY_LOSS_LIMIT,
                code="DL001",
                message=f"日亏损超限：{daily_change:.2%} < {self.params.max_daily_loss_ratio:.2%}",
                current_value=daily_change,
                limit_value=self.params.max_daily_loss_ratio,
                suggestion="停止交易，进行风险复盘",
            ))

        return alerts

    def check_price_deviation(self, order_price: float, market_price: float) -> List[RiskAlert]:
        """
        检查价格偏离

        Args:
            order_price: 委托价格
            market_price: 市场价格

        Returns:
            风险警报列表
        """
        alerts = []

        if market_price <= 0:
            return alerts

        deviation = abs(order_price - market_price) / market_price

        if deviation > self.params.max_price_deviation:
            alerts.append(RiskAlert(
                level=RiskLevel.WARNING,
                risk_type=RiskType.POSITION_TOO_HIGH,
                code="PD001",
                message=f"委托价格偏离过大：{deviation:.2%}",
                current_value=deviation,
                limit_value=self.params.max_price_deviation,
                suggestion="检查价格输入是否正确",
            ))

        return alerts

    def check(self, positions, total_assets: Optional[float] = None,
              yesterday_value: Optional[float] = None) -> List[RiskAlert]:
        """
        执行全面风险检查

        Args:
            positions: PositionManager 对象
            total_assets: 总资产（可选）
            yesterday_value: 昨日市值（可选）

        Returns:
            风险警报列表
        """
        self.clear_alerts()

        # 1. 仓位限额检查
        if total_assets:
            self.add_alerts(self.check_position_limit(positions, total_assets))

        # 2. 集中度检查
        self.add_alerts(self.check_concentration(positions))

        # 3. 止损检查
        self.add_alerts(self.check_stop_loss(positions))

        # 4. 日亏损检查
        if yesterday_value:
            self.add_alerts(self.check_daily_loss(positions, yesterday_value))

        return self.alerts

    def check_order(self, positions, account_id: str, stock_code: str,
                    volume: int, price: float, market_price: float) -> List[RiskAlert]:
        """
        检查订单风险

        Args:
            positions: PositionManager 对象
            account_id: 账户 ID
            stock_code: 证券代码
            volume: 订单数量
            price: 委托价格
            market_price: 市场价格

        Returns:
            风险警报列表
        """
        self.clear_alerts()

        # 1. T0 频率检查
        self.add_alerts(self.check_t0_frequency(positions, stock_code, account_id, volume))

        # 2. 价格偏离检查
        self.add_alerts(self.check_price_deviation(price, market_price))

        return self.alerts

    def get_summary(self) -> Dict[str, Any]:
        """获取检查汇总"""
        error_count = len([a for a in self.alerts if a.level == RiskLevel.ERROR])
        warning_count = len([a for a in self.alerts if a.level == RiskLevel.WARNING])
        info_count = len([a for a in self.alerts if a.level == RiskLevel.INFO])

        return {
            'total_alerts': len(self.alerts),
            'error_count': error_count,
            'warning_count': warning_count,
            'info_count': info_count,
            'status': 'ERROR' if error_count > 0 else ('WARNING' if warning_count > 0 else 'OK'),
            't0_trade_count': sum(self.t0_trade_counts.values()),
            'params': self.params.to_dict(),
        }

    def has_error(self) -> bool:
        """是否有错误级警报"""
        return any(a.level == RiskLevel.ERROR for a in self.alerts)

    def has_warning(self) -> bool:
        """是否有警告级警报"""
        return any(a.level == RiskLevel.WARNING for a in self.alerts)

    def can_trade(self) -> bool:
        """是否可以交易（无错误级警报）"""
        return not self.has_error()
