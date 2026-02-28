"""
持仓管理模块

管理真实持仓和虚拟持仓 (T0 临时仓位)
支持多账户、多股票持仓管理
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict
import copy


class PositionSide(Enum):
    """持仓方向"""
    LONG = "LONG"       # 多头持仓
    SHORT = "SHORT"     # 空头持仓 (融券)


class PositionStatus(Enum):
    """持仓状态"""
    ACTIVE = "ACTIVE"       # 活跃持仓
    FROZEN = "FROZEN"       # 冻结持仓
    CLOSED = "CLOSED"       # 已平仓


class RealPosition:
    """
    真实持仓类

    来自 CCTJ 文件的实际持仓数据
    """

    def __init__(
        self,
        stock_code: str,
        stock_name: str,
        account_id: str,
        market_id: str,
        total_volume: int = 0,
        available_volume: int = 0,
        frozen_volume: int = 0,
        yesterday_volume: int = 0,
        today_volume: int = 0,
        cost_price: float = 0.0,
        current_price: float = 0.0,
        status: PositionStatus = PositionStatus.ACTIVE,
        update_time: Optional[datetime] = None,
    ):
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.account_id = account_id
        self.market_id = market_id
        self.total_volume = total_volume
        self.available_volume = available_volume
        self.frozen_volume = frozen_volume
        self.yesterday_volume = yesterday_volume
        self.today_volume = today_volume
        self.cost_price = cost_price
        self.current_price = current_price
        self.status = status
        self.update_time = update_time

    @property
    def cost_amount(self) -> float:
        """成本金额"""
        return self.total_volume * self.cost_price

    @property
    def market_value(self) -> float:
        """市值"""
        return self.total_volume * self.current_price

    @property
    def profit_loss(self) -> float:
        """浮动盈亏"""
        return (self.current_price - self.cost_price) * self.total_volume

    @property
    def key(self) -> str:
        """获取唯一键"""
        return f"{self.stock_code}_{self.account_id}"

    @property
    def sellable_volume(self) -> int:
        """可卖出数量"""
        if self.status == PositionStatus.FROZEN:
            return 0
        return self.available_volume

    @property
    def buyable_volume(self) -> int:
        """可继续买入的参考数量（基于可用资金，此处仅返回占位）"""
        # 实际可买数量需要结合账户资金计算
        return self.available_volume

    def update_price(self, price: float):
        """更新当前价"""
        self.current_price = price

    def freeze(self, volume: int) -> bool:
        """
        冻结指定数量

        Args:
            volume: 冻结数量

        Returns:
            是否成功
        """
        if volume <= 0 or volume > self.available_volume:
            return False

        self.available_volume -= volume
        self.frozen_volume += volume
        return True

    def unfreeze(self, volume: int) -> bool:
        """解冻指定数量"""
        if volume <= 0 or volume > self.frozen_volume:
            return False

        self.frozen_volume -= volume
        self.available_volume += volume
        return True

    def reduce(self, volume: int) -> bool:
        """
        减少持仓（卖出）

        Args:
            volume: 卖出数量

        Returns:
            是否成功
        """
        if volume <= 0 or volume > self.available_volume:
            return False

        self.total_volume -= volume
        self.available_volume -= volume
        # cost_amount 是计算属性，不需要更新
        return True

    def increase(self, volume: int, price: float) -> bool:
        """
        增加持仓（买入）

        Args:
            volume: 买入数量
            price: 买入价格

        Returns:
            是否成功
        """
        if volume <= 0:
            return False

        # 计算新的成本价（加权平均）
        old_cost_amount = self.cost_amount
        new_cost = volume * price
        self.total_volume += volume
        self.today_volume += volume

        if self.total_volume > 0:
            self.cost_price = (old_cost_amount + new_cost) / self.total_volume

        return True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'account_id': self.account_id,
            'market_id': self.market_id,
            'total_volume': self.total_volume,
            'available_volume': self.available_volume,
            'frozen_volume': self.frozen_volume,
            'yesterday_volume': self.yesterday_volume,
            'today_volume': self.today_volume,
            'cost_price': self.cost_price,
            'current_price': self.current_price,
            'market_value': self.market_value,
            'cost_amount': self.cost_amount,
            'profit_loss': self.profit_loss,
            'status': self.status.value,
            'update_time': self.update_time.isoformat() if self.update_time else None,
        }


@dataclass
class VirtualPosition:
    """
    虚拟持仓类

    T0 交易产生的临时仓位
    用于跟踪 T0 交易的开仓和平仓状态
    """
    stock_code: str             # 证券代码
    account_id: str             # 资金账号
    position_id: str            # 虚拟持仓 ID（唯一）

    # T0 类型
    t0_type: str = "SELL_FIRST"  # "SELL_FIRST" 先卖后买，"BUY_FIRST" 先买后卖

    # 开仓信息
    open_volume: int = 0        # 开仓数量
    open_price: float = 0.0     # 开仓均价
    open_time: Optional[datetime] = None

    # 平仓信息
    closed_volume: int = 0      # 已平仓数量
    close_price: float = 0.0    # 平仓均价
    close_time: Optional[datetime] = None

    # 盈亏
    profit_loss: float = 0.0    # T0 盈亏
    profit_rate: float = 0.0    # 盈亏率

    # 状态
    status: PositionStatus = PositionStatus.ACTIVE

    @property
    def key(self) -> str:
        """获取唯一键"""
        return f"{self.position_id}"

    @property
    def remaining_volume(self) -> int:
        """剩余未平仓数量"""
        return self.open_volume - self.closed_volume

    @property
    def is_closed(self) -> bool:
        """是否已完全平仓"""
        return self.remaining_volume <= 0

    def open(self, volume: int, price: float, t0_type: str = "SELL_FIRST"):
        """
        开仓

        Args:
            volume: 开仓数量
            price: 开仓价格
            t0_type: T0 类型
        """
        self.open_volume = volume
        self.open_price = price
        self.t0_type = t0_type
        self.open_time = datetime.now()
        self.status = PositionStatus.ACTIVE

    def close_partial(self, volume: int, price: float) -> float:
        """
        部分平仓

        Args:
            volume: 平仓数量
            price: 平仓价格

        Returns:
            本次平仓盈亏
        """
        if volume <= 0 or volume > self.remaining_volume:
            return 0.0

        # 计算本次平仓盈亏
        if self.t0_type == "SELL_FIRST":
            # 先卖后买：卖出价 - 买入价
            profit = (self.open_price - price) * volume
        else:
            # 先买后卖：买入价 - 卖出价
            profit = (price - self.open_price) * volume

        # 更新累计盈亏
        total_volume = self.closed_volume + volume
        self.profit_loss = self.profit_loss + profit

        self.closed_volume += volume
        self.close_price = price
        self.close_time = datetime.now()

        if self.open_volume > 0:
            self.profit_rate = self.profit_loss / (self.open_price * self.open_volume) * 100

        # 检查是否完全平仓
        if self.is_closed:
            self.status = PositionStatus.CLOSED

        return profit

    def close_all(self, price: float) -> float:
        """
        完全平仓

        Args:
            price: 平仓价格

        Returns:
            总盈亏
        """
        return self.close_partial(self.remaining_volume, price)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'position_id': self.position_id,
            'stock_code': self.stock_code,
            'account_id': self.account_id,
            't0_type': self.t0_type,
            'open_volume': self.open_volume,
            'open_price': self.open_price,
            'closed_volume': self.closed_volume,
            'close_price': self.close_price,
            'remaining_volume': self.remaining_volume,
            'profit_loss': self.profit_loss,
            'profit_rate': round(self.profit_rate, 4),
            'status': self.status.value,
            'open_time': self.open_time.isoformat() if self.open_time else None,
            'close_time': self.close_time.isoformat() if self.close_time else None,
        }


@dataclass
class AccountPosition:
    """
    账户持仓汇总

    单个账户的所有持仓（真实 + 虚拟）
    """
    account_id: str
    positions: Dict[str, RealPosition] = field(default_factory=dict)  # stock_code -> RealPosition
    virtual_positions: Dict[str, VirtualPosition] = field(default_factory=dict)  # position_id -> VirtualPosition

    @property
    def total_market_value(self) -> float:
        """总持仓市值"""
        return sum(p.market_value for p in self.positions.values())

    @property
    def total_cost(self) -> float:
        """总成本"""
        return sum(p.cost_amount for p in self.positions.values())

    @property
    def total_profit_loss(self) -> float:
        """总盈亏"""
        return sum(p.profit_loss for p in self.positions.values())

    @property
    def t0_profit_loss(self) -> float:
        """T0 总盈亏"""
        return sum(vp.profit_loss for vp in self.virtual_positions.values())

    def get_position(self, stock_code: str) -> Optional[RealPosition]:
        """获取某股票的真实持仓"""
        return self.positions.get(stock_code)

    def get_virtual_positions(self, stock_code: str) -> List[VirtualPosition]:
        """获取某股票的虚拟持仓列表"""
        return [vp for vp in self.virtual_positions.values() if vp.stock_code == stock_code]

    def add_position(self, position: RealPosition):
        """添加真实持仓"""
        self.positions[position.stock_code] = position

    def remove_position(self, stock_code: str):
        """移除真实持仓"""
        if stock_code in self.positions:
            del self.positions[stock_code]

    def add_virtual_position(self, vp: VirtualPosition):
        """添加虚拟持仓"""
        self.virtual_positions[vp.position_id] = vp

    def get_summary(self) -> Dict[str, Any]:
        """获取账户汇总"""
        return {
            'account_id': self.account_id,
            'real_positions_count': len(self.positions),
            'virtual_positions_count': len(self.virtual_positions),
            'total_market_value': round(self.total_market_value, 2),
            'total_cost': round(self.total_cost, 2),
            'total_profit_loss': round(self.total_profit_loss, 2),
            't0_profit_loss': round(self.t0_profit_loss, 2),
            'active_t0_count': len([vp for vp in self.virtual_positions.values()
                                    if vp.status == PositionStatus.ACTIVE]),
        }


class PositionManager:
    """
    持仓管理器

    管理所有账户的真实持仓和虚拟持仓
    """

    def __init__(self):
        self.accounts: Dict[str, AccountPosition] = {}  # account_id -> AccountPosition
        self.update_time: Optional[datetime] = None

    def load_from_cctj(self, cctj_result) -> int:
        """
        从 CCTJ 解析结果加载真实持仓

        Args:
            cctj_result: CCTJParseResult 对象

        Returns:
            加载的持仓数量
        """
        count = 0
        for pos in cctj_result.positions:
            real_pos = RealPosition(
                stock_code=pos.stock_code,
                stock_name=pos.stock_name,
                account_id=pos.account_id,
                market_id=pos.market_id,
                total_volume=pos.total_volume,
                available_volume=pos.available_volume,
                frozen_volume=pos.frozen_volume,
                yesterday_volume=pos.yesterday_volume,
                today_volume=pos.today_volume,
                cost_price=pos.cost_price,
                current_price=pos.current_price,
                market_value=pos.market_value,
                cost_amount=pos.cost_amount,
                profit_loss=pos.profit_loss,
                update_time=datetime.now(),
            )

            # 获取或创建账户持仓
            account = self.get_or_create_account(pos.account_id)
            account.add_position(real_pos)
            count += 1

        self.update_time = datetime.now()
        return count

    def get_or_create_account(self, account_id: str) -> AccountPosition:
        """获取或创建账户持仓"""
        if account_id not in self.accounts:
            self.accounts[account_id] = AccountPosition(account_id=account_id)
        return self.accounts[account_id]

    def get_account(self, account_id: str) -> Optional[AccountPosition]:
        """获取账户持仓"""
        return self.accounts.get(account_id)

    def get_all_positions(self) -> List[RealPosition]:
        """获取所有真实持仓"""
        positions = []
        for account in self.accounts.values():
            positions.extend(account.positions.values())
        return positions

    def get_position(self, account_id: str, stock_code: str) -> Optional[RealPosition]:
        """获取指定账户的指定股票持仓"""
        account = self.accounts.get(account_id)
        if account:
            return account.get_position(stock_code)
        return None

    def get_sellable_volume(self, account_id: str, stock_code: str) -> int:
        """获取指定账户的指定股票可卖数量"""
        pos = self.get_position(account_id, stock_code)
        if pos:
            return pos.sellable_volume
        return 0

    def update_price(self, stock_code: str, price: float):
        """更新所有账户中某股票的当前价"""
        for account in self.accounts.values():
            pos = account.positions.get(stock_code)
            if pos:
                pos.update_price(price)

    def execute_t0_sell_first(self, account_id: str, stock_code: str,
                              volume: int, sell_price: float,
                              buy_price: float) -> Optional[VirtualPosition]:
        """
        执行先卖后买 T0

        Args:
            account_id: 账户 ID
            stock_code: 证券代码
            volume: T0 数量
            sell_price: 卖出价格
            buy_price: 买入价格

        Returns:
            虚拟持仓对象，失败返回 None
        """
        account = self.accounts.get(account_id)
        if not account:
            return None

        position = account.positions.get(stock_code)
        if not position:
            return None

        # 检查可卖数量
        if volume > position.sellable_volume:
            return None

        # 创建虚拟持仓
        vp = VirtualPosition(
            position_id=f"T0_{account_id}_{stock_code}_{datetime.now().strftime('%H%M%S%f')}",
            stock_code=stock_code,
            account_id=account_id,
        )

        # 执行卖出（减少真实持仓）
        position.reduce(volume)

        # 开仓（先卖）
        vp.open(volume, sell_price, t0_type="SELL_FIRST")

        # 执行买入（平仓）
        vp.close_all(buy_price)

        # 恢复真实持仓（买入的数量加回）
        position.increase(volume, buy_price)

        account.add_virtual_position(vp)
        self.update_time = datetime.now()

        return vp

    def execute_t0_buy_first(self, account_id: str, stock_code: str,
                             volume: int, buy_price: float,
                             sell_price: float) -> Optional[VirtualPosition]:
        """
        执行先买后卖 T0

        Args:
            account_id: 账户 ID
            stock_code: 证券代码
            volume: T0 数量
            buy_price: 买入价格
            sell_price: 卖出价格

        Returns:
            虚拟持仓对象，失败返回 None
        """
        account = self.accounts.get(account_id)
        if not account:
            return None

        position = account.positions.get(stock_code)
        if not position:
            return None

        # 创建虚拟持仓
        vp = VirtualPosition(
            position_id=f"T0_{account_id}_{stock_code}_{datetime.now().strftime('%H%M%S%f')}",
            stock_code=stock_code,
            account_id=account_id,
        )

        # 开仓（先买）
        vp.open(volume, buy_price, t0_type="BUY_FIRST")

        # 执行卖出（平仓）
        vp.close_all(sell_price)

        # 真实持仓不变（先买后卖不改变底仓）

        account.add_virtual_position(vp)
        self.update_time = datetime.now()

        return vp

    def get_summary(self) -> Dict[str, Any]:
        """获取总汇总"""
        total_mv = sum(acc.total_market_value for acc in self.accounts.values())
        total_cost = sum(acc.total_cost for acc in self.accounts.values())
        total_pl = sum(acc.total_profit_loss for acc in self.accounts.values())
        total_t0_pl = sum(acc.t0_profit_loss for acc in self.accounts.values())

        return {
            'account_count': len(self.accounts),
            'total_positions': sum(len(acc.positions) for acc in self.accounts.values()),
            'total_virtual_positions': sum(len(acc.virtual_positions) for acc in self.accounts.values()),
            'total_market_value': round(total_mv, 2),
            'total_cost': round(total_cost, 2),
            'total_profit_loss': round(total_pl, 2),
            'total_t0_profit_loss': round(total_t0_pl, 2),
            'update_time': self.update_time.isoformat() if self.update_time else None,
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'accounts': {aid: acc.get_summary() for aid, acc in self.accounts.items()},
            'summary': self.get_summary(),
        }
