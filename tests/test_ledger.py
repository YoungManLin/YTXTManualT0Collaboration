"""
台账记录模块单元测试
"""

import pytest
import os
import tempfile
from datetime import datetime
from src.ledger import LedgerRecord, LedgerManager


class TestLedgerRecord:
    """测试 LedgerRecord 类"""

    def test_create_record(self):
        """测试创建台账记录"""
        record = LedgerRecord(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            frozen_volume=200,
            yesterday_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        assert record.trade_date == "20240101"
        assert record.account_id == "TEST001"
        assert record.stock_code == "000001"
        assert record.total_volume == 1000
        assert record.cost_price == 10.0
        assert record.current_price == 10.5

    def test_record_key(self):
        """测试唯一键"""
        record = LedgerRecord(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            frozen_volume=0,
            yesterday_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        assert record.key == "20240101_TEST001_000001"

    def test_record_to_dict(self):
        """测试转换为字典"""
        record = LedgerRecord(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            frozen_volume=200,
            yesterday_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        d = record.to_dict()
        assert d['trade_date'] == "20240101"
        assert d['account_id'] == "TEST001"
        assert d['stock_code'] == "000001"
        assert d['stock_name'] == "平安银行"
        assert d['market_id'] == "SZ"
        assert d['total_volume'] == 1000
        assert d['available_volume'] == 800
        assert d['frozen_volume'] == 200
        assert d['yesterday_volume'] == 1000
        assert d['cost_price'] == 10.0
        assert d['current_price'] == 10.5
        assert 'market_value' in d
        assert 'cost_amount' in d
        assert 'profit_loss' in d
        assert 'profit_rate' in d
        assert 'record_time' in d

    def test_calculated_fields(self):
        """测试计算字段"""
        manager = LedgerManager()
        manager.add_record(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            frozen_volume=0,
            yesterday_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        record = manager.records[0]
        d = record.to_dict()
        # 市值 = 1000 * 10.5 = 10500
        assert d['market_value'] == 10500.0
        # 成本 = 1000 * 10.0 = 10000
        assert d['cost_amount'] == 10000.0
        # 盈亏 = (10.5 - 10.0) * 1000 = 500
        assert d['profit_loss'] == 500.0
        # 盈亏率 = 500 / 10000 * 100 = 5%
        assert d['profit_rate'] == 5.0

    def test_default_values(self):
        """测试默认值"""
        record = LedgerRecord(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            total_volume=0,
            available_volume=0,
            frozen_volume=0,
            yesterday_volume=0,
            cost_price=0.0,
            current_price=0.0,
        )

        d = record.to_dict()
        assert d['market_value'] == 0.0
        assert d['cost_amount'] == 0.0
        assert d['profit_loss'] == 0.0
        assert d['profit_rate'] == 0.0


class TestLedgerManager:
    """测试 LedgerManager 类"""

    def test_create_manager(self):
        """测试创建台账管理器"""
        manager = LedgerManager()
        assert len(manager.records) == 0
        assert manager.trade_date is None

    def test_create_manager_with_dir(self):
        """测试创建带输出目录的管理器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LedgerManager(output_dir=tmpdir)
            assert str(manager.output_dir) == tmpdir

    def test_add_record(self):
        """测试添加记录"""
        manager = LedgerManager()

        record = manager.add_record(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            frozen_volume=200,
            yesterday_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        assert len(manager.records) == 1
        assert manager.trade_date == "20240101"
        assert record.stock_code == "000001"

    def test_add_multiple_records(self):
        """测试添加多条记录"""
        manager = LedgerManager()

        manager.add_record(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            frozen_volume=200,
            yesterday_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        manager.add_record(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000002",
            stock_name="万科 A",
            market_id="SZ",
            total_volume=500,
            available_volume=500,
            frozen_volume=0,
            yesterday_volume=500,
            cost_price=20.0,
            current_price=21.0,
        )

        assert len(manager.records) == 2

    def test_get_records_by_account(self):
        """测试按账户获取记录"""
        manager = LedgerManager()

        manager.add_record(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            frozen_volume=0,
            yesterday_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        manager.add_record(
            trade_date="20240101",
            account_id="TEST002",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            total_volume=500,
            available_volume=500,
            frozen_volume=0,
            yesterday_volume=500,
            cost_price=10.0,
            current_price=10.5,
        )

        account1_records = manager.get_records_by_account("TEST001")
        assert len(account1_records) == 1

        account2_records = manager.get_records_by_account("TEST002")
        assert len(account2_records) == 1

    def test_get_records_by_stock(self):
        """测试按股票获取记录"""
        manager = LedgerManager()

        manager.add_record(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            frozen_volume=0,
            yesterday_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        manager.add_record(
            trade_date="20240101",
            account_id="TEST002",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            total_volume=500,
            available_volume=500,
            frozen_volume=0,
            yesterday_volume=500,
            cost_price=10.0,
            current_price=10.5,
        )

        manager.add_record(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000002",
            stock_name="万科 A",
            market_id="SZ",
            total_volume=500,
            available_volume=500,
            frozen_volume=0,
            yesterday_volume=500,
            cost_price=20.0,
            current_price=21.0,
        )

        stock1_records = manager.get_records_by_stock("000001")
        assert len(stock1_records) == 2

    def test_get_summary(self):
        """测试获取汇总"""
        manager = LedgerManager()

        manager.add_record(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            frozen_volume=0,
            yesterday_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        manager.add_record(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000002",
            stock_name="万科 A",
            market_id="SZ",
            total_volume=500,
            available_volume=500,
            frozen_volume=0,
            yesterday_volume=500,
            cost_price=20.0,
            current_price=21.0,
        )

        summary = manager.get_summary()
        assert summary['trade_date'] == "20240101"
        assert summary['record_count'] == 2
        # 市值 = 1000*10.5 + 500*21 = 10500 + 10500 = 21000
        assert summary['total_market_value'] == 21000.0
        # 成本 = 1000*10 + 500*20 = 10000 + 10000 = 20000
        assert summary['total_cost'] == 20000.0
        # 盈亏 = 500 + 500 = 1000
        assert summary['total_profit_loss'] == 1000.0
        assert summary['unique_accounts'] == 1
        assert summary['unique_stocks'] == 2

    def test_get_summary_empty(self):
        """测试空汇总"""
        manager = LedgerManager()

        summary = manager.get_summary()
        assert summary['record_count'] == 0
        assert summary['total_market_value'] == 0.0
        assert summary['total_cost'] == 0.0
        assert summary['unique_accounts'] == 0
        assert summary['unique_stocks'] == 0

    def test_to_dataframe(self):
        """测试转换为 DataFrame"""
        manager = LedgerManager()

        manager.add_record(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            frozen_volume=0,
            yesterday_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        df = manager.to_dataframe()
        assert len(df) == 1
        assert df.iloc[0]['stock_code'] == "000001"
        assert df.iloc[0]['total_volume'] == 1000

    def test_to_dataframe_empty(self):
        """测试空 DataFrame"""
        manager = LedgerManager()
        df = manager.to_dataframe()
        assert df.empty

    def test_export_excel(self):
        """测试导出 Excel"""
        manager = LedgerManager()

        manager.add_record(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            frozen_volume=0,
            yesterday_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            temp_path = f.name

        try:
            result_path = manager.export(temp_path)
            assert os.path.exists(result_path)
            assert result_path.endswith('.xlsx')
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_csv(self):
        """测试导出 CSV"""
        manager = LedgerManager()

        manager.add_record(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            frozen_volume=0,
            yesterday_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            temp_path = f.name

        try:
            result_path = manager.export_csv(temp_path)
            assert os.path.exists(result_path)
            assert result_path.endswith('.csv')
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_empty_data(self):
        """测试导出空数据"""
        manager = LedgerManager()

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="没有可导出的数据"):
                manager.export(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_clear(self):
        """测试清空"""
        manager = LedgerManager()

        manager.add_record(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            frozen_volume=0,
            yesterday_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        assert len(manager.records) == 1
        manager.clear()
        assert len(manager.records) == 0
        assert manager.trade_date is None

    def test_auto_generate_filename(self):
        """测试自动生成文件名"""
        manager = LedgerManager()

        manager.add_record(
            trade_date="20240101",
            account_id="TEST001",
            stock_code="000001",
            stock_name="平安银行",
            market_id="SZ",
            total_volume=1000,
            available_volume=1000,
            frozen_volume=0,
            yesterday_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_ledger.xlsx")
            result_path = manager.export(output_path)
            assert os.path.exists(result_path)


class TestLedgerManagerWithPositions:
    """测试 LedgerManager 与持仓对象的集成"""

    def test_add_records_from_positions(self):
        """测试从持仓列表批量添加记录"""
        from src.position import RealPosition

        manager = LedgerManager()

        pos1 = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            frozen_volume=200,
            yesterday_volume=1000,
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
            frozen_volume=0,
            yesterday_volume=500,
            cost_price=20.0,
            current_price=21.0,
        )

        manager.add_records_from_positions([pos1, pos2], trade_date="20240101")

        assert len(manager.records) == 2
        assert manager.trade_date == "20240101"

    def test_load_from_cctj_result(self):
        """测试从 CCTJ 解析结果加载"""
        from src.cctj_parser import CCTJPosition, CCTJParseResult
        from datetime import datetime

        manager = LedgerManager()

        pos = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
            total_volume=1000,
            available_volume=800,
            frozen_volume=200,
            yesterday_volume=1000,
            cost_price=10.0,
            current_price=10.5,
            trade_date="20240101",
        )

        result = CCTJParseResult(
            positions=[pos],
            file_path="/path/to/file.cctj",
            parse_time=datetime.now(),
            trade_date="20240101",
        )

        manager.load_from_cctj_result(result)

        assert len(manager.records) == 1
        assert manager.trade_date == "20240101"

    def test_load_from_position_manager(self):
        """测试从持仓管理器加载"""
        from src.position import PositionManager, RealPosition

        manager = LedgerManager()
        pm = PositionManager()

        pos = RealPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            total_volume=1000,
            available_volume=800,
            frozen_volume=200,
            yesterday_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        account = pm.get_or_create_account("TEST001")
        account.add_position(pos)

        manager.load_from_position_manager(pm, trade_date="20240101")

        assert len(manager.records) == 1


class TestLedgerColumns:
    """测试台账列"""

    def test_columns_defined(self):
        """测试列定义存在"""
        assert len(LedgerManager.COLUMNS) > 0
        assert 'trade_date' in LedgerManager.COLUMNS
        assert 'account_id' in LedgerManager.COLUMNS
        assert 'stock_code' in LedgerManager.COLUMNS
        assert 'total_volume' in LedgerManager.COLUMNS

    def test_column_names_defined(self):
        """测试中文列名定义存在"""
        assert len(LedgerManager.COLUMN_NAMES) > 0
        assert LedgerManager.COLUMN_NAMES['trade_date'] == '交易日期'
        assert LedgerManager.COLUMN_NAMES['account_id'] == '账户 ID'
        assert LedgerManager.COLUMN_NAMES['stock_code'] == '证券代码'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
