"""
仓位计算核心模块 - 简化版
"""

import pandas as pd
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class Position:
    """仓位数据类"""
    stock_code: str
    account_id: str
    strategy: str
    total_volume: int = 0
    available_volume: int = 0
    frozen_volume: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    profit_loss: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'stock_code': self.stock_code,
            'account_id': self.account_id,
            'strategy': self.strategy,
            'total_volume': self.total_volume,
            'market_value': self.market_value,
            'profit_loss': self.profit_loss,
        }


class PositionCalculator:
    """仓位计算器"""
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.orders = []
        self.prices: Dict[str, float] = {}
    
    def load_orders(self, orders):
        self.orders = orders
    
    def set_prices(self, prices: Dict[str, float]):
        self.prices = prices
    
    def calculate(self) -> Dict[str, Position]:
        """计算仓位"""
        self.positions = {}
        
        # 简化计算：按股票 + 账户分组
        order_groups = {}
        for order in self.orders:
            key = f"{order.stock_code}_{order.account_id}"
            if key not in order_groups:
                order_groups[key] = []
            order_groups[key].append(order)
        
        # 计算每个分组的仓位
        for key, orders in order_groups.items():
            stock_code = orders[0].stock_code
            account_id = orders[0].account_id
            
            total_volume = sum(int(o.volume) if o.volume.isdigit() else 0 for o in orders)
            current_price = self.prices.get(stock_code, 0)
            
            self.positions[key] = Position(
                stock_code=stock_code,
                account_id=account_id,
                strategy=orders[0].strategy or 'DEFAULT',
                total_volume=total_volume,
                available_volume=total_volume,
                current_price=current_price,
                market_value=total_volume * current_price,
            )
        
        return self.positions
    
    def get_summary(self) -> Dict:
        if not self.positions:
            return {'total_positions': 0}
        
        total_value = sum(p.market_value for p in self.positions.values())
        total_pl = sum(p.profit_loss for p in self.positions.values())
        
        return {
            'total_positions': len(self.positions),
            'total_market_value': total_value,
            'total_profit_loss': total_pl,
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        if not self.positions:
            return pd.DataFrame()
        return pd.DataFrame([p.to_dict() for p in self.positions.values()])
    
    def export_report(self, output_path: str):
        df = self.to_dataframe()
        df.to_excel(output_path, index=False, engine='openpyxl')
