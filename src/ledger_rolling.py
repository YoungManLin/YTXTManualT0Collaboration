"""
台账滚动计算模块

实现 T0 策略核心公式：Ledger_T = Ledger_{T-1} × AF_T + E_T

其中：
- Ledger_T: T 日台账
- Ledger_{T-1}: T-1 日台账
- AF_T: T 日除权因子 (Adjustment Factor)
- E_T: T 日调整额 (如分红、配股等)
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AdjustmentType(Enum):
    """
    调整类型枚举
    """
    DIVIDEND = "dividend"           # 分红
    RIGHTS_ISSUE = "rights_issue"   # 配股
    BONUS_SHARE = "bonus_share"     # 送股
    SPLIT = "split"                 # 拆细/拆股
    REVERSE_SPLIT = "reverse_split" # 合股
    SPECIAL = "special"             # 特殊调整


@dataclass
class AdjustmentEvent:
    """
    调整事件类

    记录导致台账变化的事件
    """
    trade_date: str                       # 交易日期
    stock_code: str                       # 证券代码
    adjustment_type: AdjustmentType       # 调整类型
    adjustment_factor: float = 1.0        # 除权因子 AF_T
    adjustment_amount: float = 0.0        # 调整金额 E_T
    adjustment_volume: int = 0            # 调整数量（如送股）
    description: str = ""                 # 描述
    record_time: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @property
    def key(self) -> str:
        """唯一键"""
        return f"{self.trade_date}_{self.stock_code}"

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'trade_date': self.trade_date,
            'stock_code': self.stock_code,
            'adjustment_type': self.adjustment_type.value,
            'adjustment_factor': self.adjustment_factor,
            'adjustment_amount': self.adjustment_amount,
            'adjustment_volume': self.adjustment_volume,
            'description': self.description,
            'record_time': self.record_time,
        }


@dataclass
class LedgerRollingState:
    """
    台账滚动状态类

    记录单个证券的台账滚动状态
    """
    stock_code: str                       # 证券代码
    stock_name: str = ""                  # 证券名称
    account_id: str = ""                  # 账户 ID

    # 台账值
    previous_ledger: float = 0.0          # Ledger_{T-1}
    current_ledger: float = 0.0           # Ledger_T

    # 计算明细
    adjustment_factor: float = 1.0        # AF_T
    adjustment_amount: float = 0.0        # E_T

    # 交易日
    previous_date: str = ""               # T-1 日
    current_date: str = ""                # T 日

    @property
    def key(self) -> str:
        """唯一键"""
        return f"{self.account_id}_{self.stock_code}"

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'account_id': self.account_id,
            'previous_ledger': round(self.previous_ledger, 4),
            'current_ledger': round(self.current_ledger, 4),
            'adjustment_factor': self.adjustment_factor,
            'adjustment_amount': round(self.adjustment_amount, 4),
            'previous_date': self.previous_date,
            'current_date': self.current_date,
        }


class LedgerRollingCalculator:
    """
    台账滚动计算器

    实现核心公式：Ledger_T = Ledger_{T-1} × AF_T + E_T

    功能：
    1. 计算除权因子（基于公司行为）
    2. 执行台账滚动计算
    3. 支持多账户、多证券管理
    4. 记录计算历史
    """

    def __init__(self):
        """
        初始化台账滚动计算器
        """
        # 状态存储：key -> LedgerRollingState
        self._states: Dict[str, LedgerRollingState] = {}

        # 调整事件历史：stock_code -> List[AdjustmentEvent]
        self._adjustment_history: Dict[str, List[AdjustmentEvent]] = {}

        # 计算历史：key -> List[Dict]
        self._calculation_history: Dict[str, List[Dict]] = {}

    def _get_state_key(self, account_id: str, stock_code: str) -> str:
        """生成状态唯一键"""
        return f"{account_id}_{stock_code}"

    def _get_or_create_state(
        self,
        account_id: str,
        stock_code: str,
        stock_name: str = ""
    ) -> LedgerRollingState:
        """获取或创建状态"""
        key = self._get_state_key(account_id, stock_code)

        if key not in self._states:
            self._states[key] = LedgerRollingState(
                stock_code=stock_code,
                stock_name=stock_name,
                account_id=account_id,
            )

        return self._states[key]

    def calculate_adjustment_factor(
        self,
        dividend_per_share: float = 0.0,      # 每股分红
        rights_ratio: float = 0.0,            # 配股比例（如 10 配 3 = 0.3）
        rights_price: float = 0.0,            # 配股价
        bonus_ratio: float = 0.0,             # 送股比例（如 10 送 3 = 0.3）
        split_ratio: float = 1.0,             # 拆细比例（如 1 拆 2 = 2.0）
        current_price: float = 0.0,           # 当前股价（用于计算理论除权价）
    ) -> float:
        """
        计算除权因子 AF_T

        除权因子用于调整台账以反映公司行为的影响

        公式：
        - 分红除权：AF = 1（分红通过 E_T 调整金额体现）
        - 配股除权：AF = (P + P_rights × ratio) / (P × (1 + ratio))
        - 送股除权：AF = 1 / (1 + bonus_ratio)
        - 拆细除权：AF = 1 / split_ratio

        综合公式（简化）：
        AF = 1 / (1 + bonus_ratio + rights_ratio) × (1 + adjustment_from_price)

        Args:
            dividend_per_share: 每股分红
            rights_ratio: 配股比例
            rights_price: 配股价
            bonus_ratio: 送股比例
            split_ratio: 拆细比例
            current_price: 当前股价

        Returns:
            除权因子 AF_T
        """
        af = 1.0

        # 送股调整
        if bonus_ratio > 0:
            af = af / (1 + bonus_ratio)

        # 配股调整（简化计算）
        if rights_ratio > 0 and current_price > 0:
            # 理论除权价 = (原价 + 配股价 × 配股比例) / (1 + 配股比例)
            # AF = 理论除权价 / 原价
            theoretical_ex_rights_price = (current_price + rights_price * rights_ratio) / (1 + rights_ratio)
            af = af * (theoretical_ex_rights_price / current_price)

        # 拆细调整
        if split_ratio > 0 and split_ratio != 1.0:
            af = af / split_ratio

        return af

    def calculate_adjustment_amount(
        self,
        previous_ledger: float,
        dividend_per_share: float = 0.0,      # 每股分红
        total_shares: int = 0,                # 总股数
        special_adjustment: float = 0.0,      # 特殊调整
    ) -> float:
        """
        计算调整额 E_T

        调整额包括：
        - 现金分红
        - 特殊调整项

        Args:
            previous_ledger: 前一日台账
            dividend_per_share: 每股分红
            total_shares: 总股数
            special_adjustment: 特殊调整

        Returns:
            调整额 E_T
        """
        e_t = 0.0

        # 现金分红调整
        if dividend_per_share > 0 and total_shares > 0:
            e_t += dividend_per_share * total_shares

        # 特殊调整
        if special_adjustment != 0:
            e_t += special_adjustment

        return e_t

    def roll(
        self,
        account_id: str,
        stock_code: str,
        stock_name: str = "",
        adjustment_factor: Optional[float] = None,
        adjustment_amount: float = 0.0,
        trade_date: str = "",
        events: Optional[List[AdjustmentEvent]] = None,
    ) -> LedgerRollingState:
        """
        执行台账滚动计算

        核心公式：Ledger_T = Ledger_{T-1} × AF_T + E_T

        Args:
            account_id: 账户 ID
            stock_code: 证券代码
            stock_name: 证券名称
            adjustment_factor: 除权因子 AF_T（可选，优先使用）
            adjustment_amount: 调整额 E_T
            trade_date: 交易日期
            events: 调整事件列表（可选，用于自动计算 AF_T）

        Returns:
            LedgerRollingState 更新后的状态

        Raises:
            ValueError: 当参数无效时
        """
        if not account_id:
            raise ValueError("account_id 不能为空")
        if not stock_code:
            raise ValueError("stock_code 不能为空")

        # 获取或创建状态
        state = self._get_or_create_state(account_id, stock_code, stock_name)

        # 保存前一日状态
        state.previous_ledger = state.current_ledger if state.current_ledger != 0 else state.previous_ledger
        state.previous_date = state.current_date

        # 更新当前日期
        state.current_date = trade_date or datetime.now().strftime("%Y%m%d")

        # 计算或更新除权因子
        if adjustment_factor is None and events:
            # 从事件计算综合除权因子
            adjustment_factor = self._calculate_composite_adjustment_factor(events)

        if adjustment_factor is None:
            adjustment_factor = 1.0

        state.adjustment_factor = adjustment_factor
        state.adjustment_amount = adjustment_amount

        # 核心公式：Ledger_T = Ledger_{T-1} × AF_T + E_T
        state.current_ledger = state.previous_ledger * adjustment_factor + adjustment_amount

        # 记录计算历史
        self._record_calculation(state, trade_date)

        return state

    def _calculate_composite_adjustment_factor(
        self,
        events: List[AdjustmentEvent]
    ) -> float:
        """
        从多个调整事件计算综合除权因子

        Args:
            events: 调整事件列表

        Returns:
            综合除权因子
        """
        composite_af = 1.0

        for event in events:
            composite_af *= event.adjustment_factor

        return composite_af

    def _record_calculation(self, state: LedgerRollingState, trade_date: str):
        """记录计算历史"""
        key = state.key

        if key not in self._calculation_history:
            self._calculation_history[key] = []

        history_entry = {
            'trade_date': trade_date,
            'previous_ledger': state.previous_ledger,
            'adjustment_factor': state.adjustment_factor,
            'adjustment_amount': state.adjustment_amount,
            'current_ledger': state.current_ledger,
            'calculation': f"{state.previous_ledger} × {state.adjustment_factor} + {state.adjustment_amount} = {state.current_ledger}",
        }

        self._calculation_history[key].append(history_entry)

    def get_state(self, account_id: str, stock_code: str) -> Optional[LedgerRollingState]:
        """
        获取指定账户和证券的状态

        Args:
            account_id: 账户 ID
            stock_code: 证券代码

        Returns:
            LedgerRollingState 或 None
        """
        key = self._get_state_key(account_id, stock_code)
        return self._states.get(key)

    def get_current_ledger(self, account_id: str, stock_code: str) -> float:
        """
        获取当前台账值

        Args:
            account_id: 账户 ID
            stock_code: 证券代码

        Returns:
            当前台账值，不存在则返回 0
        """
        state = self.get_state(account_id, stock_code)
        return state.current_ledger if state else 0.0

    def get_all_states(self) -> List[LedgerRollingState]:
        """获取所有状态"""
        return list(self._states.values())

    def get_calculation_history(
        self,
        account_id: str,
        stock_code: str
    ) -> List[Dict]:
        """
        获取指定账户和证券的计算历史

        Args:
            account_id: 账户 ID
            stock_code: 证券代码

        Returns:
            计算历史列表
        """
        key = self._get_state_key(account_id, stock_code)
        return self._calculation_history.get(key, [])

    def add_adjustment_event(self, event: AdjustmentEvent):
        """
        添加调整事件

        Args:
            event: 调整事件
        """
        if event.stock_code not in self._adjustment_history:
            self._adjustment_history[event.stock_code] = []

        self._adjustment_history[event.stock_code].append(event)

    def get_adjustment_history(self, stock_code: str) -> List[AdjustmentEvent]:
        """
        获取指定证券的调整事件历史

        Args:
            stock_code: 证券代码

        Returns:
            调整事件列表
        """
        return self._adjustment_history.get(stock_code, [])

    def reset(self, account_id: str, stock_code: str):
        """
        重置指定账户和证券的状态

        Args:
            account_id: 账户 ID
            stock_code: 证券代码
        """
        key = self._get_state_key(account_id, stock_code)

        if key in self._states:
            state = self._states[key]
            state.previous_ledger = 0.0
            state.current_ledger = 0.0
            state.adjustment_factor = 1.0
            state.adjustment_amount = 0.0
            state.previous_date = ""
            state.current_date = ""

    def clear(self):
        """清空所有状态和历史"""
        self._states.clear()
        self._adjustment_history.clear()
        self._calculation_history.clear()

    def initialize_ledger(
        self,
        account_id: str,
        stock_code: str,
        stock_name: str = "",
        initial_ledger: float = 0.0,
        trade_date: str = ""
    ) -> LedgerRollingState:
        """
        初始化台账

        用于设置初始台账值（如 T0 策略启动时）

        Args:
            account_id: 账户 ID
            stock_code: 证券代码
            stock_name: 证券名称
            initial_ledger: 初始台账值
            trade_date: 交易日期

        Returns:
            LedgerRollingState 初始化后的状态
        """
        key = self._get_state_key(account_id, stock_code)

        state = LedgerRollingState(
            stock_code=stock_code,
            stock_name=stock_name,
            account_id=account_id,
            current_ledger=initial_ledger,
            previous_ledger=initial_ledger,
            current_date=trade_date or datetime.now().strftime("%Y%m%d"),
            previous_date=trade_date or datetime.now().strftime("%Y%m%d"),
        )

        self._states[key] = state

        return state
