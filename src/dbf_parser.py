"""
DBF 预埋单文件解析模块

基于迅投 PB-DBF 预埋单参数说明文档 V2.15
支持读取 XT_DBF_ORDER.dbf 格式的委托文件
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DBFOrder:
    """DBF 委托订单数据类"""
    order_type: str  # 下单类型
    price_type: str  # 委托价格类型
    mode_price: Optional[str]  # 委托价格
    stock_code: str  # 证券代码
    volume: str  # 委托数量
    account_id: str  # 下单资金账号
    act_type: Optional[str]  # 账号类别
    brokertype: Optional[str]  # 账号类型
    strategy: Optional[str]  # 策略备注
    note: Optional[str]  # 投资备注
    note1: Optional[str]  # 投资备注 2
    tradeparam: Optional[str]  # 交易参数
    command_id: Optional[str]  # 指令编号
    basketpath: Optional[str]  # 文件绝对路径
    inserttime: Optional[str]  # 写入时间
    extraparam: Optional[str]  # 额外参数
    batch_id: Optional[str]  # 批次 ID
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'order_type': self.order_type,
            'price_type': self.price_type,
            'mode_price': self.mode_price,
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


class DBFParser:
    """
    DBF 预埋单文件解析器
    
    支持格式：
    - .dbf 文件（原生 DBF 格式）
    - .xlsx 文件（Excel 导出格式）
    - .csv 文件（CSV 导出格式）
    """
    
    # DBF 字段映射（迅投 PB-DBF V2.15）
    FIELD_MAPPING = {
        'order_type': '下单类型',
        'price_type': '委托价格类型',
        'mode_price': '委托价格',
        'stock_code': '证券代码',
        'volume': '委托数量',
        'account_id': '下单资金账号',
        'act_type': '账号类别',
        'brokertype': '账号类型',
        'strategy': '策略备注',
        'note': '投资备注',
        'note1': '投资备注 2',
        'tradeparam': '交易参数',
        'command_id': '指令编号',
        'basketpath': '文件路径',
        'inserttime': '写入时间',
        'extraparam': '额外参数',
        'batch_id': '批次 ID',
    }
    
    # 必填字段
    REQUIRED_FIELDS = ['order_type', 'price_type', 'stock_code', 'volume', 'account_id']
    
    def __init__(self, file_path: Union[str, Path]):
        """
        初始化解析器
        
        Args:
            file_path: DBF/Excel/CSV文件路径
        """
        self.file_path = Path(file_path)
        self.orders: List[DBFOrder] = []
        self.df: Optional[pd.DataFrame] = None
        self.parse_errors: List[str] = []
        
    def parse(self) -> List[DBFOrder]:
        """
        解析文件
        
        Returns:
            DBFOrder 对象列表
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不支持
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件不存在：{self.file_path}")
        
        suffix = self.file_path.suffix.lower()
        
        if suffix == '.dbf':
            self._parse_dbf()
        elif suffix in ['.xlsx', '.xls']:
            self._parse_excel()
        elif suffix == '.csv':
            self._parse_csv()
        else:
            raise ValueError(f"不支持的文件格式：{suffix}")
        
        return self.orders
    
    def _parse_dbf(self):
        """解析 DBF 文件"""
        try:
            from dbfread import DBF
            dbf = DBF(str(self.file_path), encoding='gbk')
            
            records = []
            for record in dbf:
                records.append(record)
            
            self.df = pd.DataFrame(records)
            self._convert_to_orders()
            
        except ImportError:
            # 如果没有 dbfread，尝试用 pandas 读取
            self._parse_excel()
        except Exception as e:
            self.parse_errors.append(f"DBF 解析错误：{str(e)}")
    
    def _parse_excel(self):
        """解析 Excel 文件"""
        try:
            # 读取"详情"工作表
            self.df = pd.read_excel(
                self.file_path,
                sheet_name='详情',
                engine='openpyxl'
            )
            self._convert_to_orders()
            
        except Exception as e:
            self.parse_errors.append(f"Excel 解析错误：{str(e)}")
    
    def _parse_csv(self):
        """解析 CSV 文件"""
        try:
            self.df = pd.read_csv(
                self.file_path,
                encoding='gbk'
            )
            self._convert_to_orders()
            
        except Exception as e:
            self.parse_errors.append(f"CSV 解析错误：{str(e)}")
    
    def _convert_to_orders(self):
        """将 DataFrame 转换为 DBFOrder 对象列表"""
        if self.df is None or self.df.empty:
            return
        
        # 标准化列名（中文转英文）
        self.df = self._normalize_columns(self.df)
        
        # 转换为 DBFOrder 对象
        for idx, row in self.df.iterrows():
            try:
                order = DBFOrder(
                    order_type=str(row.get('order_type', '')),
                    price_type=str(row.get('price_type', '')),
                    mode_price=str(row.get('mode_price', '')) if pd.notna(row.get('mode_price')) else None,
                    stock_code=str(row.get('stock_code', '')),
                    volume=str(row.get('volume', '')),
                    account_id=str(row.get('account_id', '')),
                    act_type=str(row.get('act_type', '')) if pd.notna(row.get('act_type')) else None,
                    brokertype=str(row.get('brokertype', '')) if pd.notna(row.get('brokertype')) else None,
                    strategy=str(row.get('strategy', '')) if pd.notna(row.get('strategy')) else None,
                    note=str(row.get('note', '')) if pd.notna(row.get('note')) else None,
                    note1=str(row.get('note1', '')) if pd.notna(row.get('note1')) else None,
                    tradeparam=str(row.get('tradeparam', '')) if pd.notna(row.get('tradeparam')) else None,
                    command_id=str(row.get('command_id', '')) if pd.notna(row.get('command_id')) else None,
                    basketpath=str(row.get('basketpath', '')) if pd.notna(row.get('basketpath')) else None,
                    inserttime=str(row.get('inserttime', '')) if pd.notna(row.get('inserttime')) else None,
                    extraparam=str(row.get('extraparam', '')) if pd.notna(row.get('extraparam')) else None,
                    batch_id=str(row.get('batch_id', '')) if pd.notna(row.get('batch_id')) else None,
                )
                self.orders.append(order)
                
            except Exception as e:
                self.parse_errors.append(f"行{idx}转换错误：{str(e)}")
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化列名（中文转英文）
        
        Args:
            df: 原始 DataFrame
            
        Returns:
            列名标准化后的 DataFrame
        """
        # 创建列名映射（反向）
        reverse_mapping = {v: k for k, v in self.FIELD_MAPPING.items()}
        
        # 重命名列
        new_columns = {}
        for col in df.columns:
            col_clean = col.strip()
            if col_clean in reverse_mapping:
                new_columns[col_clean] = reverse_mapping[col_clean]
            else:
                # 尝试匹配部分列名
                matched = False
                for cn, en in reverse_mapping.items():
                    if cn in col_clean or col_clean in cn:
                        new_columns[col_clean] = en
                        matched = True
                        break
                if not matched:
                    # 保留原列名（去除空格）
                    new_columns[col_clean] = col_clean
        
        df = df.rename(columns=new_columns)
        return df
    
    def validate(self) -> bool:
        """
        验证订单数据
        
        Returns:
            是否全部验证通过
        """
        if not self.orders:
            return False
        
        valid = True
        for i, order in enumerate(self.orders):
            for field in self.REQUIRED_FIELDS:
                if not getattr(order, field):
                    self.parse_errors.append(f"订单{i+1}: 缺少必填字段 {field}")
                    valid = False
        
        return valid
    
    def get_summary(self) -> Dict:
        """
        获取解析摘要
        
        Returns:
            摘要信息字典
        """
        return {
            'file_path': str(self.file_path),
            'total_orders': len(self.orders),
            'parse_errors': len(self.parse_errors),
            'errors': self.parse_errors[:10],  # 只显示前 10 个错误
            'unique_stocks': len(set(o.stock_code for o in self.orders)),
            'unique_accounts': len(set(o.account_id for o in self.orders)),
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        转换为 DataFrame
        
        Returns:
            包含所有订单的 DataFrame
        """
        if not self.orders:
            return pd.DataFrame()
        
        return pd.DataFrame([o.to_dict() for o in self.orders])
