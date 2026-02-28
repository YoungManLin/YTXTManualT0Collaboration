"""
CCTJ 仓位文件解析模块

解析 GT 系统的 CCTJ 仓位文件格式，提供真实持仓数据
支持 .cctj, .dbf, .xlsx, .csv 格式
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class CCTJError(Exception):
    """CCTJ 解析错误基类"""
    pass


class CCTJFileNotFoundError(CCTJError):
    """文件不存在错误"""
    pass


class CCTJFormatError(CCTJError):
    """文件格式错误"""
    pass


class CCTJDataError(CCTJError):
    """数据内容错误"""
    pass


class PositionType(Enum):
    """仓位类型"""
    REAL = "REAL"       # 真实持仓
    VIRTUAL = "VIRTUAL" # 虚拟持仓 (T0 临时仓位)


@dataclass
class CCTJPosition:
    """
    CCTJ 仓位数据类

    对应 GT 系统 CCTJ 文件中的仓位记录
    """
    stock_code: str           # 证券代码
    stock_name: str           # 证券名称
    account_id: str           # 资金账号
    market_id: str            # 市场代码 (SH/SZ)
    position_type: str        # 仓位类型

    # 持仓数量
    total_volume: int = 0           # 总持仓
    available_volume: int = 0       # 可用数量
    frozen_volume: int = 0          # 冻结数量
    yesterday_volume: int = 0       # 昨日持仓 (可卖)
    today_volume: int = 0           # 今日持仓 (买入)

    # 成本价格
    cost_price: float = 0.0         # 成本价
    open_price: float = 0.0         # 开盘价
    current_price: float = 0.0      # 当前价

    # 市值与盈亏
    market_value: float = 0.0       # 市值
    cost_amount: float = 0.0        # 成本金额
    profit_loss: float = 0.0        # 浮动盈亏
    profit_rate: float = 0.0        # 盈亏比例

    # 时间信息
    trade_date: Optional[str] = None      # 交易日期
    update_time: Optional[str] = None     # 更新时间

    # 扩展字段
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        """获取唯一键 (股票 + 账户)"""
        return f"{self.stock_code}_{self.account_id}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'account_id': self.account_id,
            'market_id': self.market_id,
            'position_type': self.position_type,
            'total_volume': self.total_volume,
            'available_volume': self.available_volume,
            'frozen_volume': self.frozen_volume,
            'yesterday_volume': self.yesterday_volume,
            'today_volume': self.today_volume,
            'cost_price': self.cost_price,
            'open_price': self.open_price,
            'current_price': self.current_price,
            'market_value': self.market_value,
            'cost_amount': self.cost_amount,
            'profit_loss': self.profit_loss,
            'profit_rate': self.profit_rate,
            'trade_date': self.trade_date,
            'update_time': self.update_time,
            **self.extra
        }

    def validate(self) -> List[str]:
        """
        验证数据有效性

        Returns:
            错误信息列表，空列表表示验证通过
        """
        errors = []

        if not self.stock_code:
            errors.append("证券代码不能为空")

        if not self.account_id:
            errors.append("资金账号不能为空")

        if self.total_volume < 0:
            errors.append(f"总持仓不能为负数：{self.total_volume}")

        if self.available_volume < 0:
            errors.append(f"可用数量不能为负数：{self.available_volume}")

        if self.frozen_volume < 0:
            errors.append(f"冻结数量不能为负数：{self.frozen_volume}")

        # 数量关系检查
        if self.available_volume + self.frozen_volume > self.total_volume:
            errors.append(
                f"可用 + 冻结 > 总持仓：{self.available_volume}+{self.frozen_volume}>"
                f"{self.total_volume}"
            )

        if self.cost_price < 0:
            errors.append(f"成本价不能为负数：{self.cost_price}")

        if self.current_price < 0:
            errors.append(f"当前价不能为负数：{self.current_price}")

        return errors


@dataclass
class CCTJParseResult:
    """
    CCTJ 解析结果

    包含解析后的仓位列表和元数据
    """
    positions: List[CCTJPosition]           # 仓位列表
    file_path: str                          # 文件路径
    parse_time: datetime                    # 解析时间
    trade_date: Optional[str] = None        # 交易日期
    total_count: int = 0                    # 总记录数
    valid_count: int = 0                    # 有效记录数
    error_count: int = 0                    # 错误记录数
    errors: List[str] = field(default_factory=list)  # 错误信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'file_path': self.file_path,
            'parse_time': self.parse_time.isoformat(),
            'trade_date': self.trade_date,
            'total_count': self.total_count,
            'valid_count': self.valid_count,
            'error_count': self.error_count,
            'errors': self.errors[:20],  # 只返回前 20 个错误
            'positions_count': len(self.positions)
        }


class CCTJParser:
    """
    CCTJ 仓位文件解析器

    支持格式:
    - .cctj (原生格式)
    - .dbf (DBF 格式)
    - .xlsx / .xls (Excel 格式)
    - .csv (CSV 格式)

    CCTJ 文件标准字段 (GT 系统):
    - ZQDM: 证券代码
    - ZQJC: 证券简称
    - ZJZH: 资金账号
    - SC: 市场 (SH/SZ)
    - CWLB: 仓位类型
    - ZSL: 总数量
    - KSL: 可用数量
    - DJSL: 冻结数量
    - ZRHJ: 昨日持仓
    - JRHJ: 今日持仓
    - CB Price: 成本价
    - KCP: 开盘价
    - ZXP: 最新价
    - SZ: 市值
    - CB: 成本
    - FY: 浮盈
    - FYL: 盈利率
    - JYRQ: 交易日期
    - GXSJ: 更新时间
    """

    # CCTJ 字段映射 (中文/英文 -> 标准英文名)
    FIELD_MAPPING: Dict[str, str] = {
        # 证券信息
        'zqdm': 'stock_code',
        '证券代码': 'stock_code',
        '证券简称': 'stock_name',
        'zqjc': 'stock_name',
        # 账户信息
        'zjzh': 'account_id',
        '资金账号': 'account_id',
        'sc': 'market_id',
        '市场': 'market_id',
        # 仓位类型
        'fwlb': 'position_type',
        '仓位类型': 'position_type',
        # 数量信息
        'zsl': 'total_volume',
        '总数量': 'total_volume',
        'ksl': 'available_volume',
        '可用数量': 'available_volume',
        'dj sl': 'frozen_volume',
        '冻结数量': 'frozen_volume',
        'zhhj': 'yesterday_volume',
        '昨日持仓': 'yesterday_volume',
        'jrhj': 'today_volume',
        '今日持仓': 'today_volume',
        # 价格信息
        'cbj': 'cost_price',
        '成本价': 'cost_price',
        'kcp': 'open_price',
        '开盘价': 'open_price',
        'zxp': 'current_price',
        '当前价': 'current_price',
        '最新价': 'current_price',
        # 市值盈亏
        'sz': 'market_value',
        '市值': 'market_value',
        'cb': 'cost_amount',
        '成本': 'cost_amount',
        'fy': 'profit_loss',
        '浮盈': 'profit_loss',
        '浮动盈亏': 'profit_loss',
        'fyl': 'profit_rate',
        '盈利率': 'profit_rate',
        # 时间信息
        'jyrq': 'trade_date',
        '交易日期': 'trade_date',
        'gxsj': 'update_time',
        '更新时间': 'update_time',
    }

    # 必填字段
    REQUIRED_FIELDS = ['stock_code', 'account_id', 'market_id']

    # 数值字段 (需要转换)
    NUMERIC_FIELDS = {
        'total_volume': int,
        'available_volume': int,
        'frozen_volume': int,
        'yesterday_volume': int,
        'today_volume': int,
        'cost_price': float,
        'open_price': float,
        'current_price': float,
        'market_value': float,
        'cost_amount': float,
        'profit_loss': float,
        'profit_rate': float,
    }

    def __init__(self, file_path: Optional[Union[str, Path]] = None):
        """
        初始化解析器

        Args:
            file_path: CCTJ 文件路径 (可选，可在 parse() 时指定)
        """
        self.file_path: Optional[Path] = Path(file_path) if file_path else None
        self.df: Optional[pd.DataFrame] = None
        self.positions: List[CCTJPosition] = []
        self.result: Optional[CCTJParseResult] = None

    def parse(self, file_path: Optional[Union[str, Path]] = None) -> CCTJParseResult:
        """
        解析 CCTJ 文件

        Args:
            file_path: 文件路径 (可选，覆盖初始化时的路径)

        Returns:
            CCTJParseResult 解析结果

        Raises:
            CCTJFileNotFoundError: 文件不存在
            CCTJFormatError: 文件格式不支持
            CCTJDataError: 数据格式错误
        """
        # 确定文件路径
        path = Path(file_path) if file_path else self.file_path
        if not path:
            raise CCTJFileNotFoundError("未指定文件路径")

        path = Path(path)
        if not path.exists():
            raise CCTJFileNotFoundError(f"文件不存在：{path}")

        self.file_path = path
        self.positions = []
        errors: List[str] = []

        # 根据后缀选择解析方法
        suffix = path.suffix.lower()

        try:
            if suffix == '.cctj':
                self._parse_cctj()
            elif suffix == '.dbf':
                self._parse_dbf()
            elif suffix in ['.xlsx', '.xls']:
                self._parse_excel()
            elif suffix == '.csv':
                self._parse_csv()
            else:
                raise CCTJFormatError(f"不支持的文件格式：{suffix}")
        except (ImportError, pd.errors.EmptyDataError) as e:
            raise CCTJFormatError(f"解析失败：{str(e)}")

        # 转换并验证数据
        self._convert_to_positions()

        # 验证所有仓位
        valid_count = 0
        error_count = 0
        for pos in self.positions:
            pos_errors = pos.validate()
            if pos_errors:
                errors.extend([f"{pos.key}: {e}" for e in pos_errors])
                error_count += 1
            else:
                valid_count += 1

        # 提取交易日期
        trade_date = None
        if self.positions:
            trade_dates = [p.trade_date for p in self.positions if p.trade_date]
            if trade_dates:
                trade_date = trade_dates[0]

        # 创建解析结果
        self.result = CCTJParseResult(
            positions=self.positions,
            file_path=str(path),
            parse_time=datetime.now(),
            trade_date=trade_date,
            total_count=len(self.positions),
            valid_count=valid_count,
            error_count=error_count,
            errors=errors
        )

        return self.result

    def _parse_cctj(self):
        """
        解析原生 CCTJ 格式

        CCTJ 格式通常是固定宽度或分隔符格式
        """
        # 尝试用不同方式读取
        try:
            # 首先尝试作为带分隔符的文本
            self.df = pd.read_csv(
                self.file_path,
                encoding='gbk',
                delimiter=None,
                engine='python'
            )
        except Exception:
            try:
                # 尝试 UTF-8
                self.df = pd.read_csv(
                    self.file_path,
                    encoding='utf-8',
                    delimiter=None,
                    engine='python'
                )
            except Exception:
                # 尝试固定宽度
                self.df = pd.read_fwf(
                    self.file_path,
                    encoding='gbk'
                )

    def _parse_dbf(self):
        """解析 DBF 格式"""
        try:
            from dbfread import DBF

            dbf = DBF(str(self.file_path), encoding='gbk')
            records = list(dbf)

            if not records:
                self.df = pd.DataFrame()
            else:
                self.df = pd.DataFrame(records)

        except ImportError:
            # 如果没有 dbfread，尝试用 pandas
            self.df = pd.read_excel(self.file_path, engine='openpyxl')

    def _parse_excel(self):
        """解析 Excel 格式"""
        # 尝试不同的工作表名称
        excel_file = pd.ExcelFile(self.file_path, engine='openpyxl')
        sheet_names = excel_file.sheet_names

        # 优先使用"详情"或"仓位"工作表
        target_sheet = None
        for name in ['详情', '仓位', '持仓', 'CCTJ', sheet_names[0] if sheet_names else None]:
            if name and name in sheet_names:
                target_sheet = name
                break

        if target_sheet is None:
            raise CCTJFormatError("Excel 文件没有有效的工作表")

        self.df = pd.read_excel(
            self.file_path,
            sheet_name=target_sheet,
            engine='openpyxl'
        )

    def _parse_csv(self):
        """解析 CSV 格式"""
        # 尝试不同编码
        for encoding in ['gbk', 'utf-8', 'gb2312']:
            try:
                self.df = pd.read_csv(
                    self.file_path,
                    encoding=encoding
                )
                break
            except UnicodeDecodeError:
                continue
        else:
            raise CCTJFormatError("无法识别 CSV 文件编码")

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化列名

        将中文列名映射为英文
        """
        if df.columns.empty:
            return df

        # 标准化：小写、去空格
        new_columns = {}
        for col in df.columns:
            col_lower = str(col).lower().strip()
            col_clean = col_lower.replace('_', '').replace(' ', '')

            # 查找映射
            mapped = False
            for src, target in self.FIELD_MAPPING.items():
                src_lower_iter = src.lower().strip()
                src_clean = src_lower_iter.replace('_', '').replace(' ', '')
                if col_clean == src_clean or col_lower == src_lower_iter:
                    new_columns[col] = target
                    mapped = True
                    break

            if not mapped:
                # 保留原列名 (去除空格)
                new_columns[col] = col.strip()

        return df.rename(columns=new_columns)

    def _convert_to_positions(self):
        """将 DataFrame 转换为 CCTJPosition 列表"""
        if self.df is None or self.df.empty:
            return

        # 标准化列名
        df = self._normalize_columns(self.df.copy())

        # 过滤空行
        df = df.dropna(how='all')

        for idx, row in df.iterrows():
            try:
                # 跳过完全空的行
                if row.isna().all():
                    continue

                position = CCTJPosition(
                    stock_code=self._safe_str(row.get('stock_code', '')),
                    stock_name=self._safe_str(row.get('stock_name', '')),
                    account_id=self._safe_str(row.get('account_id', '')),
                    market_id=self._safe_str(row.get('market_id', '')).upper(),
                    position_type=self._safe_str(row.get('position_type', 'REAL')),

                    # 数量字段
                    total_volume=self._safe_int(row.get('total_volume', 0)),
                    available_volume=self._safe_int(row.get('available_volume', 0)),
                    frozen_volume=self._safe_int(row.get('frozen_volume', 0)),
                    yesterday_volume=self._safe_int(row.get('yesterday_volume', 0)),
                    today_volume=self._safe_int(row.get('today_volume', 0)),

                    # 价格字段
                    cost_price=self._safe_float(row.get('cost_price', 0.0)),
                    open_price=self._safe_float(row.get('open_price', 0.0)),
                    current_price=self._safe_float(row.get('current_price', 0.0)),

                    # 市值字段
                    market_value=self._safe_float(row.get('market_value', 0.0)),
                    cost_amount=self._safe_float(row.get('cost_amount', 0.0)),
                    profit_loss=self._safe_float(row.get('profit_loss', 0.0)),
                    profit_rate=self._safe_float(row.get('profit_rate', 0.0)),

                    # 时间字段
                    trade_date=self._safe_str(row.get('trade_date', None)),
                    update_time=self._safe_str(row.get('update_time', None)),
                )

                self.positions.append(position)

            except Exception as e:
                # 记录转换错误，但继续处理其他行
                if hasattr(self, 'result'):
                    self.result.errors.append(f"行{idx}转换失败：{str(e)}")

    def _safe_str(self, value: Any) -> str:
        """安全转换为字符串"""
        if value is None or pd.isna(value):
            return ''
        return str(value).strip()

    def _safe_int(self, value: Any) -> int:
        """安全转换为整数"""
        if value is None or pd.isna(value):
            return 0
        try:
            # 处理字符串中的逗号
            if isinstance(value, str):
                value = value.replace(',', '')
            return int(float(value))
        except (ValueError, TypeError):
            return 0

    def _safe_float(self, value: Any) -> float:
        """安全转换为浮点数"""
        if value is None or pd.isna(value):
            return 0.0
        try:
            # 处理字符串中的逗号
            if isinstance(value, str):
                value = value.replace(',', '')
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def get_positions_by_account(self, account_id: str) -> List[CCTJPosition]:
        """
        按账户获取仓位

        Args:
            account_id: 资金账号

        Returns:
            该账户的所有仓位
        """
        return [p for p in self.positions if p.account_id == account_id]

    def get_positions_by_stock(self, stock_code: str) -> List[CCTJPosition]:
        """
        按股票获取仓位

        Args:
            stock_code: 证券代码

        Returns:
            该股票的所有仓位
        """
        return [p for p in self.positions if p.stock_code == stock_code]

    def get_summary(self) -> Dict[str, Any]:
        """
        获取解析摘要

        Returns:
            摘要信息字典
        """
        if not self.positions:
            return {
                'total_positions': 0,
                'total_market_value': 0.0,
                'total_cost': 0.0,
                'total_profit_loss': 0.0,
                'unique_stocks': 0,
                'unique_accounts': 0,
            }

        total_mv = sum(p.market_value for p in self.positions)
        total_cost = sum(p.cost_amount for p in self.positions)
        total_pl = sum(p.profit_loss for p in self.positions)

        return {
            'total_positions': len(self.positions),
            'total_market_value': round(total_mv, 2),
            'total_cost': round(total_cost, 2),
            'total_profit_loss': round(total_pl, 2),
            'unique_stocks': len(set(p.stock_code for p in self.positions)),
            'unique_accounts': len(set(p.account_id for p in self.positions)),
            'avg_profit_rate': round(total_pl / total_cost * 100, 2) if total_cost > 0 else 0.0,
        }

    def to_dataframe(self) -> pd.DataFrame:
        """
        转换为 DataFrame

        Returns:
            包含所有仓位的 DataFrame
        """
        if not self.positions:
            return pd.DataFrame()

        return pd.DataFrame([p.to_dict() for p in self.positions])

    def export(self, output_path: Union[str, Path], format: str = 'excel') -> str:
        """
        导出解析结果

        Args:
            output_path: 输出文件路径
            format: 导出格式 ('excel', 'csv', 'json')

        Returns:
            实际输出的文件路径
        """
        output_path = Path(output_path)
        df = self.to_dataframe()

        if df.empty:
            raise CCTJDataError("没有可导出的数据")

        if format == 'excel' or output_path.suffix in ['.xlsx', '.xls']:
            df.to_excel(output_path.with_suffix('.xlsx'), index=False, engine='openpyxl')
        elif format == 'csv' or output_path.suffix == '.csv':
            df.to_csv(output_path.with_suffix('.csv'), index=False, encoding='utf-8-sig')
        elif format == 'json' or output_path.suffix == '.json':
            df.to_json(output_path.with_suffix('.json'), orient='records', force_ascii=False, indent=2)
        else:
            raise CCTJFormatError(f"不支持的导出格式：{format}")

        return str(output_path)
