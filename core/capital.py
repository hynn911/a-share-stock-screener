"""
资金分析模块
"""
import pandas as pd
from core.database import SessionLocal
from core.models import StockCapitalFlow, Stock
from sqlalchemy import and_, func


class CapitalAnalyzer:
    """资金分析器"""

    def __init__(self):
        self.db = SessionLocal()

    def get_stock_name(self, stock_code: str) -> str:
        """获取股票名称"""
        stock = self.db.query(Stock).filter(Stock.code == stock_code).first()
        return stock.name if stock else ""

    def get_consecutive_inflow(self, stock_code: str, days: int = 3) -> list:
        """获取连续 N 日资金净流入的股票"""
        # 获取最近 N 天的资金流数据
        flows = self.db.query(StockCapitalFlow).filter(
            StockCapitalFlow.stock_code == stock_code
        ).order_by(StockCapitalFlow.trade_date.desc()).limit(days + 2).all()

        if len(flows) < days:
            return []

        # 检查是否连续净流入
        consecutive = 0
        total_inflow = 0
        for flow in flows:
            if flow.net_inflow > 0:
                consecutive += 1
                total_inflow += flow.net_inflow
            else:
                break

        if consecutive >= days:
            return [{
                'stock_code': stock_code,
                'stock_name': self.get_stock_name(stock_code),
                'consecutive_days': consecutive,
                'total_net_inflow': total_inflow
            }]

        return []

    def get_all_consecutive_inflow(self, min_days: int = 3, min_amount: float = 10000000) -> list:
        """筛选所有连续流入的股票"""
        # 获取所有股票
        stocks = self.db.query(StockCapitalFlow.stock_code).distinct().all()

        results = []
        for (stock_code,) in stocks:
            inflow_data = self.get_consecutive_inflow(stock_code, min_days)
            if inflow_data and inflow_data[0]['total_net_inflow'] >= min_amount:
                results.append(inflow_data[0])

        # 按净流入排序
        results.sort(key=lambda x: x['total_net_inflow'], reverse=True)

        return results

    def get_capital_trend(self, stock_code: str, days: int = 10) -> dict:
        """获取个股资金趋势"""
        flows = self.db.query(StockCapitalFlow).filter(
            StockCapitalFlow.stock_code == stock_code
        ).order_by(StockCapitalFlow.trade_date.desc()).limit(days).all()

        if not flows:
            return {}

        total_inflow = sum(f.main_force_in for f in flows)
        total_outflow = sum(f.main_force_out for f in flows)
        net_inflow = sum(f.net_inflow for f in flows)
        positive_days = sum(1 for f in flows if f.net_inflow > 0)

        return {
            'stock_code': stock_code,
            'stock_name': self.get_stock_name(stock_code),
            'total_main_force_in': total_inflow,
            'total_main_force_out': total_outflow,
            'net_inflow': net_inflow,
            'positive_days': positive_days,
            'negative_days': days - positive_days
        }

    def close(self):
        self.db.close()
