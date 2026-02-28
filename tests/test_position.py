"""
持仓管理模块单元测试
"""

import pytest
from datetime import datetime
from src.position import (
    RealPosition, VirtualPosition, AccountPosition, PositionManager,
    PositionStatus, PositionSide
)


class TestRealPosition:
    """测试 RealPosition 类"""

    def test_create_position(self):
        """测试创建持仓"""
        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        assert pos.stock_code == "000001"
        assert pos.total_volume == 1000
        assert pos.sellable_volume == 1000
        assert pos.market_value == 1000 * 10.5
        assert pos.cost_amount == 1000 * 10.0
        assert pos.profit_loss == (10.5 - 10.0) * 1000

    def test_position_key(self):
        """测试唯一键"""
        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
        )
        assert pos.key == "000001_TEST001"

    def test_update_price(self):
        """测试更新价格"""
        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            cost_price=10.0,
        )

        pos.update_price(11.0)
        assert pos.current_price == 11.0
        assert pos.market_value == 11000
        assert pos.profit_loss == 1000

    def test_freeze_unfreeze(self):
        """测试冻结和解冻"""
        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
        )

        # 测试冻结
        assert pos.freeze(300) == True
        assert pos.available_volume == 700
        assert pos.frozen_volume == 300
        assert pos.sellable_volume == 700

        # 测试超额冻结失败
        assert pos.freeze(800) == False

        # 测试解冻
        assert pos.unfreeze(200) == True
        assert pos.available_volume == 900
        assert pos.frozen_volume == 100

    def test_reduce(self):
        """测试减少持仓"""
        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            cost_price=10.0,
        )

        assert pos.cost_amount == 10000  # 1000 * 10.0
        assert pos.reduce(300) == True
        assert pos.total_volume == 700
        assert pos.available_volume == 700
        assert pos.cost_amount == 7000  # 700 * 10.0

        # 测试超额卖出失败
        assert pos.reduce(800) == False

    def test_increase(self):
        """测试增加持仓"""
        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            cost_price=10.0,
        )

        assert pos.cost_amount == 10000  # 1000 * 10.0
        assert pos.increase(500, 11.0) == True
        assert pos.total_volume == 1500
        assert pos.today_volume == 500
        assert pos.cost_amount == 10000 + 500 * 11.0
        # 加权平均成本
        assert abs(pos.cost_price - (15500 / 1500)) < 0.01

    def test_frozen_sellable(self):
        """测试冻结状态下可卖数量"""
        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            status=PositionStatus.FROZEN,
        )

        assert pos.sellable_volume == 0


class TestVirtualPosition:
    """测试 VirtualPosition 类"""

    def test_create_virtual_position(self):
        """测试创建虚拟持仓"""
        vp = VirtualPosition(
            position_id="VP001",
            stock_code="000001",
            account_id="TEST001",
        )

        assert vp.stock_code == "000001"
        assert vp.open_volume == 0
        assert vp.remaining_volume == 0
        assert vp.is_closed == True

    def test_open_and_close(self):
        """测试开仓和平仓"""
        vp = VirtualPosition(
            position_id="VP001",
            stock_code="000001",
            account_id="TEST001",
        )

        # 先卖后开：卖出价 10 元，买入价 9.5 元
        vp.open(1000, 10.0, t0_type="SELL_FIRST")
        assert vp.open_volume == 1000
        assert vp.remaining_volume == 1000
        assert vp.status == PositionStatus.ACTIVE

        # 平仓
        profit = vp.close_all(9.5)
        assert vp.is_closed == True
        assert vp.status == PositionStatus.CLOSED
        assert vp.remaining_volume == 0
        # 先卖后买盈利：(10 - 9.5) * 1000 = 500
        assert vp.profit_loss == 500

    def test_sell_first_profit(self):
        """测试先卖后买盈亏计算"""
        vp = VirtualPosition(
            position_id="VP001",
            stock_code="000001",
            account_id="TEST001",
        )

        vp.open(1000, 10.0, t0_type="SELL_FIRST")
        profit = vp.close_all(9.0)
        # (10 - 9) * 1000 = 1000
        assert profit == 1000
        assert vp.profit_loss == 1000

    def test_buy_first_profit(self):
        """测试先买后卖盈亏计算"""
        vp = VirtualPosition(
            position_id="VP001",
            stock_code="000001",
            account_id="TEST001",
        )

        vp.open(1000, 9.0, t0_type="BUY_FIRST")
        profit = vp.close_all(10.0)
        # (10 - 9) * 1000 = 1000
        assert profit == 1000
        assert vp.profit_loss == 1000

    def test_partial_close(self):
        """测试部分平仓"""
        vp = VirtualPosition(
            position_id="VP001",
            stock_code="000001",
            account_id="TEST001",
        )

        vp.open(1000, 10.0, t0_type="SELL_FIRST")

        # 部分平仓 500
        profit1 = vp.close_partial(500, 9.5)
        assert profit1 == (10.0 - 9.5) * 500
        assert vp.remaining_volume == 500
        assert vp.is_closed == False

        # 继续平仓剩余
        profit2 = vp.close_all(9.0)
        assert profit2 == (10.0 - 9.0) * 500
        assert vp.is_closed == True


class TestAccountPosition:
    """测试 AccountPosition 类"""

    def test_account_summary(self):
        """测试账户汇总"""
        account = AccountPosition(account_id="TEST001")

        # 添加真实持仓
        pos1 = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )
        pos2 = RealPosition(
            stock_code="000002",
            stock_name="万科 A",
            account_id="TEST001",
            market_id="SZ",
            total_volume=500,
            available_volume=500,
            cost_price=20.0,
            current_price=21.0,
        )

        account.add_position(pos1)
        account.add_position(pos2)

        assert account.total_market_value == 1000 * 10.5 + 500 * 21.0
        assert account.total_cost == 1000 * 10.0 + 500 * 20.0
        assert len(account.positions) == 2


class TestPositionManager:
    """测试 PositionManager 类"""

    def test_create_manager(self):
        """测试创建管理器"""
        pm = PositionManager()
        assert len(pm.accounts) == 0

    def test_get_or_create_account(self):
        """测试获取或创建账户"""
        pm = PositionManager()
        account = pm.get_or_create_account("TEST001")
        assert account.account_id == "TEST001"
        assert "TEST001" in pm.accounts

    def test_add_position(self):
        """测试添加持仓"""
        pm = PositionManager()

        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        account = pm.get_or_create_account("TEST001")
        account.add_position(pos)

        assert pm.get_position("TEST001", "000001") is not None
        assert pm.get_sellable_volume("TEST001", "000001") == 1000

    def test_update_price(self):
        """测试更新价格"""
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

        pm.update_price("000001", 11.0)
        updated_pos = pm.get_position("TEST001", "000001")
        assert updated_pos.current_price == 11.0
        assert updated_pos.market_value == 11000

    def test_execute_t0_sell_first(self):
        """测试执行先卖后买 T0"""
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

        # 执行 T0：卖出价 10.5，买入价 10.0
        vp = pm.execute_t0_sell_first(
            account_id="TEST001",
            stock_code="000001",
            volume=500,
            sell_price=10.5,
            buy_price=10.0,
        )

        assert vp is not None
        assert vp.t0_type == "SELL_FIRST"
        assert vp.profit_loss == (10.5 - 10.0) * 500  # 盈利 250

        # 检查持仓变化
        updated_pos = pm.get_position("TEST001", "000001")
        # 卖出 500 后又买入 500，持仓数量不变，但成本可能变化
        assert updated_pos.total_volume == 1000

    def test_execute_t0_insufficient_volume(self):
        """测试持仓不足时 T0 失败"""
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

        # 尝试 T0 1000 股（超过持仓）
        vp = pm.execute_t0_sell_first(
            account_id="TEST001",
            stock_code="000001",
            volume=1000,
            sell_price=10.5,
            buy_price=10.0,
        )

        assert vp is None

    def test_get_summary(self):
        """测试获取汇总"""
        pm = PositionManager()

        # 添加两个账户
        for acc_id in ["TEST001", "TEST002"]:
            pos = RealPosition(
                stock_code="000001",
                stock_name="平安银行",
                account_id=acc_id,
                market_id="SZ",
                total_volume=1000,
                available_volume=1000,
                cost_price=10.0,
                current_price=10.5,
            )
            account = pm.get_or_create_account(acc_id)
            account.add_position(pos)

        summary = pm.get_summary()
        assert summary['account_count'] == 2
        assert summary['total_positions'] == 2
        assert summary['total_market_value'] == 2 * 1000 * 10.5


class TestPositionValidation:
    """测试持仓验证"""

    def test_position_to_dict(self):
        """测试转换为字典"""
        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
        )

        d = pos.to_dict()
        assert d['stock_code'] == "000001"
        assert d['total_volume'] == 1000
        assert d['status'] == PositionStatus.ACTIVE.value

    def test_virtual_position_to_dict(self):
        """测试虚拟持仓转换为字典"""
        vp = VirtualPosition(
            position_id="VP001",
            stock_code="000001",
            account_id="TEST001",
        )
        vp.open(1000, 10.0)

        d = vp.to_dict()
        assert d['position_id'] == "VP001"
        assert d['open_volume'] == 1000
        assert d['t0_type'] == "SELL_FIRST"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
