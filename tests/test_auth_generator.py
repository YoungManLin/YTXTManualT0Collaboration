"""
授权文件生成器单元测试
"""

import pytest
import os
import tempfile
from datetime import datetime, timedelta
from src.auth_generator import AuthRecord, AuthGenerator


class TestAuthRecord:
    """测试 AuthRecord 类"""

    def test_create_record(self):
        """测试创建授权记录"""
        record = AuthRecord(
            trade_date="20240102",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            max_buy_volume=1000,
            max_sell_volume=800,
            max_buy_amount=10000.0,
            max_sell_amount=8400.0,
            max_position_ratio=0.2,
            max_position_volume=1200,
            risk_level="NORMAL",
            stop_loss_price=9.5,
            stop_profit_price=11.5,
            auth_status="ACTIVE",
            remark="测试备注",
        )

        assert record.trade_date == "20240102"
        assert record.account_id == "TEST001"
        assert record.stock_code == "000001"
        assert record.max_buy_volume == 1000
        assert record.risk_level == "NORMAL"
        assert record.auth_status == "ACTIVE"

    def test_record_key(self):
        """测试唯一键"""
        record = AuthRecord(
            trade_date="20240102",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
        )

        assert record.key == "20240102_TEST001_000001"

    def test_record_to_dict(self):
        """测试转换为字典"""
        record = AuthRecord(
            trade_date="20240102",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            max_buy_volume=1000,
            max_sell_volume=800,
            max_buy_amount=10000.0,
            max_sell_amount=8400.0,
            max_position_ratio=0.2,
            max_position_volume=1200,
            risk_level="NORMAL",
            stop_loss_price=9.5,
            stop_profit_price=11.5,
            auth_status="ACTIVE",
            remark="测试备注",
        )

        d = record.to_dict()
        assert d['trade_date'] == "20240102"
        assert d['account_id'] == "TEST001"
        assert d['stock_code'] == "000001"
        assert d['stock_name'] == "平安银行"
        assert d['market_id'] == "SZ"
        assert d['max_buy_volume'] == 1000
        assert d['max_sell_volume'] == 800
        assert d['max_position_ratio'] == 0.2
        assert d['risk_level'] == "NORMAL"
        assert d['auth_status'] == "ACTIVE"
        assert d['remark'] == "测试备注"

    def test_default_values(self):
        """测试默认值"""
        record = AuthRecord(
            trade_date="20240102",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
        )

        d = record.to_dict()
        assert d['max_buy_volume'] == 0
        assert d['max_sell_volume'] == 0
        assert d['max_buy_amount'] == 0.0
        assert d['max_sell_amount'] == 0.0
        assert d['max_position_ratio'] == 0.0
        assert d['risk_level'] == "NORMAL"
        assert d['auth_status'] == "ACTIVE"
        assert d['remark'] == ""


class TestAuthGenerator:
    """测试 AuthGenerator 类"""

    def test_create_generator(self):
        """测试创建授权生成器"""
        gen = AuthGenerator()
        assert len(gen.records) == 0
        assert gen.trade_date is None
        assert gen.default_max_position_ratio == 0.2
        assert gen.default_risk_level == "NORMAL"

    def test_create_generator_with_params(self):
        """测试创建带参数的生成器"""
        gen = AuthGenerator(
            default_max_position_ratio=0.3,
            default_risk_level="HIGH",
        )
        assert gen.default_max_position_ratio == 0.3
        assert gen.default_risk_level == "HIGH"

    def test_create_generator_with_dir(self):
        """测试创建带输出目录的生成器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = AuthGenerator(output_dir=tmpdir)
            assert str(gen.output_dir) == tmpdir

    def test_generate_auth_record(self):
        """测试生成授权记录"""
        gen = AuthGenerator()

        record = gen.generate_auth_record(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            current_price=10.5,
            trade_date="20240102",
        )

        assert len(gen.records) == 1
        assert record.stock_code == "000001"
        assert record.max_sell_volume == 800  # 卖出上限 = 可用数量
        assert gen.trade_date == "20240102"

    def test_generate_auth_record_auto_date(self):
        """测试自动生成交易日期"""
        gen = AuthGenerator()

        record = gen.generate_auth_record(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            current_price=10.5,
        )

        # 应该自动设置为明天
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
        assert record.trade_date == tomorrow

    def test_generate_auth_record_with_risk_level(self):
        """测试生成带风险等级的授权记录"""
        gen = AuthGenerator()

        # 测试 BLOCKED 状态
        record = gen.generate_auth_record(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            current_price=10.5,
            risk_level="BLOCKED",
        )

        assert record.risk_level == "BLOCKED"
        assert record.auth_status == "BLOCKED"
        assert record.max_buy_volume == 0
        assert record.max_sell_volume == 0

    def test_generate_auth_record_high_risk(self):
        """测试生成高风险授权记录"""
        gen = AuthGenerator()

        record = gen.generate_auth_record(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            current_price=10.5,
            risk_level="HIGH",
        )

        assert record.risk_level == "HIGH"
        assert record.auth_status == "LIMITED"

    def test_generate_auth_record_stop_loss_profit(self):
        """测试生成带止损止盈的授权记录"""
        gen = AuthGenerator()

        record = gen.generate_auth_record(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            current_price=10.0,
            stop_loss_ratio=0.05,
            stop_profit_ratio=0.10,
        )

        # 止损价 = 10.0 * (1 - 0.05) = 9.5
        assert abs(record.stop_loss_price - 9.5) < 0.01
        # 止盈价 = 10.0 * (1 + 0.10) = 11.0
        assert abs(record.stop_profit_price - 11.0) < 0.01

    def test_generate_multiple_records(self):
        """测试生成多条记录"""
        gen = AuthGenerator()

        gen.generate_auth_record(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            current_price=10.5,
            trade_date="20240102",
        )

        gen.generate_auth_record(
            stock_code="000002",
            stock_name="万科 A",
            account_id="TEST001",
            market_id="SZ",
            total_volume=500,
            available_volume=500,
            current_price=21.0,
            trade_date="20240102",
        )

        assert len(gen.records) == 2

    def test_get_records_by_account(self):
        """测试按账户获取记录"""
        gen = AuthGenerator()

        gen.generate_auth_record(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            current_price=10.5,
            trade_date="20240102",
        )

        gen.generate_auth_record(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST002",
            market_id="SZ",
            total_volume=500,
            available_volume=500,
            current_price=10.5,
            trade_date="20240102",
        )

        account1_records = gen.get_records_by_account("TEST001")
        assert len(account1_records) == 1

        account2_records = gen.get_records_by_account("TEST002")
        assert len(account2_records) == 1

    def test_get_records_by_stock(self):
        """测试按股票获取记录"""
        gen = AuthGenerator()

        gen.generate_auth_record(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            current_price=10.5,
            trade_date="20240102",
        )

        gen.generate_auth_record(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST002",
            market_id="SZ",
            total_volume=500,
            available_volume=500,
            current_price=10.5,
            trade_date="20240102",
        )

        gen.generate_auth_record(
            stock_code="000002",
            stock_name="万科 A",
            account_id="TEST001",
            market_id="SZ",
            total_volume=500,
            available_volume=500,
            current_price=21.0,
            trade_date="20240102",
        )

        stock1_records = gen.get_records_by_stock("000001")
        assert len(stock1_records) == 2

    def test_get_summary(self):
        """测试获取汇总"""
        gen = AuthGenerator()

        gen.generate_auth_record(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            current_price=10.5,
            trade_date="20240102",
            risk_level="NORMAL",
        )

        gen.generate_auth_record(
            stock_code="000002",
            stock_name="万科 A",
            account_id="TEST001",
            market_id="SZ",
            total_volume=500,
            available_volume=500,
            current_price=21.0,
            trade_date="20240102",
            risk_level="HIGH",
        )

        summary = gen.get_summary()
        assert summary['trade_date'] == "20240102"
        assert summary['record_count'] == 2
        assert summary['active_count'] == 1  # NORMAL = ACTIVE
        assert summary['limited_count'] == 1  # HIGH = LIMITED
        assert summary['blocked_count'] == 0
        assert summary['high_risk_count'] == 1
        assert summary['normal_risk_count'] == 1

    def test_get_summary_empty(self):
        """测试空汇总"""
        gen = AuthGenerator()

        summary = gen.get_summary()
        assert summary['record_count'] == 0
        assert summary['active_count'] == 0
        assert summary['blocked_count'] == 0
        assert summary['limited_count'] == 0

    def test_to_dataframe(self):
        """测试转换为 DataFrame"""
        gen = AuthGenerator()

        gen.generate_auth_record(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            current_price=10.5,
            trade_date="20240102",
        )

        df = gen.to_dataframe()
        assert len(df) == 1
        assert df.iloc[0]['stock_code'] == "000001"
        assert df.iloc[0]['account_id'] == "TEST001"

    def test_to_dataframe_empty(self):
        """测试空 DataFrame"""
        gen = AuthGenerator()
        df = gen.to_dataframe()
        assert df.empty

    def test_export_excel(self):
        """测试导出 Excel"""
        gen = AuthGenerator()

        gen.generate_auth_record(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            current_price=10.5,
            trade_date="20240102",
        )

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            temp_path = f.name

        try:
            result_path = gen.export(temp_path, format="excel")
            assert os.path.exists(result_path)
            assert result_path.endswith('.xlsx')
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_csv(self):
        """测试导出 CSV"""
        gen = AuthGenerator()

        gen.generate_auth_record(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            current_price=10.5,
            trade_date="20240102",
        )

        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            temp_path = f.name

        try:
            result_path = gen.export(temp_path, format="csv")
            assert os.path.exists(result_path)
            assert result_path.endswith('.csv')
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_empty_data(self):
        """测试导出空数据"""
        gen = AuthGenerator()

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="没有可导出的数据"):
                gen.export(temp_path, format="excel")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_clear(self):
        """测试清空"""
        gen = AuthGenerator()

        gen.generate_auth_record(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            current_price=10.5,
            trade_date="20240102",
        )

        assert len(gen.records) == 1
        gen.clear()
        assert len(gen.records) == 0
        assert gen.trade_date is None


class TestAuthGeneratorFromPositions:
    """测试 AuthGenerator 与持仓对象的集成"""

    def test_generate_from_positions(self):
        """测试从持仓列表批量生成"""
        from src.position import RealPosition

        gen = AuthGenerator()

        pos1 = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
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

        gen.generate_from_positions([pos1, pos2], trade_date="20240102")

        assert len(gen.records) == 2

    def test_generate_from_positions_with_risk_config(self):
        """测试带风险配置生成"""
        from src.position import RealPosition

        gen = AuthGenerator()

        pos1 = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            cost_price=10.0,
            current_price=10.5,
        )

        risk_config = {
            '000001': {
                'max_position_ratio': 0.3,
                'risk_level': 'HIGH',
                'stop_loss_ratio': 0.08,
            }
        }

        gen.generate_from_positions([pos1], trade_date="20240102", risk_config=risk_config)

        record = gen.records[0]
        assert record.risk_level == "HIGH"

    def test_generate_from_position_manager(self):
        """测试从持仓管理器生成"""
        from src.position import PositionManager, RealPosition

        gen = AuthGenerator()
        pm = PositionManager()

        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            cost_price=10.0,
            current_price=10.5,
        )

        account = pm.get_or_create_account("TEST001")
        account.add_position(pos)

        gen.generate_from_position_manager(pm, trade_date="20240102")

        assert len(gen.records) == 1


class TestAuthGeneratorDateHandling:
    """测试授权生成器的日期处理"""

    def test_trade_date_today_converts_to_tomorrow(self):
        """测试今天日期自动转为明天"""
        gen = AuthGenerator()

        today = datetime.now().strftime("%Y%m%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")

        record = gen.generate_auth_record(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            current_price=10.5,
            trade_date=today,
        )

        # 应该自动转换为明天
        assert record.trade_date == tomorrow

    def test_future_date_preserved(self):
        """测试未来日期保持不变"""
        gen = AuthGenerator()

        future_date = (datetime.now() + timedelta(days=5)).strftime("%Y%m%d")

        record = gen.generate_auth_record(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            current_price=10.5,
            trade_date=future_date,
        )

        assert record.trade_date == future_date


class TestAuthGeneratorDBFFields:
    """测试 DBF 字段定义"""

    def test_dbf_fields_defined(self):
        """测试 DBF 字段定义存在"""
        assert len(AuthGenerator.DBF_FIELDS) > 0
        assert 'ZQDM' in AuthGenerator.DBF_FIELDS  # 证券代码
        assert 'ZQJC' in AuthGenerator.DBF_FIELDS  # 证券简称
        assert 'ZJZH' in AuthGenerator.DBF_FIELDS  # 资金账号
        assert 'SC' in AuthGenerator.DBF_FIELDS    # 市场代码
        assert 'JYRQ' in AuthGenerator.DBF_FIELDS  # 交易日期
        assert 'MXSL' in AuthGenerator.DBF_FIELDS  # 买入数量上限
        assert 'MCSL' in AuthGenerator.DBF_FIELDS  # 卖出数量上限

    def test_column_names_defined(self):
        """测试中文列名定义存在"""
        assert len(AuthGenerator.COLUMN_NAMES) > 0
        assert AuthGenerator.COLUMN_NAMES['trade_date'] == '交易日期'
        assert AuthGenerator.COLUMN_NAMES['account_id'] == '资金账号'
        assert AuthGenerator.COLUMN_NAMES['stock_code'] == '证券代码'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
