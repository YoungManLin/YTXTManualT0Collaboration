"""
DBF 订单生成器单元测试
"""

import pytest
from src.order_gen import (
    DBFOrder, OrderBatch, OrderGenerator,
    OrderType, PriceType
)


class TestDBFOrder:
    """测试 DBFOrder 类"""

    def test_create_sell_order(self):
        """测试创建卖出订单"""
        order = DBFOrder(
            order_type='S',
            price_type='1',
            stock_code="000001",
            volume=1000,
            account_id="TEST001",
            mode_price=10.5,
        )

        assert order.order_type == 'S'
        assert order.stock_code == "000001"
        assert order.volume == 1000
        assert order.mode_price == 10.5

    def test_create_buy_order(self):
        """测试创建买入订单"""
        order = DBFOrder(
            order_type='B',
            price_type='1',
            stock_code="000001",
            volume=1000,
            account_id="TEST001",
            mode_price=10.0,
        )

        assert order.order_type == 'B'
        assert order.volume == 1000

    def test_order_key(self):
        """测试唯一键"""
        order = DBFOrder(
            order_type='S',
            price_type='1',
            stock_code="000001",
            volume=1000,
            account_id="TEST001",
        )

        assert order.key == "TEST001_000001_S"

    def test_to_dict(self):
        """测试转换为字典（中文列名）"""
        order = DBFOrder(
            order_type='S',
            price_type='1',
            stock_code="000001",
            volume=1000,
            account_id="TEST001",
            mode_price=10.5,
            strategy="T0 策略",
        )

        d = order.to_dict()
        assert d['下单类型'] == 'S'
        assert d['证券代码'] == "000001"
        assert d['委托价格'] == 10.5
        assert d['策略备注'] == "T0 策略"

    def test_validate_success(self):
        """测试验证成功"""
        order = DBFOrder(
            order_type='S',
            price_type='1',
            stock_code="000001",
            volume=1000,
            account_id="TEST001",
            mode_price=10.5,
        )

        errors = order.validate()
        assert len(errors) == 0

    def test_validate_missing_type(self):
        """测试验证缺少订单类型"""
        order = DBFOrder(
            order_type='',
            price_type='1',
            stock_code="000001",
            volume=1000,
            account_id="TEST001",
        )

        errors = order.validate()
        assert any("下单类型" in e for e in errors)

    def test_validate_invalid_type(self):
        """测试验证无效订单类型"""
        order = DBFOrder(
            order_type='X',
            price_type='1',
            stock_code="000001",
            volume=1000,
            account_id="TEST001",
        )

        errors = order.validate()
        assert any("无效的下单类型" in e for e in errors)

    def test_validate_invalid_price_type(self):
        """测试验证无效价格类型"""
        order = DBFOrder(
            order_type='S',
            price_type='9',
            stock_code="000001",
            volume=1000,
            account_id="TEST001",
        )

        errors = order.validate()
        assert any("无效的委托价格类型" in e for e in errors)

    def test_validate_missing_stock(self):
        """测试验证缺少证券代码"""
        order = DBFOrder(
            order_type='S',
            price_type='1',
            stock_code="",
            volume=1000,
            account_id="TEST001",
        )

        errors = order.validate()
        assert any("证券代码" in e for e in errors)

    def test_validate_invalid_volume(self):
        """测试验证无效数量"""
        order = DBFOrder(
            order_type='S',
            price_type='1',
            stock_code="000001",
            volume=0,
            account_id="TEST001",
        )

        errors = order.validate()
        assert any("委托数量" in e for e in errors)

    def test_validate_buy_volume_multiple(self):
        """测试验证买入数量为 100 倍数"""
        order = DBFOrder(
            order_type='B',
            price_type='1',
            stock_code="000001",
            volume=150,  # 不是 100 的倍数
            account_id="TEST001",
        )

        errors = order.validate()
        assert any("100 的整数倍" in e for e in errors)

    def test_validate_limit_price_required(self):
        """测试验证限价委托需要价格"""
        order = DBFOrder(
            order_type='S',
            price_type='1',  # 限价委托
            stock_code="000001",
            volume=1000,
            account_id="TEST001",
            mode_price=None,
        )

        errors = order.validate()
        assert any("限价委托必须指定价格" in e for e in errors)

    def test_validate_invalid_price(self):
        """测试验证无效价格"""
        order = DBFOrder(
            order_type='S',
            price_type='1',
            stock_code="000001",
            volume=1000,
            account_id="TEST001",
            mode_price=-10.0,
        )

        errors = order.validate()
        assert any("无效的委托价格" in e for e in errors)


class TestOrderBatch:
    """测试 OrderBatch 类"""

    def test_create_batch(self):
        """测试创建批次"""
        batch = OrderBatch(batch_id="BATCH001", description="测试批次")

        assert batch.batch_id == "BATCH001"
        assert batch.description == "测试批次"
        assert len(batch.orders) == 0

    def test_add_order(self):
        """测试添加订单"""
        batch = OrderBatch(batch_id="BATCH001")

        order = DBFOrder(
            order_type='S',
            price_type='1',
            stock_code="000001",
            volume=1000,
            account_id="TEST001",
        )

        batch.add_order(order)
        assert len(batch.orders) == 1
        assert order.batch_id == "BATCH001"

    def test_batch_summary(self):
        """测试批次汇总"""
        batch = OrderBatch(batch_id="BATCH001")

        # 添加买卖订单
        batch.add_order(DBFOrder(
            order_type='B',
            price_type='1',
            stock_code="000001",
            volume=1000,
            account_id="TEST001",
        ))
        batch.add_order(DBFOrder(
            order_type='S',
            price_type='1',
            stock_code="000001",
            volume=1000,
            account_id="TEST001",
        ))

        summary = batch.get_summary()
        assert summary['total_orders'] == 2
        assert summary['buy_orders'] == 1
        assert summary['sell_orders'] == 1
        assert summary['buy_volume'] == 1000
        assert summary['sell_volume'] == 1000


class TestOrderGenerator:
    """测试 OrderGenerator 类"""

    def test_create_generator(self):
        """测试创建生成器"""
        gen = OrderGenerator()
        assert gen.default_price_type == '1'
        assert len(gen.batches) == 0

    def test_create_batch(self):
        """测试创建批次"""
        gen = OrderGenerator()
        batch = gen.create_batch(description="测试批次")

        assert batch.batch_id.startswith("BATCH_")
        assert batch.description == "测试批次"
        assert batch.batch_id in gen.batches

    def test_create_batch_with_id(self):
        """测试创建指定 ID 的批次"""
        gen = OrderGenerator()
        batch = gen.create_batch(batch_id="MY_BATCH", description="测试")

        assert batch.batch_id == "MY_BATCH"
        assert "MY_BATCH" in gen.batches

    def test_generate_sell_order(self):
        """测试生成卖出订单"""
        gen = OrderGenerator()
        order = gen.generate_sell_order(
            stock_code="000001",
            account_id="TEST001",
            volume=1000,
            price=10.5,
            strategy="T0 卖出",
        )

        assert order.order_type == 'S'
        assert order.stock_code == "000001"
        assert order.volume == 1000
        assert order.mode_price == 10.5
        assert order.strategy == "T0 卖出"

    def test_generate_buy_order(self):
        """测试生成买入订单"""
        gen = OrderGenerator()
        order = gen.generate_buy_order(
            stock_code="000001",
            account_id="TEST001",
            volume=1000,
            price=10.0,
        )

        assert order.order_type == 'B'
        assert order.volume == 1000

    def test_generate_t0_sell_first_orders(self):
        """测试生成先卖后买 T0 订单对"""
        gen = OrderGenerator()
        orders = gen.generate_t0_sell_first_orders(
            stock_code="000001",
            account_id="TEST001",
            volume=500,
            sell_price=10.5,
            buy_price=10.0,
            strategy="T0-先卖后买",
        )

        assert len(orders) == 2
        assert orders[0].order_type == 'S'
        assert orders[0].mode_price == 10.5
        assert orders[1].order_type == 'B'
        assert orders[1].mode_price == 10.0
        assert orders[0].strategy == "T0-先卖后买"

    def test_generate_t0_buy_first_orders(self):
        """测试生成先买后卖 T0 订单对"""
        gen = OrderGenerator()
        orders = gen.generate_t0_buy_first_orders(
            stock_code="000001",
            account_id="TEST001",
            volume=500,
            buy_price=10.0,
            sell_price=10.5,
            strategy="T0-先买后卖",
        )

        assert len(orders) == 2
        assert orders[0].order_type == 'B'
        assert orders[0].mode_price == 10.0
        assert orders[1].order_type == 'S'
        assert orders[1].mode_price == 10.5

    def test_add_order_to_batch(self):
        """测试添加订单到批次"""
        gen = OrderGenerator()
        batch = gen.create_batch(batch_id="BATCH001")

        order = gen.generate_sell_order(
            stock_code="000001",
            account_id="TEST001",
            volume=1000,
            price=10.5,
        )

        result = gen.add_order(order, batch_id="BATCH001")
        assert result == True
        assert len(batch.orders) == 1

    def test_add_invalid_order(self):
        """测试添加无效订单"""
        gen = OrderGenerator()

        order = DBFOrder(
            order_type='',  # 无效
            price_type='1',
            stock_code="000001",
            volume=1000,
            account_id="TEST001",
        )

        result = gen.add_order(order)
        assert result == False
        assert len(gen.errors) > 0

    def test_add_order_to_nonexistent_batch(self):
        """测试添加到不存在的批次"""
        gen = OrderGenerator()

        order = gen.generate_sell_order(
            stock_code="000001",
            account_id="TEST001",
            volume=1000,
            price=10.5,
        )

        result = gen.add_order(order, batch_id="NOT_EXIST")
        assert result == False
        assert any("批次不存在" in e for e in gen.errors)

    def test_get_summary(self):
        """测试获取汇总"""
        gen = OrderGenerator()
        batch = gen.create_batch(batch_id="BATCH001")

        # 添加订单
        gen.add_order(gen.generate_sell_order(
            stock_code="000001",
            account_id="TEST001",
            volume=1000,
            price=10.5,
        ), batch_id="BATCH001")

        gen.add_order(gen.generate_buy_order(
            stock_code="000001",
            account_id="TEST001",
            volume=1000,
            price=10.0,
        ), batch_id="BATCH001")

        summary = gen.get_summary()
        assert summary['total_orders'] == 2
        assert summary['buy_orders'] == 1
        assert summary['sell_orders'] == 1
        assert summary['batches'] == 1

    def test_to_dataframe(self):
        """测试转换为 DataFrame"""
        gen = OrderGenerator()
        batch = gen.create_batch(batch_id="BATCH001")

        gen.add_order(gen.generate_sell_order(
            stock_code="000001",
            account_id="TEST001",
            volume=1000,
            price=10.5,
        ), batch_id="BATCH001")

        df = gen.to_dataframe()
        assert len(df) == 1
        assert df.iloc[0]['证券代码'] == "000001"

    def test_empty_dataframe(self):
        """测试空 DataFrame"""
        gen = OrderGenerator()
        df = gen.to_dataframe()
        assert df.empty


class TestOrderExport:
    """测试订单导出功能"""

    def test_validate_all(self):
        """测试批量验证"""
        gen = OrderGenerator()
        batch = gen.create_batch(batch_id="BATCH001")

        # 添加有效订单
        gen.add_order(gen.generate_sell_order(
            stock_code="000001",
            account_id="TEST001",
            volume=1000,
            price=10.5,
        ), batch_id="BATCH001")

        result = gen.validate_all()
        assert result == True

    def test_validate_with_errors(self):
        """测试批量验证（有错误）"""
        gen = OrderGenerator()

        # 手动添加无效订单
        invalid_order = DBFOrder(
            order_type='',
            price_type='1',
            stock_code="",
            volume=0,
            account_id="",
        )
        gen.orders.append(invalid_order)

        result = gen.validate_all()
        assert result == False
        assert len(gen.errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
