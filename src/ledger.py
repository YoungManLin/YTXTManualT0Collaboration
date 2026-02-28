"""
台账记录模块

记录每日持仓台账，支持导出 Excel 文件
用于盘后记录和追溯持仓数据
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field
from datetime import datetime
import os


@dataclass
class LedgerRecord:
    """
    台账记录类

    单条台账数据结构
    """
    trade_date: str                   # 交易日期
    account_id: str                   # 账户 ID
    stock_code: str                   # 证券代码
    stock_name: str                   # 证券名称
    market_id: str                    # 市场代码

    # 持仓数量
    total_volume: int = 0             # 总持仓
    available_volume: int = 0         # 可用数量
    frozen_volume: int = 0            # 冻结数量
    yesterday_volume: int = 0         # 昨日持仓

    # 价格信息
    cost_price: float = 0.0           # 成本价
    current_price: float = 0.0        # 当前价

    # 市值与盈亏
    market_value: float = 0.0         # 市值
    cost_amount: float = 0.0          # 成本金额
    profit_loss: float = 0.0          # 浮动盈亏
    profit_rate: float = 0.0          # 盈亏率

    # 记录时间
    record_time: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

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
            'total_volume': self.total_volume,
            'available_volume': self.available_volume,
            'frozen_volume': self.frozen_volume,
            'yesterday_volume': self.yesterday_volume,
            'cost_price': round(self.cost_price, 4),
            'current_price': round(self.current_price, 4),
            'market_value': round(self.market_value, 2),
            'cost_amount': round(self.cost_amount, 2),
            'profit_loss': round(self.profit_loss, 2),
            'profit_rate': round(self.profit_rate, 4),
            'record_time': self.record_time,
        }


class LedgerManager:
    """
    台账管理器

    管理每日持仓台账记录
    """

    # Excel 列顺序
    COLUMNS = [
        'trade_date',      # 交易日期
        'account_id',      # 账户 ID
        'stock_code',      # 证券代码
        'stock_name',      # 证券名称
        'market_id',       # 市场代码
        'total_volume',    # 总持仓
        'available_volume', # 可用数量
        'frozen_volume',   # 冻结数量
        'yesterday_volume', # 昨日持仓
        'cost_price',      # 成本价
        'current_price',   # 当前价
        'market_value',    # 市值
        'cost_amount',     # 成本金额
        'profit_loss',     # 浮动盈亏
        'profit_rate',     # 盈亏率
        'record_time',     # 记录时间
    ]

    # 中文列名映射
    COLUMN_NAMES = {
        'trade_date': '交易日期',
        'account_id': '账户 ID',
        'stock_code': '证券代码',
        'stock_name': '证券名称',
        'market_id': '市场代码',
        'total_volume': '总持仓',
        'available_volume': '可用数量',
        'frozen_volume': '冻结数量',
        'yesterday_volume': '昨日持仓',
        'cost_price': '成本价',
        'current_price': '当前价',
        'market_value': '市值',
        'cost_amount': '成本金额',
        'profit_loss': '浮动盈亏',
        'profit_rate': '盈亏率 (%)',
        'record_time': '记录时间',
    }

    def __init__(self, output_dir: Optional[Union[str, Path]] = None):
        """
        初始化台账管理器

        Args:
            output_dir: 台账文件输出目录
        """
        self.output_dir = Path(output_dir) if output_dir else Path("./output/ledger")
        self.records: List[LedgerRecord] = []
        self.trade_date: Optional[str] = None

        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def add_record(
        self,
        trade_date: str,
        account_id: str,
        stock_code: str,
        stock_name: str,
        market_id: str,
        total_volume: int,
        available_volume: int,
        frozen_volume: int,
        yesterday_volume: int,
        cost_price: float,
        current_price: float,
    ) -> LedgerRecord:
        """
        添加台账记录

        Args:
            trade_date: 交易日期
            account_id: 账户 ID
            stock_code: 证券代码
            stock_name: 证券名称
            market_id: 市场代码
            total_volume: 总持仓
            available_volume: 可用数量
            frozen_volume: 冻结数量
            yesterday_volume: 昨日持仓
            cost_price: 成本价
            current_price: 当前价

        Returns:
            LedgerRecord 记录对象
        """
        # 计算派生字段
        market_value = total_volume * current_price
        cost_amount = total_volume * cost_price
        profit_loss = (current_price - cost_price) * total_volume
        profit_rate = (profit_loss / cost_amount * 100) if cost_amount > 0 else 0.0

        record = LedgerRecord(
            trade_date=trade_date,
            account_id=account_id,
            stock_code=stock_code,
            stock_name=stock_name,
            market_id=market_id,
            total_volume=total_volume,
            available_volume=available_volume,
            frozen_volume=frozen_volume,
            yesterday_volume=yesterday_volume,
            cost_price=cost_price,
            current_price=current_price,
            market_value=market_value,
            cost_amount=cost_amount,
            profit_loss=profit_loss,
            profit_rate=profit_rate,
        )

        self.records.append(record)

        # 更新交易日期
        if self.trade_date is None:
            self.trade_date = trade_date

        return record

    def add_records_from_positions(self, positions: List[Any], trade_date: Optional[str] = None):
        """
        从持仓列表批量添加记录

        Args:
            positions: 持仓对象列表（支持 RealPosition 或 CCTJPosition）
            trade_date: 交易日期（可选）
        """
        for pos in positions:
            # 自动检测持仓对象类型
            if hasattr(pos, 'account_id'):
                # RealPosition 或 CCTJPosition
                self.add_record(
                    trade_date=trade_date or getattr(pos, 'trade_date', datetime.now().strftime("%Y%m%d")),
                    account_id=pos.account_id,
                    stock_code=pos.stock_code,
                    stock_name=getattr(pos, 'stock_name', ''),
                    market_id=getattr(pos, 'market_id', ''),
                    total_volume=getattr(pos, 'total_volume', 0),
                    available_volume=getattr(pos, 'available_volume', 0),
                    frozen_volume=getattr(pos, 'frozen_volume', 0),
                    yesterday_volume=getattr(pos, 'yesterday_volume', 0),
                    cost_price=getattr(pos, 'cost_price', 0.0),
                    current_price=getattr(pos, 'current_price', 0.0),
                )

    def get_records_by_account(self, account_id: str) -> List[LedgerRecord]:
        """按账户获取记录"""
        return [r for r in self.records if r.account_id == account_id]

    def get_records_by_stock(self, stock_code: str) -> List[LedgerRecord]:
        """按股票获取记录"""
        return [r for r in self.records if r.stock_code == stock_code]

    def get_summary(self) -> Dict[str, Any]:
        """
        获取台账汇总

        Returns:
            汇总信息字典
        """
        if not self.records:
            return {
                'trade_date': self.trade_date,
                'record_count': 0,
                'total_market_value': 0.0,
                'total_cost': 0.0,
                'total_profit_loss': 0.0,
                'unique_accounts': 0,
                'unique_stocks': 0,
            }

        total_mv = sum(r.market_value for r in self.records)
        total_cost = sum(r.cost_amount for r in self.records)
        total_pl = sum(r.profit_loss for r in self.records)

        return {
            'trade_date': self.trade_date,
            'record_count': len(self.records),
            'total_market_value': round(total_mv, 2),
            'total_cost': round(total_cost, 2),
            'total_profit_loss': round(total_pl, 2),
            'avg_profit_rate': round(total_pl / total_cost * 100, 2) if total_cost > 0 else 0.0,
            'unique_accounts': len(set(r.account_id for r in self.records)),
            'unique_stocks': len(set(r.stock_code for r in self.records)),
        }

    def to_dataframe(self) -> pd.DataFrame:
        """
        转换为 DataFrame

        Returns:
            包含所有记录的 DataFrame
        """
        if not self.records:
            return pd.DataFrame(columns=self.COLUMNS)

        df = pd.DataFrame([r.to_dict() for r in self.records])

        # 按指定列顺序排列
        existing_cols = [c for c in self.COLUMNS if c in df.columns]
        return df[existing_cols]

    def export(
        self,
        output_path: Optional[Union[str, Path]] = None,
        include_summary: bool = True,
    ) -> str:
        """
        导出台账到 Excel

        Args:
            output_path: 输出路径（可选，默认自动生成）
            include_summary: 是否包含汇总工作表

        Returns:
            输出文件路径
        """
        if not self.records:
            raise ValueError("没有可导出的数据")

        # 确定输出路径
        if output_path is None:
            trade_date = self.trade_date or datetime.now().strftime("%Y%m%d")
            output_path = self.output_dir / f"ledger_{trade_date}.xlsx"
        else:
            output_path = Path(output_path)

        # 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建 DataFrame
        df = self.to_dataframe()

        # 重命名列名为中文
        df_cn = df.rename(columns=self.COLUMN_NAMES)

        # 导出到 Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 台账明细
            df_cn.to_excel(writer, sheet_name='台账明细', index=False)

            if include_summary:
                # 汇总信息
                summary = self.get_summary()
                summary_df = pd.DataFrame([
                    {'项目': '交易日期', '值': summary.get('trade_date', '')},
                    {'项目': '记录数', '值': summary.get('record_count', 0)},
                    {'项目': '总市值', '值': summary.get('total_market_value', 0)},
                    {'项目': '总成本', '值': summary.get('total_cost', 0)},
                    {'项目': '总盈亏', '值': summary.get('total_profit_loss', 0)},
                    {'项目': '平均盈亏率', '值': f"{summary.get('avg_profit_rate', 0)}%"},
                    {'项目': '账户数', '值': summary.get('unique_accounts', 0)},
                    {'项目': '股票数', '值': summary.get('unique_stocks', 0)},
                ])
                summary_df.to_excel(writer, sheet_name='汇总', index=False)

        return str(output_path)

    def export_csv(self, output_path: Optional[Union[str, Path]] = None) -> str:
        """
        导出台账到 CSV

        Args:
            output_path: 输出路径（可选）

        Returns:
            输出文件路径
        """
        if not self.records:
            raise ValueError("没有可导出的数据")

        if output_path is None:
            trade_date = self.trade_date or datetime.now().strftime("%Y%m%d")
            output_path = self.output_dir / f"ledger_{trade_date}.csv"
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        df = self.to_dataframe().rename(columns=self.COLUMN_NAMES)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')

        return str(output_path)

    def clear(self):
        """清空记录"""
        self.records = []
        self.trade_date = None

    def load_from_cctj_result(self, cctj_result, trade_date: Optional[str] = None):
        """
        从 CCTJ 解析结果加载台账

        Args:
            cctj_result: CCTJParseResult 对象
            trade_date: 交易日期（可选，优先使用）
        """
        use_date = trade_date or getattr(cctj_result, 'trade_date', None)
        if not use_date:
            use_date = datetime.now().strftime("%Y%m%d")

        self.add_records_from_positions(cctj_result.positions, trade_date=use_date)

    def load_from_position_manager(self, position_manager, trade_date: Optional[str] = None):
        """
        从持仓管理器加载台账

        Args:
            position_manager: PositionManager 对象
            trade_date: 交易日期
        """
        if not trade_date:
            trade_date = datetime.now().strftime("%Y%m%d")

        positions = position_manager.get_all_positions()
        self.add_records_from_positions(positions, trade_date=trade_date)
