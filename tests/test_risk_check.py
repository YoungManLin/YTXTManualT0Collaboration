"""
风险控制模块单元测试
"""

import pytest
from src.risk_check import (
    RiskAlert, RiskCheckParams, RiskChecker,
    RiskLevel, RiskType
)
from src.position import PositionManager, RealPosition


class TestRiskAlert:
    """测试 RiskAlert 类"""

    def test_create_alert(self):
        """测试创建警报"""
        alert = RiskAlert(
            level=RiskLevel.WARNING,
            risk_type=RiskType.CONCENTRATION,
            code="CC001",
            message="单票集中度过高",
            stock_code="000001",
            current_value=0.35,
            limit_value=0.30,
            suggestion="降低持仓",
        )

        assert alert.level == RiskLevel.WARNING
        assert alert.risk_type == RiskType.CONCENTRATION
        assert alert.code == "CC001"
        assert alert.current_value == 0.35

    def test_alert_to_dict(self):
        """测试转换为字典"""
        alert = RiskAlert(
            level=RiskLevel.ERROR,
            risk_type=RiskType.STOP_LOSS,
            code="SL001",
            message="触及止损线",
        )

        d = alert.to_dict()
        assert d['level'] == 'ERROR'
        assert d['risk_type'] == 'STOP_LOSS'
        assert d['code'] == 'SL001'
        assert 'timestamp' in d


class TestRiskCheckParams:
    """测试 RiskCheckParams 类"""

    def test_default_params(self):
        """测试默认参数"""
        params = RiskCheckParams()

        assert params.max_total_position_ratio == 0.95
        assert params.min_cash_ratio == 0.05
        assert params.max_single_stock_ratio == 0.30
        assert params.max_t0_trades_per_day == 10
        assert params.max_single_stock_loss_ratio == -0.10

    def test_custom_params(self):
        """测试自定义参数"""
        params = RiskCheckParams(
            max_total_position_ratio=0.80,
            max_single_stock_ratio=0.20,
            max_t0_trades_per_day=5,
        )

        assert params.max_total_position_ratio == 0.80
        assert params.max_single_stock_ratio == 0.20
        assert params.max_t0_trades_per_day == 5

    def test_params_to_dict(self):
        """测试转换为字典"""
        params = RiskCheckParams()
        d = params.to_dict()

        assert 'max_total_position_ratio' in d
        assert 'max_single_stock_ratio' in d
        assert 'max_t0_trades_per_day' in d


class TestRiskChecker:
    """测试 RiskChecker 类"""

    def test_create_checker(self):
        """测试创建检查器"""
        checker = RiskChecker()
        assert len(checker.alerts) == 0
        assert checker.can_trade() == True

    def test_create_checker_with_params(self):
        """测试创建带参数的检查器"""
        params = RiskCheckParams(max_single_stock_ratio=0.25)
        checker = RiskChecker(params=params)

        assert checker.params.max_single_stock_ratio == 0.25

    def test_clear_alerts(self):
        """测试清空警报"""
        checker = RiskChecker()
        checker.add_alert(RiskAlert(
            level=RiskLevel.WARNING,
            risk_type=RiskType.CONCENTRATION,
            code="CC001",
            message="测试警报",
        ))

        assert len(checker.alerts) == 1
        checker.clear_alerts()
        assert len(checker.alerts) == 0

    def test_add_alert(self):
        """测试添加警报"""
        checker = RiskChecker()

        alert = RiskAlert(
            level=RiskLevel.ERROR,
            risk_type=RiskType.STOP_LOSS,
            code="SL001",
            message="测试错误",
        )

        checker.add_alert(alert)
        assert len(checker.alerts) == 1
        assert checker.has_error() == True

    def test_has_error(self):
        """测试是否有错误"""
        checker = RiskChecker()

        assert checker.has_error() == False

        checker.add_alert(RiskAlert(
            level=RiskLevel.ERROR,
            risk_type=RiskType.STOP_LOSS,
            code="SL001",
            message="错误",
        ))
        assert checker.has_error() == True

    def test_has_warning(self):
        """测试是否有警告"""
        checker = RiskChecker()

        assert checker.has_warning() == False

        checker.add_alert(RiskAlert(
            level=RiskLevel.WARNING,
            risk_type=RiskType.CONCENTRATION,
            code="CC001",
            message="警告",
        ))
        assert checker.has_warning() == True

    def test_can_trade(self):
        """测试是否可以交易"""
        checker = RiskChecker()
        assert checker.can_trade() == True

        # 添加错误警报后不能交易
        checker.add_alert(RiskAlert(
            level=RiskLevel.ERROR,
            risk_type=RiskType.STOP_LOSS,
            code="SL001",
            message="错误",
        ))
        assert checker.can_trade() == False

        # 只有警告仍可交易
        checker2 = RiskChecker()
        checker2.add_alert(RiskAlert(
            level=RiskLevel.WARNING,
            risk_type=RiskType.CONCENTRATION,
            code="CC001",
            message="警告",
        ))
        assert checker2.can_trade() == True

    def test_get_summary(self):
        """测试获取汇总"""
        checker = RiskChecker()

        checker.add_alert(RiskAlert(
            level=RiskLevel.ERROR,
            risk_type=RiskType.STOP_LOSS,
            code="SL001",
            message="错误",
        ))
        checker.add_alert(RiskAlert(
            level=RiskLevel.WARNING,
            risk_type=RiskType.CONCENTRATION,
            code="CC001",
            message="警告",
        ))
        checker.add_alert(RiskAlert(
            level=RiskLevel.INFO,
            risk_type=RiskType.CONCENTRATION,
            code="CC002",
            message="提示",
        ))

        summary = checker.get_summary()
        assert summary['total_alerts'] == 3
        assert summary['error_count'] == 1
        assert summary['warning_count'] == 1
        assert summary['info_count'] == 1
        assert summary['status'] == 'ERROR'

    def test_check_position_limit(self):
        """测试仓位限额检查"""
        pm = PositionManager()
        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            cost_price=10.0,
            current_price=10.0,
        )
        account = pm.get_or_create_account("TEST001")
        account.add_position(pos)

        checker = RiskChecker()
        # 持仓 10000，总资产 10000，仓位比例 100% > 95%
        alerts = checker.check_position_limit(pm, total_assets=10000)

        assert len(alerts) > 0
        assert any(a.risk_type == RiskType.POSITION_LIMIT for a in alerts)

    def test_check_position_limit_ok(self):
        """测试仓位限额检查（正常）"""
        pm = PositionManager()
        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=500,
            available_volume=500,
            cost_price=10.0,
            current_price=10.0,
        )
        account = pm.get_or_create_account("TEST001")
        account.add_position(pos)

        checker = RiskChecker()
        # 持仓 5000，总资产 10000，仓位比例 50% < 95%
        alerts = checker.check_position_limit(pm, total_assets=10000)

        position_alerts = [a for a in alerts if a.risk_type == RiskType.POSITION_LIMIT]
        assert len(position_alerts) == 0

    def test_check_cash_shortage(self):
        """测试现金不足检查"""
        pm = PositionManager()
        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=980,
            available_volume=980,
            cost_price=10.0,
            current_price=10.0,
        )
        account = pm.get_or_create_account("TEST001")
        account.add_position(pos)

        checker = RiskChecker()
        # 持仓 9800，总资产 10000，现金比例 2% < 5%
        alerts = checker.check_position_limit(pm, total_assets=10000)

        cash_alerts = [a for a in alerts if a.risk_type == RiskType.CASH_SHORTAGE]
        assert len(cash_alerts) > 0

    def test_check_concentration(self):
        """测试集中度检查"""
        pm = PositionManager()

        # 单票持仓超过 30%
        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            cost_price=10.0,
            current_price=10.0,
        )
        account = pm.get_or_create_account("TEST001")
        account.add_position(pos)

        # 添加另一个持仓较低的
        pos2 = RealPosition(
            stock_code="000002",
            stock_name="万科 A",
            account_id="TEST001",
            market_id="SZ",
            total_volume=100,
            available_volume=100,
            cost_price=10.0,
            current_price=10.0,
        )
        account.add_position(pos2)

        checker = RiskChecker()
        alerts = checker.check_concentration(pm)

        # 000001 持仓占比 10000/11000 = 90.9% > 30%
        concentration_alerts = [a for a in alerts if a.risk_type == RiskType.CONCENTRATION]
        assert len(concentration_alerts) > 0

    def test_check_t0_frequency(self):
        """测试 T0 频率检查"""
        pm = PositionManager()
        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
        )
        account = pm.get_or_create_account("TEST001")
        account.add_position(pos)

        checker = RiskChecker(RiskCheckParams(max_t0_trades_per_day=3))

        # 模拟 3 次 T0 交易
        checker.record_t0_trade("TEST001", "000001", 100)
        checker.record_t0_trade("TEST001", "000001", 100)
        checker.record_t0_trade("TEST001", "000001", 100)

        # 第 4 次检查应该失败
        alerts = checker.check_t0_frequency(pm, "000001", "TEST001", 100)
        assert len(alerts) > 0
        assert any(a.risk_type == RiskType.T0_FREQUENCY for a in alerts)

    def test_check_t0_volume_ratio(self):
        """测试 T0 数量比例检查"""
        pm = PositionManager()
        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=500,
            available_volume=500,
        )
        account = pm.get_or_create_account("TEST001")
        account.add_position(pos)

        checker = RiskChecker()

        # T0 数量 1500，底仓 500，比例 3 倍 > 2 倍
        alerts = checker.check_t0_frequency(pm, "000001", "TEST001", 1500)

        volume_alerts = [a for a in alerts if a.risk_type == RiskType.T0_FREQUENCY]
        assert len(volume_alerts) > 0

    def test_check_stop_loss(self):
        """测试止损检查"""
        pm = PositionManager()

        # 创建亏损持仓（亏损 15% > 10%）
        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            cost_price=10.0,
            current_price=8.5,  # 亏损 15%
        )
        account = pm.get_or_create_account("TEST001")
        account.add_position(pos)

        checker = RiskChecker()
        alerts = checker.check_stop_loss(pm)

        stop_loss_alerts = [a for a in alerts if a.risk_type == RiskType.STOP_LOSS]
        assert len(stop_loss_alerts) > 0

    def test_check_full(self):
        """测试全面风险检查"""
        pm = PositionManager()
        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            cost_price=10.0,
            current_price=10.0,
        )
        account = pm.get_or_create_account("TEST001")
        account.add_position(pos)

        checker = RiskChecker()
        alerts = checker.check(pm, total_assets=10000)

        # 应该有现金不足的警报
        assert len(alerts) > 0

    def test_check_order(self):
        """测试订单检查"""
        pm = PositionManager()

        checker = RiskChecker()
        alerts = checker.check_order(
            pm,
            account_id="TEST001",
            stock_code="000001",
            volume=1000,
            price=10.0,
            market_price=10.0,
        )

        assert len(alerts) == 0

    def test_check_price_deviation(self):
        """测试价格偏离检查"""
        checker = RiskChecker()

        # 委托价 11.5 元，市价 10 元，偏离 15% > 10%
        alerts = checker.check_price_deviation(11.5, 10.0)

        assert len(alerts) > 0
        assert any(a.risk_type == RiskType.POSITION_TOO_HIGH for a in alerts)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
