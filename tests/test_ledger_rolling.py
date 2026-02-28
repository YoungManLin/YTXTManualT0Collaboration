"""
台账滚动计算模块单元测试

测试核心公式：Ledger_T = Ledger_{T-1} × AF_T + E_T
"""

import pytest
from src.ledger_rolling import (
    LedgerRollingCalculator,
    LedgerRollingState,
    AdjustmentEvent,
    AdjustmentType,
)


class TestAdjustmentType:
    """测试调整类型枚举"""

    def test_adjustment_type_values(self):
        """测试调整类型值"""
        assert AdjustmentType.DIVIDEND.value == "dividend"
        assert AdjustmentType.RIGHTS_ISSUE.value == "rights_issue"
        assert AdjustmentType.BONUS_SHARE.value == "bonus_share"
        assert AdjustmentType.SPLIT.value == "split"
        assert AdjustmentType.REVERSE_SPLIT.value == "reverse_split"
        assert AdjustmentType.SPECIAL.value == "special"


class TestAdjustmentEvent:
    """测试调整事件类"""

    def test_create_event(self):
        """测试创建调整事件"""
        event = AdjustmentEvent(
            trade_date="20240101",
            stock_code="000001",
            adjustment_type=AdjustmentType.DIVIDEND,
            adjustment_factor=1.0,
            adjustment_amount=0.5,
            description="每股分红 0.5 元",
        )

        assert event.trade_date == "20240101"
        assert event.stock_code == "000001"
        assert event.adjustment_type == AdjustmentType.DIVIDEND
        assert event.adjustment_factor == 1.0
        assert event.adjustment_amount == 0.5

    def test_event_key(self):
        """测试唯一键"""
        event = AdjustmentEvent(
            trade_date="20240101",
            stock_code="000001",
            adjustment_type=AdjustmentType.DIVIDEND,
        )

        assert event.key == "20240101_000001"

    def test_event_to_dict(self):
        """测试转换为字典"""
        event = AdjustmentEvent(
            trade_date="20240101",
            stock_code="000001",
            adjustment_type=AdjustmentType.DIVIDEND,
            adjustment_factor=1.0,
            adjustment_amount=0.5,
            description="分红",
        )

        d = event.to_dict()
        assert d['trade_date'] == "20240101"
        assert d['stock_code'] == "000001"
        assert d['adjustment_type'] == "dividend"
        assert d['adjustment_factor'] == 1.0
        assert d['adjustment_amount'] == 0.5


class TestLedgerRollingState:
    """测试台账滚动状态类"""

    def test_create_state(self):
        """测试创建状态"""
        state = LedgerRollingState(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
        )

        assert state.stock_code == "000001"
        assert state.stock_name == "平安银行"
        assert state.account_id == "TEST001"
        assert state.previous_ledger == 0.0
        assert state.current_ledger == 0.0
        assert state.adjustment_factor == 1.0

    def test_state_key(self):
        """测试唯一键"""
        state = LedgerRollingState(
            stock_code="000001",
            account_id="TEST001",
        )

        assert state.key == "TEST001_000001"

    def test_state_to_dict(self):
        """测试转换为字典"""
        state = LedgerRollingState(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            previous_ledger=1000.0,
            current_ledger=1050.0,
            adjustment_factor=1.0,
            adjustment_amount=50.0,
        )

        d = state.to_dict()
        assert d['stock_code'] == "000001"
        assert d['stock_name'] == "平安银行"
        assert d['account_id'] == "TEST001"
        assert d['previous_ledger'] == 1000.0
        assert d['current_ledger'] == 1050.0
        assert d['adjustment_factor'] == 1.0
        assert d['adjustment_amount'] == 50.0


class TestLedgerRollingCalculator:
    """测试台账滚动计算器"""

    def test_create_calculator(self):
        """测试创建计算器"""
        calc = LedgerRollingCalculator()
        assert calc.get_all_states() == []

    def test_initialize_ledger(self):
        """测试初始化台账"""
        calc = LedgerRollingCalculator()

        state = calc.initialize_ledger(
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            initial_ledger=1000.0,
            trade_date="20240101",
        )

        assert state.current_ledger == 1000.0
        assert state.previous_ledger == 1000.0
        assert state.current_date == "20240101"

    def test_roll_basic(self):
        """测试基本滚动计算"""
        calc = LedgerRollingCalculator()

        # 初始化
        calc.initialize_ledger(
            account_id="TEST001",
            stock_code="000001",
            initial_ledger=1000.0,
            trade_date="20240101",
        )

        # 滚动：AF=1.0, E=50
        # Ledger_T = 1000 × 1.0 + 50 = 1050
        state = calc.roll(
            account_id="TEST001",
            stock_code="000001",
            adjustment_factor=1.0,
            adjustment_amount=50.0,
            trade_date="20240102",
        )

        assert state.previous_ledger == 1000.0
        assert state.current_ledger == 1050.0
        assert state.adjustment_factor == 1.0
        assert state.adjustment_amount == 50.0

    def test_roll_with_adjustment_factor(self):
        """测试带除权因子的滚动"""
        calc = LedgerRollingCalculator()

        # 初始化
        calc.initialize_ledger(
            account_id="TEST001",
            stock_code="000001",
            initial_ledger=1000.0,
            trade_date="20240101",
        )

        # 滚动：AF=0.9（如 10 送 1）, E=0
        # Ledger_T = 1000 × 0.9 + 0 = 900
        state = calc.roll(
            account_id="TEST001",
            stock_code="000001",
            adjustment_factor=0.9,
            adjustment_amount=0.0,
            trade_date="20240102",
        )

        assert state.previous_ledger == 1000.0
        assert state.current_ledger == 900.0
        assert state.adjustment_factor == 0.9

    def test_roll_formula(self):
        """测试核心公式 Ledger_T = Ledger_{T-1} × AF_T + E_T"""
        calc = LedgerRollingCalculator()

        # 初始化
        calc.initialize_ledger(
            account_id="TEST001",
            stock_code="000001",
            initial_ledger=2000.0,
            trade_date="20240101",
        )

        # 多次滚动
        # T1: 2000 × 1.0 + 100 = 2100
        calc.roll(
            account_id="TEST001",
            stock_code="000001",
            adjustment_factor=1.0,
            adjustment_amount=100.0,
            trade_date="20240102",
        )

        # T2: 2100 × 0.95 + 50 = 2045
        calc.roll(
            account_id="TEST001",
            stock_code="000001",
            adjustment_factor=0.95,
            adjustment_amount=50.0,
            trade_date="20240103",
        )

        state = calc.get_state("TEST001", "000001")
        assert state.current_ledger == 2045.0

    def test_get_current_ledger(self):
        """测试获取当前台账"""
        calc = LedgerRollingCalculator()

        calc.initialize_ledger(
            account_id="TEST001",
            stock_code="000001",
            initial_ledger=1000.0,
        )

        assert calc.get_current_ledger("TEST001", "000001") == 1000.0
        assert calc.get_current_ledger("TEST001", "000002") == 0.0  # 不存在

    def test_get_state(self):
        """测试获取状态"""
        calc = LedgerRollingCalculator()

        calc.initialize_ledger(
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            initial_ledger=1000.0,
        )

        state = calc.get_state("TEST001", "000001")
        assert state is not None
        assert state.stock_name == "平安银行"

        # 不存在的状态
        state2 = calc.get_state("TEST001", "000002")
        assert state2 is None

    def test_get_all_states(self):
        """测试获取所有状态"""
        calc = LedgerRollingCalculator()

        calc.initialize_ledger("TEST001", "000001", initial_ledger=1000.0)
        calc.initialize_ledger("TEST001", "000002", initial_ledger=2000.0)
        calc.initialize_ledger("TEST002", "000001", initial_ledger=1500.0)

        states = calc.get_all_states()
        assert len(states) == 3

    def test_calculation_history(self):
        """测试计算历史"""
        calc = LedgerRollingCalculator()

        calc.initialize_ledger(
            account_id="TEST001",
            stock_code="000001",
            initial_ledger=1000.0,
            trade_date="20240101",
        )

        calc.roll(
            account_id="TEST001",
            stock_code="000001",
            adjustment_factor=1.0,
            adjustment_amount=50.0,
            trade_date="20240102",
        )

        history = calc.get_calculation_history("TEST001", "000001")
        assert len(history) == 1
        assert history[0]['previous_ledger'] == 1000.0
        assert history[0]['current_ledger'] == 1050.0
        assert 'calculation' in history[0]

    def test_reset(self):
        """测试重置"""
        calc = LedgerRollingCalculator()

        calc.initialize_ledger(
            account_id="TEST001",
            stock_code="000001",
            initial_ledger=1000.0,
        )

        calc.roll(
            account_id="TEST001",
            stock_code="000001",
            adjustment_factor=1.0,
            adjustment_amount=50.0,
            trade_date="20240102",
        )

        calc.reset("TEST001", "000001")

        state = calc.get_state("TEST001", "000001")
        assert state.current_ledger == 0.0
        assert state.previous_ledger == 0.0
        assert state.adjustment_factor == 1.0

    def test_clear(self):
        """测试清空"""
        calc = LedgerRollingCalculator()

        calc.initialize_ledger("TEST001", "000001", initial_ledger=1000.0)
        calc.initialize_ledger("TEST001", "000002", initial_ledger=2000.0)

        calc.clear()

        assert calc.get_all_states() == []

    def test_roll_validation(self):
        """测试参数验证"""
        calc = LedgerRollingCalculator()

        with pytest.raises(ValueError, match="account_id 不能为空"):
            calc.roll(
                account_id="",
                stock_code="000001",
            )

        with pytest.raises(ValueError, match="stock_code 不能为空"):
            calc.roll(
                account_id="TEST001",
                stock_code="",
            )


class TestAdjustmentFactorCalculation:
    """测试除权因子计算"""

    def test_no_adjustment(self):
        """测试无调整"""
        calc = LedgerRollingCalculator()
        af = calc.calculate_adjustment_factor()
        assert af == 1.0

    def test_bonus_share(self):
        """测试送股除权"""
        calc = LedgerRollingCalculator()

        # 10 送 3，即每 1 股送 0.3 股
        # AF = 1 / (1 + 0.3) = 0.7692...
        af = calc.calculate_adjustment_factor(bonus_ratio=0.3)
        assert abs(af - 1/1.3) < 0.0001

    def test_split(self):
        """测试拆细除权"""
        calc = LedgerRollingCalculator()

        # 1 拆 2
        # AF = 1 / 2 = 0.5
        af = calc.calculate_adjustment_factor(split_ratio=2.0)
        assert af == 0.5

    def test_dividend_only(self):
        """测试仅分红（不影响 AF）"""
        calc = LedgerRollingCalculator()

        # 分红通过 E_T 体现，不影响 AF
        af = calc.calculate_adjustment_factor(dividend_per_share=0.5)
        assert af == 1.0

    def test_rights_issue(self):
        """测试配股除权"""
        calc = LedgerRollingCalculator()

        # 10 配 3，配股价 5 元，当前价 10 元
        # 理论除权价 = (10 + 5×0.3) / (1+0.3) = 11.5/1.3 = 8.846...
        # AF = 8.846 / 10 = 0.8846...
        af = calc.calculate_adjustment_factor(
            rights_ratio=0.3,
            rights_price=5.0,
            current_price=10.0,
        )
        expected = ((10.0 + 5.0 * 0.3) / 1.3) / 10.0
        assert abs(af - expected) < 0.0001

    def test_combined_adjustment(self):
        """测试综合调整"""
        calc = LedgerRollingCalculator()

        # 10 送 2 且 1 拆 2
        # AF = 1/(1+0.2) × 1/2 = 0.8333... × 0.5 = 0.4166...
        af = calc.calculate_adjustment_factor(
            bonus_ratio=0.2,
            split_ratio=2.0,
        )
        expected = (1/1.2) * (1/2.0)
        assert abs(af - expected) < 0.0001


class TestAdjustmentAmountCalculation:
    """测试调整额计算"""

    def test_no_adjustment(self):
        """测试无调整"""
        calc = LedgerRollingCalculator()
        e_t = calc.calculate_adjustment_amount(previous_ledger=1000.0)
        assert e_t == 0.0

    def test_dividend(self):
        """测试分红调整额"""
        calc = LedgerRollingCalculator()

        # 每股分红 0.5 元，1000 股
        # E_T = 0.5 × 1000 = 500
        e_t = calc.calculate_adjustment_amount(
            previous_ledger=1000.0,
            dividend_per_share=0.5,
            total_shares=1000,
        )
        assert e_t == 500.0

    def test_special_adjustment(self):
        """测试特殊调整"""
        calc = LedgerRollingCalculator()

        e_t = calc.calculate_adjustment_amount(
            previous_ledger=1000.0,
            special_adjustment=100.0,
        )
        assert e_t == 100.0

    def test_combined_adjustment(self):
        """测试综合调整额"""
        calc = LedgerRollingCalculator()

        # 分红 + 特殊调整
        # E_T = 0.5×1000 + (-50) = 450
        e_t = calc.calculate_adjustment_amount(
            previous_ledger=1000.0,
            dividend_per_share=0.5,
            total_shares=1000,
            special_adjustment=-50.0,
        )
        assert e_t == 450.0


class TestAdjustmentEventManagement:
    """测试调整事件管理"""

    def test_add_adjustment_event(self):
        """测试添加调整事件"""
        calc = LedgerRollingCalculator()

        event = AdjustmentEvent(
            trade_date="20240101",
            stock_code="000001",
            adjustment_type=AdjustmentType.DIVIDEND,
            adjustment_factor=1.0,
            adjustment_amount=0.5,
        )

        calc.add_adjustment_event(event)

        events = calc.get_adjustment_history("000001")
        assert len(events) == 1
        assert events[0].adjustment_type == AdjustmentType.DIVIDEND

    def test_multiple_events(self):
        """测试多个事件"""
        calc = LedgerRollingCalculator()

        event1 = AdjustmentEvent(
            trade_date="20240101",
            stock_code="000001",
            adjustment_type=AdjustmentType.DIVIDEND,
        )

        event2 = AdjustmentEvent(
            trade_date="20240102",
            stock_code="000001",
            adjustment_type=AdjustmentType.BONUS_SHARE,
        )

        calc.add_adjustment_event(event1)
        calc.add_adjustment_event(event2)

        events = calc.get_adjustment_history("000001")
        assert len(events) == 2

    def test_roll_with_events(self):
        """测试带事件的滚动"""
        calc = LedgerRollingCalculator()

        event1 = AdjustmentEvent(
            trade_date="20240102",
            stock_code="000001",
            adjustment_type=AdjustmentType.SPLIT,
            adjustment_factor=0.5,
        )

        calc.add_adjustment_event(event1)

        calc.initialize_ledger(
            account_id="TEST001",
            stock_code="000001",
            initial_ledger=1000.0,
            trade_date="20240101",
        )

        # 从事件自动计算 AF
        state = calc.roll(
            account_id="TEST001",
            stock_code="000001",
            trade_date="20240102",
            events=[event1],
        )

        # Ledger_T = 1000 × 0.5 + 0 = 500
        assert state.current_ledger == 500.0


class TestMultiAccountAndStock:
    """测试多账户多证券"""

    def test_multiple_accounts(self):
        """测试多账户"""
        calc = LedgerRollingCalculator()

        calc.initialize_ledger("ACCOUNT1", "000001", initial_ledger=1000.0)
        calc.initialize_ledger("ACCOUNT2", "000001", initial_ledger=2000.0)

        assert calc.get_current_ledger("ACCOUNT1", "000001") == 1000.0
        assert calc.get_current_ledger("ACCOUNT2", "000001") == 2000.0

    def test_multiple_stocks(self):
        """测试多证券"""
        calc = LedgerRollingCalculator()

        calc.initialize_ledger("TEST001", "000001", initial_ledger=1000.0)
        calc.initialize_ledger("TEST001", "000002", initial_ledger=2000.0)

        assert calc.get_current_ledger("TEST001", "000001") == 1000.0
        assert calc.get_current_ledger("TEST001", "000002") == 2000.0

    def test_independent_rolling(self):
        """测试独立滚动"""
        calc = LedgerRollingCalculator()

        calc.initialize_ledger("TEST001", "000001", initial_ledger=1000.0)
        calc.initialize_ledger("TEST001", "000002", initial_ledger=2000.0)

        # 只对 000001 滚动
        calc.roll(
            account_id="TEST001",
            stock_code="000001",
            adjustment_factor=1.0,
            adjustment_amount=100.0,
        )

        # 000001: 1000 + 100 = 1100
        assert calc.get_current_ledger("TEST001", "000001") == 1100.0
        # 000002: 不变
        assert calc.get_current_ledger("TEST001", "000002") == 2000.0


class TestEdgeCases:
    """测试边界情况"""

    def test_zero_initial_ledger(self):
        """测试零初始台账"""
        calc = LedgerRollingCalculator()

        calc.initialize_ledger(
            account_id="TEST001",
            stock_code="000001",
            initial_ledger=0.0,
        )

        calc.roll(
            account_id="TEST001",
            stock_code="000001",
            adjustment_factor=1.0,
            adjustment_amount=100.0,
        )

        # 0 × 1.0 + 100 = 100
        assert calc.get_current_ledger("TEST001", "000001") == 100.0

    def test_negative_adjustment(self):
        """测试负调整"""
        calc = LedgerRollingCalculator()

        calc.initialize_ledger(
            account_id="TEST001",
            stock_code="000001",
            initial_ledger=1000.0,
        )

        calc.roll(
            account_id="TEST001",
            stock_code="000001",
            adjustment_factor=1.0,
            adjustment_amount=-100.0,
        )

        # 1000 × 1.0 + (-100) = 900
        assert calc.get_current_ledger("TEST001", "000001") == 900.0

    def test_very_small_adjustment_factor(self):
        """测试很小的除权因子"""
        calc = LedgerRollingCalculator()

        calc.initialize_ledger(
            account_id="TEST001",
            stock_code="000001",
            initial_ledger=1000.0,
        )

        calc.roll(
            account_id="TEST001",
            stock_code="000001",
            adjustment_factor=0.01,
            adjustment_amount=0.0,
        )

        # 1000 × 0.01 = 10
        assert calc.get_current_ledger("TEST001", "000001") == 10.0

    def test_consecutive_rolling(self):
        """测试连续滚动"""
        calc = LedgerRollingCalculator()

        calc.initialize_ledger(
            account_id="TEST001",
            stock_code="000001",
            initial_ledger=1000.0,
            trade_date="20240101",
        )

        # 连续 5 天滚动
        for i in range(2, 7):
            calc.roll(
                account_id="TEST001",
                stock_code="000001",
                adjustment_factor=1.0,
                adjustment_amount=100.0,
                trade_date=f"2024010{i}",
            )

        # 1000 + 100×5 = 1500
        assert calc.get_current_ledger("TEST001", "000001") == 1500.0


class TestIntegration:
    """集成测试"""

    def test_full_workflow(self):
        """测试完整工作流"""
        calc = LedgerRollingCalculator()

        # 1. 初始化台账
        state = calc.initialize_ledger(
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            initial_ledger=5000.0,
            trade_date="20240101",
        )
        assert state.current_ledger == 5000.0

        # 2. 添加分红事件
        dividend_event = AdjustmentEvent(
            trade_date="20240102",
            stock_code="000001",
            adjustment_type=AdjustmentType.DIVIDEND,
            adjustment_factor=1.0,
            adjustment_amount=0.5,
            description="每股分红 0.5 元",
        )
        calc.add_adjustment_event(dividend_event)

        # 3. 滚动 T+1
        calc.roll(
            account_id="TEST001",
            stock_code="000001",
            adjustment_factor=1.0,
            adjustment_amount=500.0,  # 分红总额
            trade_date="20240102",
        )
        assert calc.get_current_ledger("TEST001", "000001") == 5500.0

        # 4. 滚动 T+2（无调整）
        calc.roll(
            account_id="TEST001",
            stock_code="000001",
            adjustment_factor=1.0,
            adjustment_amount=0.0,
            trade_date="20240103",
        )
        assert calc.get_current_ledger("TEST001", "000001") == 5500.0

        # 5. 验证历史
        history = calc.get_calculation_history("TEST001", "000001")
        assert len(history) == 2  # 两次滚动


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
