"""
股东户数分析
"""
from core.database import SessionLocal
from core.models import StockHolderCount, Stock
from sqlalchemy import desc
from typing import List, Dict, Optional
import pandas as pd


class ShareholderAnalyzer:
    """股东户数分析器"""

    def __init__(self):
        self.db = SessionLocal()

    def get_stock_name(self, stock_code: str) -> str:
        """获取股票名称"""
        stock = self.db.query(Stock).filter(Stock.code == stock_code).first()
        return stock.name if stock else ""

    def get_holder_count_trend(self, stock_code: str, limit: int = 10) -> List[Dict]:
        """获取股东户数变化趋势"""
        data = self.db.query(StockHolderCount).filter(
            StockHolderCount.stock_code == stock_code
        ).order_by(
            desc(StockHolderCount.trade_date)
        ).limit(limit).all()

        if not data:
            return []

        return [{
            'trade_date': d.trade_date,
            'holder_count': d.holder_count,
            'change_count': d.change_count,
            'change_ratio': d.change_ratio,
            'avg_holdings': d.avg_holdings,
            'avg_holdings_change': d.avg_holdings_change
        } for d in data]

    def get_consecutive_decrease(self, stock_code: str, min_days: int = 3) -> Optional[Dict]:
        """获取连续股东户数减少（筹码集中）"""
        data = self.db.query(StockHolderCount).filter(
            StockHolderCount.stock_code == stock_code
        ).order_by(
            desc(StockHolderCount.trade_date)
        ).limit(10).all()

        if not data or len(data) < min_days:
            return None

        # 检查连续减少
        consecutive_days = 0
        total_change_ratio = 0

        for i in range(len(data) - 1):
            if data[i].change_count < 0:  # 股东户数减少
                consecutive_days += 1
                total_change_ratio += data[i].change_ratio
            else:
                break

        if consecutive_days >= min_days:
            return {
                'stock_code': stock_code,
                'stock_name': self.get_stock_name(stock_code),
                'consecutive_days': consecutive_days,
                'total_change_ratio': total_change_ratio,
                'latest_holder_count': data[0].holder_count,
                'latest_change_ratio': data[0].change_ratio,
                'latest_trade_date': data[0].trade_date
            }

        return None

    def get_all_consecutive_concentrated(self, min_days: int = 3, min_change_ratio: float = -5.0) -> List[Dict]:
        """获取所有连续筹码集中的股票"""
        # 获取所有股票代码
        stocks = self.db.query(StockHolderCount.stock_code).distinct().all()

        results = []
        for (stock_code,) in stocks:
            result = self.get_consecutive_decrease(stock_code, min_days)
            if result and result['total_change_ratio'] < min_change_ratio:
                results.append(result)

        # 按总变化比例排序（越负越集中）
        results.sort(key=lambda x: x['total_change_ratio'])

        return results

    def get_holder_count_summary(self, stock_code: str) -> Optional[Dict]:
        """获取股东户数汇总信息"""
        latest = self.db.query(StockHolderCount).filter(
            StockHolderCount.stock_code == stock_code
        ).order_by(
            desc(StockHolderCount.trade_date)
        ).first()

        if not latest:
            return None

        # 计算趋势（与上期比）
        prev = self.db.query(StockHolderCount).filter(
            StockHolderCount.stock_code == stock_code,
            StockHolderCount.trade_date < latest.trade_date
        ).order_by(
            desc(StockHolderCount.trade_date)
        ).first()

        trend = "stable"
        if latest.change_count < 0:
            trend = "concentrated"  # 筹码集中
        elif latest.change_count > 0:
            trend = "dispersed"  # 筹码分散

        return {
            'stock_code': stock_code,
            'stock_name': self.get_stock_name(stock_code),
            'trade_date': latest.trade_date,
            'holder_count': latest.holder_count,
            'change_count': latest.change_count,
            'change_ratio': latest.change_ratio,
            'avg_holdings': latest.avg_holdings,
            'trend': trend,
            'prev_holder_count': prev.holder_count if prev else None
        }

    def close(self):
        self.db.close()
