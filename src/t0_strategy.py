"""T0 策略模块 - 简化版"""

from typing import Dict, List
from dataclasses import dataclass


@dataclass
class T0Signal:
    stock_code: str
    account_id: str
    signal_type: str
    target_volume: int
    reason: str


class T0Strategy:
    def __init__(self):
        self.signals: List[T0Signal] = []
    
    def generate_signals(self, positions, prices):
        self.signals = []
        return self.signals
    
    def get_signal_summary(self) -> Dict:
        return {
            'total_signals': len(self.signals),
            'signals': [s.__dict__ for s in self.signals],
        }
