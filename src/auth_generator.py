"""
授权文件生成器

生成第二天的交易授权文件，供迅投 PB 系统使用
支持 DBF 和 Excel 格式输出
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import os


@dataclass
class AuthRecord:
    """
    授权记录类

    单只证券的授权数据
    """
    trade_date: str                   # 交易日期
    account_id: str                   # 账户 ID
    stock_code: str                   # 证券代码
    stock_name: str                   # 证券名称
    market_id: str                    # 市场代码 (SH/SZ)

    # 交易限制
    max_buy_volume: int = 0           # 最大买入数量
    max_sell_volume: int = 0          # 最大卖出数量
    max_buy_amount: float = 0.0       # 最大买入金额
    max_sell_amount: float = 0.0      # 最大卖出金额

    # 仓位限制
    max_position_ratio: float = 0.0   # 最大持仓比例
    max_position_volume: int = 0      # 最大持仓数量

    # 风险参数
    risk_level: str = "NORMAL"        # 风险等级：LOW/NORMAL/HIGH/BLOCKED
    stop_loss_price: float = 0.0      # 止损价
    stop_profit_price: float = 0.0    # 止盈价

    # 授权状态
    auth_status: str = "ACTIVE"       # 授权状态：ACTIVE/BLOCKED/LIMITED

    # 备注
    remark: str = ""

    @property
    def key(self) -> str:
        """唯一键"""
        return f"{self.trade_date}_{self.account_id}_{self.stock_code}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'trade_date': self.trade_date,
            'account_id': self.account_id,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'market_id': self.market_id,
            'max_buy_volume': self.max_buy_volume,
            'max_sell_volume': self.max_sell_volume,
            'max_buy_amount': round(self.max_buy_amount, 2),
            'max_sell_amount': round(self.max_sell_amount, 2),
            'max_position_ratio': round(self.max_position_ratio, 4),
            'max_position_volume': self.max_position_volume,
            'risk_level': self.risk_level,
            'stop_loss_price': round(self.stop_loss_price, 4),
            'stop_profit_price': round(self.stop_profit_price, 4),
            'auth_status': self.auth_status,
            'remark': self.remark,
        }


class AuthGenerator:
    """
    授权文件生成器

    根据持仓数据生成第二天的交易授权文件
    """

    # DBF 字段定义 (迅投 PB 系统标准)
    DBF_FIELDS = {
        'ZQDM': {'type': 'C', 'size': 10},      # 证券代码
        'ZQJC': {'type': 'C', 'size': 32},      # 证券简称
        'ZJZH': {'type': 'C', 'size': 20},      # 资金账号
        'SC': {'type': 'C', 'size': 4},         # 市场代码
        'JYRQ': {'type': 'D', 'size': 8},       # 交易日期
        'MXSL': {'type': 'N', 'size': 12},      # 买入数量上限
        'MCSL': {'type': 'N', 'size': 12},      # 卖出数量上限
        'MXJE': {'type': 'N', 'size': 15, 'dec': 2},  # 买入金额上限
        'MCJE': {'type': 'N', 'size': 15, 'dec': 2},  # 卖出金额上限
        'CWSX': {'type': 'N', 'size': 10, 'dec': 4},  # 持仓上限 (比例)
        'FXDJ': {'type': 'C', 'size': 8},       # 风险等级
        'ZTJ': {'type': 'N', 'size': 10, 'dec': 4},   # 止损价
        'ZYTJ': {'type': 'N', 'size': 10, 'dec': 4},   # 止盈价
        'ZT': {'type': 'C', 'size': 8},         # 状态
        'BZ': {'type': 'C', 'size': 64},        # 备注
    }

    # 中文列名映射
    COLUMN_NAMES = {
        'trade_date': '交易日期',
        'account_id': '资金账号',
        'stock_code': '证券代码',
        'stock_name': '证券简称',
        'market_id': '市场代码',
        'max_buy_volume': '买入数量上限',
        'max_sell_volume': '卖出数量上限',
        'max_buy_amount': '买入金额上限',
        'max_sell_amount': '卖出金额上限',
        'max_position_ratio': '持仓上限 (比例)',
        'max_position_volume': '持仓上限 (数量)',
        'risk_level': '风险等级',
        'stop_loss_price': '止损价',
        'stop_profit_price': '止盈价',
        'auth_status': '状态',
        'remark': '备注',
    }

    def __init__(
        self,
        output_dir: Optional[Union[str, Path]] = None,
        default_max_position_ratio: float = 0.2,
        default_risk_level: str = "NORMAL",
    ):
        """
        初始化授权生成器

        Args:
            output_dir: 输出目录
            default_max_position_ratio: 默认最大持仓比例
            default_risk_level: 默认风险等级
        """
        self.output_dir = Path(output_dir) if output_dir else Path("./output/auth")
        self.default_max_position_ratio = default_max_position_ratio
        self.default_risk_level = default_risk_level

        self.records: List[AuthRecord] = []
        self.trade_date: Optional[str] = None

        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_auth_record(
        self,
        stock_code: str,
        stock_name: str,
        account_id: str,
        market_id: str,
        total_volume: int,
        available_volume: int,
        current_price: float,
        trade_date: Optional[str] = None,
        max_position_ratio: Optional[float] = None,
        risk_level: Optional[str] = None,
        stop_loss_ratio: float = 0.05,
        stop_profit_ratio: float = 0.10,
        remark: str = "",
    ) -> AuthRecord:
        """
        生成单条授权记录

        Args:
            stock_code: 证券代码
            stock_name: 证券名称
            account_id: 账户 ID
            market_id: 市场代码
            total_volume: 总持仓
            available_volume: 可用数量
            current_price: 当前价
            trade_date: 交易日期（可选，默认明天）
            max_position_ratio: 最大持仓比例
            risk_level: 风险等级
            stop_loss_ratio: 止损比例（相对当前价）
            stop_profit_ratio: 止盈比例（相对当前价）
            remark: 备注

        Returns:
            AuthRecord 授权记录
        """
        # 确定交易日期（默认为明天）
        if trade_date is None:
            tomorrow = datetime.now() + timedelta(days=1)
            trade_date = tomorrow.strftime("%Y%m%d")
        else:
            # 如果是今天，改为明天
            today = datetime.now().strftime("%Y%m%d")
            if trade_date == today:
                tomorrow = datetime.now() + timedelta(days=1)
                trade_date = tomorrow.strftime("%Y%m%d")

        # 设置默认值
        if max_position_ratio is None:
            max_position_ratio = self.default_max_position_ratio
        if risk_level is None:
            risk_level = self.default_risk_level

        # 计算最大买入/卖出数量
        # 卖出上限 = 可用数量
        max_sell_volume = available_volume

        # 买入上限 = 当前持仓 * 最大持仓比例 - 当前持仓
        # 但不能超过可用数量（简化处理）
        if total_volume > 0:
            max_allowed = int(total_volume * max_position_ratio / (1 - max_position_ratio)) if max_position_ratio < 1 else total_volume
            max_buy_volume = max(0, max_allowed - total_volume)
        else:
            # 没有持仓时，允许买入参考数量
            max_buy_volume = 1000  # 默认允许买入 1000 股

        # 计算金额上限
        max_buy_amount = max_buy_volume * current_price
        max_sell_amount = max_sell_volume * current_price

        # 计算止损止盈价
        stop_loss_price = current_price * (1 - stop_loss_ratio) if current_price > 0 else 0.0
        stop_profit_price = current_price * (1 + stop_profit_ratio) if current_price > 0 else 0.0

        # 确定授权状态
        auth_status = "ACTIVE"
        if risk_level == "BLOCKED":
            auth_status = "BLOCKED"
            max_buy_volume = 0
            max_sell_volume = 0
        elif risk_level == "HIGH":
            auth_status = "LIMITED"

        record = AuthRecord(
            trade_date=trade_date,
            account_id=account_id,
            stock_code=stock_code,
            stock_name=stock_name,
            market_id=market_id,
            max_buy_volume=max_buy_volume,
            max_sell_volume=max_sell_volume,
            max_buy_amount=max_buy_amount,
            max_sell_amount=max_sell_amount,
            max_position_ratio=max_position_ratio,
            max_position_volume=total_volume + max_buy_volume,
            risk_level=risk_level,
            stop_loss_price=stop_loss_price,
            stop_profit_price=stop_profit_price,
            auth_status=auth_status,
            remark=remark,
        )

        self.records.append(record)
        self.trade_date = trade_date

        return record

    def generate_from_positions(
        self,
        positions: List[Any],
        trade_date: Optional[str] = None,
        risk_config: Optional[Dict[str, Any]] = None,
    ):
        """
        从持仓列表批量生成授权记录

        Args:
            positions: 持仓对象列表（RealPosition 或 dict）
            trade_date: 交易日期
            risk_config: 风险配置（可选）
                {
                    'stock_code': {
                        'max_position_ratio': 0.3,
                        'risk_level': 'HIGH',
                        'stop_loss_ratio': 0.08,
                    }
                }
        """
        if risk_config is None:
            risk_config = {}

        for pos in positions:
            # 提取公共字段 - 支持对象和字典两种形式
            if isinstance(pos, dict):
                stock_code = pos.get('stock_code', '')
                stock_name = pos.get('stock_name', '')
                account_id = pos.get('account_id', '')
                market_id = pos.get('market_id', '')
                total_volume = pos.get('total_volume', 0)
                available_volume = pos.get('available_volume', 0)
                current_price = pos.get('current_price', 0.0)
            else:
                # 对象形式
                stock_code = getattr(pos, 'stock_code', '')
                stock_name = getattr(pos, 'stock_name', '')
                account_id = getattr(pos, 'account_id', '')
                market_id = getattr(pos, 'market_id', '')
                total_volume = getattr(pos, 'total_volume', 0)
                available_volume = getattr(pos, 'available_volume', 0)
                current_price = getattr(pos, 'current_price', 0.0)

            # 获取个股风险配置
            stock_risk = risk_config.get(stock_code, {})
            max_position_ratio = stock_risk.get('max_position_ratio', self.default_max_position_ratio)
            risk_level = stock_risk.get('risk_level', self.default_risk_level)
            stop_loss_ratio = stock_risk.get('stop_loss_ratio', 0.05)
            stop_profit_ratio = stock_risk.get('stop_profit_ratio', 0.10)
            remark = stock_risk.get('remark', '')

            self.generate_auth_record(
                stock_code=stock_code,
                stock_name=stock_name,
                account_id=account_id,
                market_id=market_id,
                total_volume=total_volume,
                available_volume=available_volume,
                current_price=current_price,
                trade_date=trade_date,
                max_position_ratio=max_position_ratio,
                risk_level=risk_level,
                stop_loss_ratio=stop_loss_ratio,
                stop_profit_ratio=stop_profit_ratio,
                remark=remark,
            )

    def generate_from_position_manager(
        self,
        position_manager,
        trade_date: Optional[str] = None,
        risk_config: Optional[Dict[str, Any]] = None,
    ):
        """
        从持仓管理器生成授权记录

        Args:
            position_manager: PositionManager 对象
            trade_date: 交易日期
            risk_config: 风险配置
        """
        positions = position_manager.get_all_positions()
        self.generate_from_positions(positions, trade_date=trade_date, risk_config=risk_config)

    def get_records_by_account(self, account_id: str) -> List[AuthRecord]:
        """按账户获取记录"""
        return [r for r in self.records if r.account_id == account_id]

    def get_records_by_stock(self, stock_code: str) -> List[AuthRecord]:
        """按股票获取记录"""
        return [r for r in self.records if r.stock_code == stock_code]

    def get_summary(self) -> Dict[str, Any]:
        """
        获取授权汇总

        Returns:
            汇总信息
        """
        if not self.records:
            return {
                'trade_date': self.trade_date,
                'record_count': 0,
                'active_count': 0,
                'blocked_count': 0,
                'limited_count': 0,
            }

        return {
            'trade_date': self.trade_date,
            'record_count': len(self.records),
            'active_count': len([r for r in self.records if r.auth_status == 'ACTIVE']),
            'blocked_count': len([r for r in self.records if r.auth_status == 'BLOCKED']),
            'limited_count': len([r for r in self.records if r.auth_status == 'LIMITED']),
            'total_buy_limit': sum(r.max_buy_volume for r in self.records),
            'total_sell_limit': sum(r.max_sell_volume for r in self.records),
            'high_risk_count': len([r for r in self.records if r.risk_level == 'HIGH']),
            'normal_risk_count': len([r for r in self.records if r.risk_level == 'NORMAL']),
        }

    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame"""
        if not self.records:
            return pd.DataFrame()

        df = pd.DataFrame([r.to_dict() for r in self.records])

        # 按指定列顺序排列
        columns = [
            'trade_date', 'account_id', 'stock_code', 'stock_name', 'market_id',
            'max_buy_volume', 'max_sell_volume',
            'max_buy_amount', 'max_sell_amount',
            'max_position_ratio', 'max_position_volume',
            'risk_level', 'stop_loss_price', 'stop_profit_price',
            'auth_status', 'remark',
        ]
        existing_cols = [c for c in columns if c in df.columns]
        return df[existing_cols]

    def export(
        self,
        output_path: Optional[Union[str, Path]] = None,
        format: str = "excel",
    ) -> str:
        """
        导出授权文件

        Args:
            output_path: 输出路径
            format: 导出格式 ('excel', 'csv', 'dbf')

        Returns:
            输出文件路径
        """
        if not self.records:
            raise ValueError("没有可导出的数据")

        if output_path is None:
            trade_date = self.trade_date or datetime.now().strftime("%Y%m%d")
            output_path = self.output_dir / f"auth_{trade_date}.{format}"
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "excel" or output_path.suffix in ['.xlsx', '.xls']:
            return self._export_excel(output_path)
        elif format == "csv" or output_path.suffix == '.csv':
            return self._export_csv(output_path)
        elif format == "dbf" or output_path.suffix == '.dbf':
            return self._export_dbf(output_path)
        else:
            raise ValueError(f"不支持的导出格式：{format}")

    def _export_excel(self, output_path: Path) -> str:
        """导出为 Excel"""
        df = self.to_dataframe()

        # 重命名列名为中文
        df_cn = df.rename(columns=self.COLUMN_NAMES)

        df_cn.to_excel(output_path.with_suffix('.xlsx'), index=False, engine='openpyxl')
        return str(output_path.with_suffix('.xlsx'))

    def _export_csv(self, output_path: Path) -> str:
        """导出为 CSV"""
        df = self.to_dataframe().rename(columns=self.COLUMN_NAMES)
        df.to_csv(output_path.with_suffix('.csv'), index=False, encoding='utf-8-sig')
        return str(output_path.with_suffix('.csv'))

    def _export_dbf(self, output_path: Path) -> str:
        """导出为 DBF"""
        try:
            from dbfread import DBF
            from dbfwrite import DBFCreate, DBFField
        except ImportError:
            # 如果没有 dbfwrite，导出为 Excel 并提示
            return self._export_excel(output_path.with_suffix('.xlsx'))

        # 创建 DBF 文件
        dbf = DBFCreate(str(output_path.with_suffix('.dbf')))

        # 添加字段
        for field_name, field_def in self.DBF_FIELDS.items():
            field_type = field_def['type']
            field_size = field_def['size']
            field_dec = field_def.get('dec', 0)

            # 映射字段类型
            if field_type == 'C':
                dbf.add_field(field_name, field_type, field_size)
            elif field_type == 'N':
                dbf.add_field(field_name, field_type, field_size, field_dec)
            elif field_type == 'D':
                dbf.add_field(field_name, field_type)

        # 写入数据
        for record in self.records:
            row = {
                'ZQDM': record.stock_code[:10],
                'ZQJC': (record.stock_name or '')[:32],
                'ZJZH': record.account_id[:20],
                'SC': record.market_id[:4],
                'JYRQ': record.trade_date,
                'MXSL': record.max_buy_volume,
                'MCSL': record.max_sell_volume,
                'MXJE': record.max_buy_amount,
                'MCJE': record.max_sell_amount,
                'CWSX': record.max_position_ratio,
                'FXDJ': record.risk_level[:8],
                'ZTJ': record.stop_loss_price,
                'ZYTJ': record.stop_profit_price,
                'ZT': record.auth_status[:8],
                'BZ': (record.remark or '')[:64],
            }
            dbf.write(row)

        dbf.close()
        return str(output_path.with_suffix('.dbf'))

    def clear(self):
        """清空记录"""
        self.records = []
        self.trade_date = None
