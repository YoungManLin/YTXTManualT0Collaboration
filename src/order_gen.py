"""
DBF 订单生成器模块

基于持仓生成迅投 PB-DBF 预埋单
基于迅投 PB-DBF 预埋单参数说明文档 V2.15
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class OrderType(Enum):
    """订单类型"""
    BUY = "B"         # 买入
    SELL = "S"        # 卖出


class PriceType(Enum):
    """委托价格类型"""
    LIMIT = "1"       # 限价委托
    MARKET = "2"      # 市价委托
    BEST5 = "3"       # 最优五档
    COUNTER = "4"     # 对手方最优价格
    OWN = "5"         # 本方最优价格


@dataclass
class DBFOrder:
    """
    DBF 委托订单数据类

    对应迅投 PB-DBF V2.15 标准的 17 个字段
    """
    # 必填字段
    order_type: str           # 下单类型 (B/S)
    price_type: str           # 委托价格类型 (1/2/3/4/5)
    stock_code: str           # 证券代码
    volume: int               # 委托数量
    account_id: str           # 下单资金账号

    # 可选字段
    mode_price: Optional[float] = None    # 委托价格（限价时使用）
    act_type: Optional[str] = None        # 账号类别
    brokertype: Optional[str] = None      # 账号类型
    strategy: Optional[str] = None        # 策略备注
    note: Optional[str] = None            # 投资备注
    note1: Optional[str] = None           # 投资备注 2
    tradeparam: Optional[str] = None      # 交易参数
    command_id: Optional[str] = None      # 指令编号
    basketpath: Optional[str] = None      # 文件绝对路径
    inserttime: Optional[str] = None      # 写入时间
    extraparam: Optional[str] = None      # 额外参数
    batch_id: Optional[str] = None        # 批次 ID

    @property
    def key(self) -> str:
        """唯一键"""
        return f"{self.account_id}_{self.stock_code}_{self.order_type}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（中文列名，用于 Excel 导出）"""
        return {
            '下单类型': self.order_type,
            '委托价格类型': self.price_type,
            '委托价格': self.mode_price if self.mode_price else '',
            '证券代码': self.stock_code,
            '委托数量': self.volume,
            '下单资金账号': self.account_id,
            '账号类别': self.act_type if self.act_type else '',
            '账号类型': self.brokertype if self.brokertype else '',
            '策略备注': self.strategy if self.strategy else '',
            '投资备注': self.note if self.note else '',
            '投资备注 2': self.note1 if self.note1 else '',
            '交易参数': self.tradeparam if self.tradeparam else '',
            '指令编号': self.command_id if self.command_id else '',
            '文件路径': self.basketpath if self.basketpath else '',
            '写入时间': self.inserttime if self.inserttime else '',
            '额外参数': self.extraparam if self.extraparam else '',
            '批次 ID': self.batch_id if self.batch_id else '',
        }

    def to_dbf_dict(self) -> Dict[str, Any]:
        """转换为 DBF 格式字典（英文列名）"""
        return {
            'order_type': self.order_type,
            'price_type': self.price_type,
            'mode_price': self.mode_price if self.mode_price else None,
            'stock_code': self.stock_code,
            'volume': self.volume,
            'account_id': self.account_id,
            'act_type': self.act_type,
            'brokertype': self.brokertype,
            'strategy': self.strategy,
            'note': self.note,
            'note1': self.note1,
            'tradeparam': self.tradeparam,
            'command_id': self.command_id,
            'basketpath': self.basketpath,
            'inserttime': self.inserttime,
            'extraparam': self.extraparam,
            'batch_id': self.batch_id,
        }

    def validate(self) -> List[str]:
        """
        验证订单数据

        Returns:
            错误信息列表，空列表表示验证通过
        """
        errors = []

        # 必填字段检查
        if not self.order_type:
            errors.append("缺少下单类型")
        elif self.order_type not in ['B', 'S']:
            errors.append(f"无效的下单类型：{self.order_type}")

        if not self.price_type:
            errors.append("缺少委托价格类型")
        elif self.price_type not in ['1', '2', '3', '4', '5']:
            errors.append(f"无效的委托价格类型：{self.price_type}")

        if not self.stock_code:
            errors.append("缺少证券代码")

        if not self.volume or self.volume <= 0:
            errors.append(f"无效的委托数量：{self.volume}")

        # 买入数量应该是 100 的整数倍（A 股）
        if self.order_type == 'B' and self.volume % 100 != 0:
            errors.append(f"买入数量应为 100 的整数倍：{self.volume}")

        if not self.account_id:
            errors.append("缺少资金账号")

        # 限价委托必须有价格
        if self.price_type == '1' and not self.mode_price:
            errors.append("限价委托必须指定价格")

        if self.mode_price and self.mode_price <= 0:
            errors.append(f"无效的委托价格：{self.mode_price}")

        return errors


@dataclass
class OrderBatch:
    """订单批次"""
    batch_id: str
    orders: List[DBFOrder] = field(default_factory=list)
    create_time: datetime = field(default_factory=datetime.now)
    description: str = ""

    def add_order(self, order: DBFOrder):
        """添加订单"""
        order.batch_id = self.batch_id
        self.orders.append(order)

    def get_summary(self) -> Dict[str, Any]:
        """获取批次汇总"""
        buy_count = len([o for o in self.orders if o.order_type == 'B'])
        sell_count = len([o for o in self.orders if o.order_type == 'S'])
        buy_volume = sum(o.volume for o in self.orders if o.order_type == 'B')
        sell_volume = sum(o.volume for o in self.orders if o.order_type == 'S')

        return {
            'batch_id': self.batch_id,
            'total_orders': len(self.orders),
            'buy_orders': buy_count,
            'sell_orders': sell_count,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'create_time': self.create_time.isoformat(),
            'description': self.description,
        }


class OrderGenerator:
    """
    DBF 订单生成器

    基于持仓生成 T0 交易订单
    """

    # 迅投 PB-DBF V2.15 字段定义
    DBF_FIELDS = {
        'order_type': {'name': '下单类型', 'type': 'C', 'width': 10, 'required': True},
        'price_type': {'name': '委托价格类型', 'type': 'C', 'width': 10, 'required': True},
        'mode_price': {'name': '委托价格', 'type': 'N', 'width': 15, 'decimals': 3, 'required': False},
        'stock_code': {'name': '证券代码', 'type': 'C', 'width': 20, 'required': True},
        'volume': {'name': '委托数量', 'type': 'N', 'width': 15, 'decimals': 0, 'required': True},
        'account_id': {'name': '下单资金账号', 'type': 'C', 'width': 30, 'required': True},
        'act_type': {'name': '账号类别', 'type': 'C', 'width': 20, 'required': False},
        'brokertype': {'name': '账号类型', 'type': 'C', 'width': 20, 'required': False},
        'strategy': {'name': '策略备注', 'type': 'C', 'width': 50, 'required': False},
        'note': {'name': '投资备注', 'type': 'C', 'width': 100, 'required': False},
        'note1': {'name': '投资备注 2', 'type': 'C', 'width': 100, 'required': False},
        'tradeparam': {'name': '交易参数', 'type': 'C', 'width': 200, 'required': False},
        'command_id': {'name': '指令编号', 'type': 'C', 'width': 50, 'required': False},
        'basketpath': {'name': '文件路径', 'type': 'C', 'width': 200, 'required': False},
        'inserttime': {'name': '写入时间', 'type': 'C', 'width': 20, 'required': False},
        'extraparam': {'name': '额外参数', 'type': 'C', 'width': 200, 'required': False},
        'batch_id': {'name': '批次 ID', 'type': 'C', 'width': 50, 'required': False},
    }

    def __init__(self, default_price_type: str = '1'):
        """
        初始化生成器

        Args:
            default_price_type: 默认委托价格类型 ('1'=限价，'2'=市价)
        """
        self.default_price_type = default_price_type
        self.batches: Dict[str, OrderBatch] = {}
        self.orders: List[DBFOrder] = []
        self.errors: List[str] = []

    def create_batch(self, batch_id: Optional[str] = None,
                     description: str = "") -> OrderBatch:
        """
        创建订单批次

        Args:
            batch_id: 批次 ID（可选，自动生成）
            description: 批次描述

        Returns:
            OrderBatch 对象
        """
        if batch_id is None:
            batch_id = f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        batch = OrderBatch(
            batch_id=batch_id,
            description=description
        )
        self.batches[batch_id] = batch
        return batch

    def generate_sell_order(self, stock_code: str, account_id: str,
                            volume: int, price: Optional[float] = None,
                            price_type: Optional[str] = None,
                            strategy: Optional[str] = None,
                            note: Optional[str] = None) -> DBFOrder:
        """
        生成卖出订单

        Args:
            stock_code: 证券代码
            account_id: 资金账号
            volume: 卖出数量
            price: 卖出价格（限价委托时必填）
            price_type: 委托价格类型
            strategy: 策略备注
            note: 投资备注

        Returns:
            DBFOrder 对象
        """
        order = DBFOrder(
            order_type='S',
            price_type=price_type or self.default_price_type,
            stock_code=stock_code,
            volume=volume,
            account_id=account_id,
            mode_price=price,
            strategy=strategy,
            note=note,
            inserttime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )
        return order

    def generate_buy_order(self, stock_code: str, account_id: str,
                           volume: int, price: Optional[float] = None,
                           price_type: Optional[str] = None,
                           strategy: Optional[str] = None,
                           note: Optional[str] = None) -> DBFOrder:
        """
        生成买入订单

        Args:
            stock_code: 证券代码
            account_id: 资金账号
            volume: 买入数量
            price: 买入价格（限价委托时必填）
            price_type: 委托价格类型
            strategy: 策略备注
            note: 投资备注

        Returns:
            DBFOrder 对象
        """
        order = DBFOrder(
            order_type='B',
            price_type=price_type or self.default_price_type,
            stock_code=stock_code,
            volume=volume,
            account_id=account_id,
            mode_price=price,
            strategy=strategy,
            note=note,
            inserttime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )
        return order

    def generate_t0_sell_first_orders(self, stock_code: str, account_id: str,
                                      volume: int, sell_price: float,
                                      buy_price: float,
                                      strategy: Optional[str] = None) -> List[DBFOrder]:
        """
        生成先卖后买 T0 订单对

        Args:
            stock_code: 证券代码
            account_id: 资金账号
            volume: T0 数量
            sell_price: 卖出价格
            buy_price: 买入价格
            strategy: 策略备注

        Returns:
            [卖出订单，买入订单] 列表
        """
        sell_order = self.generate_sell_order(
            stock_code=stock_code,
            account_id=account_id,
            volume=volume,
            price=sell_price,
            strategy=strategy or "T0-先卖后买",
            note=f"T0 Sell @{sell_price}",
        )

        buy_order = self.generate_buy_order(
            stock_code=stock_code,
            account_id=account_id,
            volume=volume,
            price=buy_price,
            strategy=strategy or "T0-先卖后买",
            note=f"T0 Buy @{buy_price}",
        )

        return [sell_order, buy_order]

    def generate_t0_buy_first_orders(self, stock_code: str, account_id: str,
                                     volume: int, buy_price: float,
                                     sell_price: float,
                                     strategy: Optional[str] = None) -> List[DBFOrder]:
        """
        生成先买后卖 T0 订单对

        Args:
            stock_code: 证券代码
            account_id: 资金账号
            volume: T0 数量
            buy_price: 买入价格
            sell_price: 卖出价格
            strategy: 策略备注

        Returns:
            [买入订单，卖出订单] 列表
        """
        buy_order = self.generate_buy_order(
            stock_code=stock_code,
            account_id=account_id,
            volume=volume,
            price=buy_price,
            strategy=strategy or "T0-先买后卖",
            note=f"T0 Buy @{buy_price}",
        )

        sell_order = self.generate_sell_order(
            stock_code=stock_code,
            account_id=account_id,
            volume=volume,
            price=sell_price,
            strategy=strategy or "T0-先买后卖",
            note=f"T0 Sell @{sell_price}",
        )

        return [buy_order, sell_order]

    def add_order(self, order: DBFOrder, batch_id: Optional[str] = None) -> bool:
        """
        添加订单到列表或批次

        Args:
            order: DBFOrder 对象
            batch_id: 批次 ID（可选）

        Returns:
            是否成功添加
        """
        # 验证订单
        errors = order.validate()
        if errors:
            for err in errors:
                self.errors.append(f"订单验证失败：{err}")
            return False

        # 添加到批次或总列表
        if batch_id:
            batch = self.batches.get(batch_id)
            if not batch:
                self.errors.append(f"批次不存在：{batch_id}")
                return False
            batch.add_order(order)
        else:
            self.orders.append(order)

        return True

    def add_orders(self, orders: List[DBFOrder], batch_id: Optional[str] = None):
        """批量添加订单"""
        for order in orders:
            self.add_order(order, batch_id)

    def generate_from_positions(self, positions, t0_params: Dict[str, Any]) -> OrderBatch:
        """
        基于持仓生成订单

        Args:
            positions: PositionManager 对象
            t0_params: T0 参数配置
                {
                    'account_id': str,
                    'stock_code': str,
                    't0_type': 'SELL_FIRST' | 'BUY_FIRST',
                    'volume': int,
                    'sell_price': float,
                    'buy_price': float,
                }

        Returns:
            OrderBatch 对象
        """
        batch = self.create_batch(description="T0 订单批次")

        account_id = t0_params.get('account_id')
        stock_code = t0_params.get('stock_code')
        t0_type = t0_params.get('t0_type', 'SELL_FIRST')
        volume = t0_params.get('volume', 0)
        sell_price = t0_params.get('sell_price', 0.0)
        buy_price = t0_params.get('buy_price', 0.0)

        if t0_type == 'SELL_FIRST':
            orders = self.generate_t0_sell_first_orders(
                stock_code=stock_code,
                account_id=account_id,
                volume=volume,
                sell_price=sell_price,
                buy_price=buy_price,
            )
        else:
            orders = self.generate_t0_buy_first_orders(
                stock_code=stock_code,
                account_id=account_id,
                volume=volume,
                buy_price=buy_price,
                sell_price=sell_price,
            )

        self.add_orders(orders, batch.batch_id)
        return batch

    def validate_all(self) -> bool:
        """验证所有订单"""
        all_valid = True
        for order in self.orders:
            errors = order.validate()
            if errors:
                all_valid = False
                for err in errors:
                    self.errors.append(f"订单 {order.key}: {err}")

        for batch in self.batches.values():
            for order in batch.orders:
                errors = order.validate()
                if errors:
                    all_valid = False
                    for err in errors:
                        self.errors.append(f"批次{batch.batch_id} 订单 {order.key}: {err}")

        return all_valid

    def export_to_excel(self, output_path: Union[str, Path],
                        sheet_name: str = "详情") -> str:
        """
        导出订单到 Excel 文件

        Args:
            output_path: 输出文件路径
            sheet_name: 工作表名称

        Returns:
            实际输出路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 收集所有订单数据
        all_orders = list(self.orders)
        for batch in self.batches.values():
            all_orders.extend(batch.orders)

        if not all_orders:
            raise ValueError("没有可导出的订单")

        # 转换为 DataFrame（使用中文列名）
        data = [order.to_dict() for order in all_orders]
        df = pd.DataFrame(data)

        # 导出到 Excel
        df.to_excel(output_path, sheet_name=sheet_name, index=False, engine='openpyxl')

        return str(output_path)

    def export_to_csv(self, output_path: Union[str, Path]) -> str:
        """导出订单到 CSV 文件"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        all_orders = list(self.orders)
        for batch in self.batches.values():
            all_orders.extend(batch.orders)

        if not all_orders:
            raise ValueError("没有可导出的订单")

        data = [order.to_dict() for order in all_orders]
        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')

        return str(output_path)

    def get_summary(self) -> Dict[str, Any]:
        """获取汇总信息"""
        all_orders = list(self.orders)
        for batch in self.batches.values():
            all_orders.extend(batch.orders)

        buy_count = len([o for o in all_orders if o.order_type == 'B'])
        sell_count = len([o for o in all_orders if o.order_type == 'S'])
        buy_volume = sum(o.volume for o in all_orders if o.order_type == 'B')
        sell_volume = sum(o.volume for o in all_orders if o.order_type == 'S')

        return {
            'total_orders': len(all_orders),
            'buy_orders': buy_count,
            'sell_orders': sell_count,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'batches': len(self.batches),
            'errors': len(self.errors),
        }

    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame"""
        all_orders = list(self.orders)
        for batch in self.batches.values():
            all_orders.extend(batch.orders)

        if not all_orders:
            return pd.DataFrame()

        return pd.DataFrame([order.to_dict() for order in all_orders])
