"""
CCTJ 解析器模块单元测试
"""

import pytest
import os
from pathlib import Path
from src.cctj_parser import (
    CCTJParser, CCTJPosition, CCTJParseResult,
    CCTJError, CCTJFileNotFoundError, CCTJFormatError
)


class TestCCTJPosition:
    """测试 CCTJPosition 类"""

    def test_create_position(self):
        """测试创建仓位"""
        pos = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
            total_volume=1000,
            available_volume=1000,
            cost_price=10.0,
            current_price=10.5,
        )

        assert pos.stock_code == "000001"
        assert pos.stock_name == "平安银行"
        assert pos.account_id == "TEST001"
        assert pos.key == "000001_TEST001"

    def test_position_key(self):
        """测试唯一键"""
        pos = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
        )
        assert pos.key == "000001_TEST001"

    def test_to_dict(self):
        """测试转换为字典"""
        pos = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
            total_volume=1000,
        )

        d = pos.to_dict()
        assert d['stock_code'] == "000001"
        assert d['stock_name'] == "平安银行"
        assert d['total_volume'] == 1000
        assert d['position_type'] == "REAL"

    def test_validate_success(self):
        """测试验证成功"""
        pos = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
            total_volume=1000,
            available_volume=800,
            frozen_volume=200,
            cost_price=10.0,
            current_price=10.5,
        )

        errors = pos.validate()
        assert len(errors) == 0

    def test_validate_empty_stock(self):
        """测试验证空证券代码"""
        pos = CCTJPosition(
            stock_code="",
            stock_name="",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
        )

        errors = pos.validate()
        assert any("证券代码不能为空" in e for e in errors)

    def test_validate_empty_account(self):
        """测试验证空资金账号"""
        pos = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="",
            market_id="SZ",
            position_type="REAL",
        )

        errors = pos.validate()
        assert any("资金账号不能为空" in e for e in errors)

    def test_validate_negative_volume(self):
        """测试验证负数持仓"""
        pos = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
            total_volume=-100,
        )

        errors = pos.validate()
        assert any("总持仓不能为负数" in e for e in errors)

    def test_validate_negative_available(self):
        """测试验证负数可用数量"""
        pos = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
            total_volume=1000,
            available_volume=-100,
        )

        errors = pos.validate()
        assert any("可用数量不能为负数" in e for e in errors)

    def test_validate_negative_frozen(self):
        """测试验证负数冻结数量"""
        pos = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
            total_volume=1000,
            available_volume=1000,
            frozen_volume=-100,
        )

        errors = pos.validate()
        assert any("冻结数量不能为负数" in e for e in errors)

    def test_validate_volume_relation(self):
        """测试验证数量关系"""
        pos = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
            total_volume=500,
            available_volume=400,
            frozen_volume=200,  # 可用 + 冻结 > 总持仓
        )

        errors = pos.validate()
        assert any("可用 + 冻结 > 总持仓" in e for e in errors)

    def test_validate_negative_cost_price(self):
        """测试验证负数成本价"""
        pos = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
            cost_price=-10.0,
        )

        errors = pos.validate()
        assert any("成本价不能为负数" in e for e in errors)

    def test_validate_negative_current_price(self):
        """测试验证负数当前价"""
        pos = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
            current_price=-10.0,
        )

        errors = pos.validate()
        assert any("当前价不能为负数" in e for e in errors)


class TestCCTJParseResult:
    """测试 CCTJParseResult 类"""

    def test_create_result(self):
        """测试创建解析结果"""
        from datetime import datetime

        result = CCTJParseResult(
            positions=[],
            file_path="/path/to/file.cctj",
            parse_time=datetime.now(),
            trade_date="2024-01-01",
        )

        assert result.file_path == "/path/to/file.cctj"
        assert result.trade_date == "2024-01-01"
        assert result.total_count == 0

    def test_result_to_dict(self):
        """测试转换为字典"""
        from datetime import datetime

        pos = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
        )

        result = CCTJParseResult(
            positions=[pos],
            file_path="/path/to/file.cctj",
            parse_time=datetime.now(),
            total_count=1,
            valid_count=1,
        )

        d = result.to_dict()
        assert d['file_path'] == "/path/to/file.cctj"
        assert d['total_count'] == 1
        assert d['valid_count'] == 1
        assert d['positions_count'] == 1
        assert 'parse_time' in d


class TestCCTJParser:
    """测试 CCTJParser 类"""

    def test_create_parser(self):
        """测试创建解析器"""
        parser = CCTJParser()
        assert parser.file_path is None
        assert len(parser.positions) == 0

    def test_create_parser_with_path(self):
        """测试创建带路径的解析器"""
        parser = CCTJParser(file_path="/path/to/file.cctj")
        assert str(parser.file_path) == "/path/to/file.cctj"

    def test_parse_nonexistent_file(self):
        """测试解析不存在的文件"""
        parser = CCTJParser()

        with pytest.raises(CCTJFileNotFoundError):
            parser.parse("/nonexistent/path/file.cctj")

    def test_parse_unsupported_format(self):
        """测试解析不支持的格式"""
        parser = CCTJParser()

        # 创建一个临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            with pytest.raises(CCTJFormatError):
                parser.parse(temp_path)
        finally:
            os.unlink(temp_path)

    def test_safe_str(self):
        """测试安全字符串转换"""
        parser = CCTJParser()

        assert parser._safe_str(None) == ""
        assert parser._safe_str("") == ""
        assert parser._safe_str("  test  ") == "test"
        assert parser._safe_str(123) == "123"

    def test_safe_int(self):
        """测试安全整数转换"""
        parser = CCTJParser()

        assert parser._safe_int(None) == 0
        assert parser._safe_int("") == 0
        assert parser._safe_int(100) == 100
        assert parser._safe_int("1,000") == 1000
        assert parser._safe_int("invalid") == 0

    def test_safe_float(self):
        """测试安全浮点数转换"""
        parser = CCTJParser()

        assert parser._safe_float(None) == 0.0
        assert parser._safe_float("") == 0.0
        assert parser._safe_float(10.5) == 10.5
        assert parser._safe_float("10.5") == 10.5
        assert parser._safe_float("1,000.50") == 1000.5
        assert parser._safe_float("invalid") == 0.0

    def test_normalize_columns(self):
        """测试列名标准化"""
        parser = CCTJParser()

        import pandas as pd
        df = pd.DataFrame({
            'ZQDM': ['000001'],
            '证券代码': ['000002'],  # 测试重复映射
            'ZJZH': ['TEST001'],
            'UNKNOWN_COL': ['value'],
        })

        normalized = parser._normalize_columns(df)
        assert 'stock_code' in normalized.columns
        assert 'account_id' in normalized.columns
        assert 'UNKNOWN_COL' in normalized.columns

    def test_get_positions_by_account(self):
        """测试按账户获取仓位"""
        parser = CCTJParser()

        pos1 = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
        )
        pos2 = CCTJPosition(
            stock_code="000002",
            stock_name="万科 A",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
        )
        pos3 = CCTJPosition(
            stock_code="000003",
            stock_name="中国平安",
            account_id="TEST002",
            market_id="SH",
            position_type="REAL",
        )

        parser.positions = [pos1, pos2, pos3]

        account1_positions = parser.get_positions_by_account("TEST001")
        assert len(account1_positions) == 2

        account2_positions = parser.get_positions_by_account("TEST002")
        assert len(account2_positions) == 1

    def test_get_positions_by_stock(self):
        """测试按股票获取仓位"""
        parser = CCTJParser()

        pos1 = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
        )
        pos2 = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST002",
            market_id="SZ",
            position_type="REAL",
        )
        pos3 = CCTJPosition(
            stock_code="000002",
            stock_name="万科 A",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
        )

        parser.positions = [pos1, pos2, pos3]

        stock_positions = parser.get_positions_by_stock("000001")
        assert len(stock_positions) == 2

    def test_get_summary(self):
        """测试获取摘要"""
        parser = CCTJParser()

        pos1 = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
            total_volume=1000,
            market_value=10500,
            cost_amount=10000,
            profit_loss=500,
        )
        pos2 = CCTJPosition(
            stock_code="000002",
            stock_name="万科 A",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
            total_volume=500,
            market_value=10000,
            cost_amount=10000,
            profit_loss=0,
        )

        parser.positions = [pos1, pos2]

        summary = parser.get_summary()
        assert summary['total_positions'] == 2
        assert summary['total_market_value'] == 20500
        assert summary['total_cost'] == 20000
        assert summary['total_profit_loss'] == 500
        assert summary['unique_stocks'] == 2
        assert summary['unique_accounts'] == 1

    def test_get_summary_empty(self):
        """测试空摘要"""
        parser = CCTJParser()

        summary = parser.get_summary()
        assert summary['total_positions'] == 0
        assert summary['total_market_value'] == 0
        assert summary['unique_stocks'] == 0

    def test_to_dataframe(self):
        """测试转换为 DataFrame"""
        parser = CCTJParser()

        pos = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
            total_volume=1000,
        )
        parser.positions = [pos]

        df = parser.to_dataframe()
        assert len(df) == 1
        assert df.iloc[0]['stock_code'] == "000001"

    def test_to_dataframe_empty(self):
        """测试空 DataFrame"""
        parser = CCTJParser()
        df = parser.to_dataframe()
        assert df.empty


class TestCCTJParserExcel:
    """测试 CCTJParser Excel 导出功能"""

    def test_export_to_excel(self):
        """测试导出到 Excel"""
        import tempfile

        parser = CCTJParser()
        pos = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
            total_volume=1000,
        )
        parser.positions = [pos]

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            temp_path = f.name

        try:
            result_path = parser.export(temp_path, format='excel')
            assert os.path.exists(result_path)
            assert result_path.endswith('.xlsx')
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_to_csv(self):
        """测试导出到 CSV"""
        import tempfile

        parser = CCTJParser()
        pos = CCTJPosition(
            stock_code="000001",
            stock_name="平安银行",
            account_id="TEST001",
            market_id="SZ",
            position_type="REAL",
            total_volume=1000,
        )
        parser.positions = [pos]

        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            temp_path = f.name

        try:
            result_path = parser.export(temp_path, format='csv')
            assert os.path.exists(result_path)
            assert result_path.endswith('.csv')
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_empty_data(self):
        """测试导出空数据"""
        import tempfile

        parser = CCTJParser()

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            temp_path = f.name

        try:
            with pytest.raises(Exception):  # CCTJDataError
                parser.export(temp_path, format='excel')
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestCCTJFieldMapping:
    """测试 CCTJ 字段映射"""

    def test_field_mapping_exists(self):
        """测试字段映射存在"""
        parser = CCTJParser()

        assert 'zqdm' in parser.FIELD_MAPPING
        assert '证券代码' in parser.FIELD_MAPPING
        assert 'zjzh' in parser.FIELD_MAPPING
        assert '资金账号' in parser.FIELD_MAPPING

    def test_field_mapping_targets(self):
        """测试字段映射目标"""
        parser = CCTJParser()

        assert parser.FIELD_MAPPING['zqdm'] == 'stock_code'
        parser.FIELD_MAPPING['证券代码'] == 'stock_code'
        assert parser.FIELD_MAPPING['zjzh'] == 'account_id'
        assert parser.FIELD_MAPPING['总数量'] == 'total_volume'
        assert parser.FIELD_MAPPING['可用数量'] == 'available_volume'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
