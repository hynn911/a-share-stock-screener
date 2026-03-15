"""
推荐回测与残差校准模块
跟踪推荐股票的实际表现，计算残差，优化评分权重
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import SessionLocal
from core.models import StockRecommendation, StockDaily, Stock
from sqlalchemy import desc, func
from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np
from scipy import stats


class RecommendationBacktester:
    """推荐回测器"""

    def __init__(self):
        self.db = SessionLocal()

    def get_recommendation_history(self, start_date: date = None, end_date: date = None) -> List[Dict]:
        """获取推荐历史数据"""
        query = self.db.query(
            StockRecommendation.trade_date,
            StockRecommendation.stock_code,
            StockRecommendation.stock_name,
            StockRecommendation.total_score,
            StockRecommendation.capital_score,
            StockRecommendation.technical_score,
            StockRecommendation.holder_score,
            StockRecommendation.news_score,
            StockRecommendation.momentum_score,
            StockRecommendation.rank
        )

        if start_date:
            query = query.filter(StockRecommendation.trade_date >= start_date)
        if end_date:
            query = query.filter(StockRecommendation.trade_date <= end_date)

        results = query.order_by(
            StockRecommendation.trade_date.desc(),
            StockRecommendation.rank
        ).all()

        return [
            {
                'trade_date': r.trade_date,
                'stock_code': r.stock_code,
                'stock_name': r.stock_name,
                'total_score': r.total_score,
                'capital_score': r.capital_score,
                'technical_score': r.technical_score,
                'holder_score': r.holder_score,
                'news_score': r.news_score,
                'momentum_score': r.momentum_score,
                'rank': r.rank
            }
            for r in results
        ]

    def calculate_forward_returns(
        self,
        recommendations: List[Dict],
        forward_days: int = 5
    ) -> pd.DataFrame:
        """
        计算推荐股票的前向收益率

        Args:
            recommendations: 推荐历史数据
            forward_days: 持有天数

        Returns:
            DataFrame 包含推荐日期、股票代码、评分、前向收益率
        """
        results = []

        for rec in recommendations:
            stock_code = rec['stock_code']
            rec_date = rec['trade_date']

            # 获取推荐日的收盘价
            entry_price = self._get_close_price(stock_code, rec_date)
            if not entry_price:
                continue

            # 获取 forward_days 天后的收盘价
            exit_date = rec_date + timedelta(days=forward_days + 2)  # 加 2 天缓冲（周末）
            exit_price = self._get_close_price(stock_code, exit_date, max_days_ago=forward_days + 5)

            if not exit_price or exit_price == 0:
                continue

            # 计算收益率
            forward_return = (exit_price - entry_price) / entry_price * 100

            results.append({
                'trade_date': rec_date,
                'stock_code': stock_code,
                'stock_name': rec['stock_name'],
                'total_score': rec['total_score'],
                'capital_score': rec['capital_score'],
                'technical_score': rec['technical_score'],
                'holder_score': rec['holder_score'],
                'news_score': rec['news_score'],
                'momentum_score': rec['momentum_score'],
                'rank': rec['rank'],
                f'return_{forward_days}d': forward_return,
                'entry_price': entry_price,
                'exit_price': exit_price
            })

        return pd.DataFrame(results)

    def _get_close_price(self, stock_code: str, target_date: date, max_days_ago: int = 10) -> Optional[float]:
        """获取指定日期的收盘价（如果无数据，向前查找最近的）"""
        query = self.db.query(StockDaily.close).filter(
            StockDaily.stock_code == stock_code,
            StockDaily.trade_date <= target_date
        ).order_by(desc(StockDaily.trade_date)).limit(1).first()

        if query:
            # 检查是否在合理范围内
            actual_date = self.db.query(
                func.max(StockDaily.trade_date)
            ).filter(
                StockDaily.stock_code == stock_code,
                StockDaily.trade_date <= target_date
            ).scalar()

            if actual_date and (target_date - actual_date).days <= max_days_ago:
                return query.close
        return None

    def calculate_ic(
        self,
        df: pd.DataFrame,
        score_col: str = 'total_score',
        return_col: str = 'return_5d'
    ) -> Dict:
        """
        计算 IC 值（Information Coefficient）- 评分与收益的相关性

        Returns:
            IC 值、p 值、样本数
        """
        if return_col not in df.columns or score_col not in df.columns:
            return {'ic': 0, 'p_value': 1, 'n': 0}

        # 去空值
        valid = df[[score_col, return_col]].dropna()
        if len(valid) < 10:
            return {'ic': 0, 'p_value': 1, 'n': len(valid)}

        # Pearson IC
        ic, p_value = stats.pearsonr(valid[score_col], valid[return_col])

        return {
            'ic': ic,
            'p_value': p_value,
            'n': len(valid),
            'ic_t_stat': ic / np.sqrt((1 - ic**2) / (len(valid) - 2)) if len(valid) > 2 else 0
        }

    def calculate_rank_ic(
        self,
        df: pd.DataFrame,
        score_col: str = 'total_score',
        return_col: str = 'return_5d'
    ) -> Dict:
        """计算 Rank IC - 排名相关性（更稳健）"""
        if return_col not in df.columns or score_col not in df.columns:
            return {'rank_ic': 0, 'p_value': 1, 'n': 0}

        valid = df[[score_col, return_col]].dropna()
        if len(valid) < 10:
            return {'rank_ic': 0, 'p_value': 1, 'n': len(valid)}

        # Spearman Rank IC
        rank_ic, p_value = stats.spearmanr(valid[score_col], valid[return_col])

        return {
            'rank_ic': rank_ic,
            'p_value': p_value,
            'n': len(valid)
        }

    def analyze_dimension_predictive_power(
        self,
        df: pd.DataFrame,
        return_col: str = 'return_5d'
    ) -> Dict[str, Dict]:
        """分析各维度分数的预测能力"""
        dimensions = ['capital_score', 'technical_score', 'holder_score', 'news_score', 'momentum_score']

        results = {}
        for dim in dimensions:
            ic_result = self.calculate_ic(df, dim, return_col)
            rank_ic_result = self.calculate_rank_ic(df, dim, return_col)

            results[dim] = {
                'ic': ic_result['ic'],
                'ic_p_value': ic_result['p_value'],
                'rank_ic': rank_ic_result['rank_ic'],
                'rank_ic_p_value': rank_ic_result['p_value'],
                'n_samples': ic_result['n']
            }

        return results

    def calculate_residuals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算残差 = 实际收益 - 预期收益
        预期收益基于总评分线性回归
        """
        if 'total_score' not in df.columns or 'return_5d' not in df.columns:
            return df

        # 保留必要的列用于后续合并
        valid = df[['trade_date', 'stock_code', 'total_score', 'return_5d']].dropna().copy()
        if len(valid) < 20:
            df['residual'] = np.nan
            df['predicted_return'] = np.nan
            return df

        # 简单线性回归
        from sklearn.linear_model import LinearRegression

        X = valid[['total_score']]
        y = valid['return_5d']

        model = LinearRegression()
        model.fit(X, y)

        # 预测收益
        valid['predicted_return'] = model.predict(X)
        # 残差
        valid['residual'] = y - valid['predicted_return']

        # 合并回原数据
        df = df.merge(
            valid[['trade_date', 'stock_code', 'predicted_return', 'residual']],
            on=['trade_date', 'stock_code'],
            how='left'
        )

        return df

    def get_backtest_summary(self, start_date: date = None, forward_days: int = 5) -> Dict:
        """获取回测汇总统计"""
        # 获取推荐历史
        history = self.get_recommendation_history(start_date=start_date)

        if not history:
            return {'error': 'No recommendation history found'}

        # 计算前向收益
        df = self.calculate_forward_returns(history, forward_days=forward_days)

        if len(df) < 10:
            return {'error': 'Insufficient data for backtest'}

        # 计算各维度 IC
        dimension_ic = self.analyze_dimension_predictive_power(df, f'return_{forward_days}d')

        # 计算总体 IC
        total_ic = self.calculate_ic(df, 'total_score', f'return_{forward_days}d')
        total_rank_ic = self.calculate_rank_ic(df, 'total_score', f'return_{forward_days}d')

        # 计算残差
        df = self.calculate_residuals(df)

        # 按分组统计
        top_n = df[df['rank'] <= 10]  # Top 10
        bottom_n = df[df['rank'] > df['rank'].max() - 10]  # Bottom 10

        summary = {
            'period': {
                'start': start_date.isoformat() if start_date else 'N/A',
                'end': date.today().isoformat(),
                'total_recommendations': len(df),
                'unique_stocks': df['stock_code'].nunique(),
                'unique_dates': df['trade_date'].nunique()
            },
            'predictive_power': {
                'total_score': {
                    'ic': total_ic['ic'],
                    'ic_p_value': total_ic['p_value'],
                    'rank_ic': total_rank_ic['rank_ic'],
                    'rank_ic_p_value': total_rank_ic['p_value']
                },
                'dimensions': dimension_ic
            },
            'returns': {
                'avg_forward_return': df[f'return_{forward_days}d'].mean(),
                'top_10_avg_return': top_n[f'return_{forward_days}d'].mean() if len(top_n) > 0 else None,
                'bottom_10_avg_return': bottom_n[f'return_{forward_days}d'].mean() if len(bottom_n) > 0 else None,
                'win_rate': (df[f'return_{forward_days}d'] > 0).mean() * 100
            },
            'residual_stats': {
                'mean_residual': df['residual'].mean() if 'residual' in df.columns else None,
                'std_residual': df['residual'].std() if 'residual' in df.columns else None,
                'skew': df['residual'].skew() if 'residual' in df.columns else None
            }
        }

        return summary

    def close(self):
        self.db.close()


if __name__ == "__main__":
    # 测试
    backtester = RecommendationBacktester()

    # 获取最近 30 天的回测统计
    start = date.today() - timedelta(days=30)
    summary = backtester.get_backtest_summary(start_date=start, forward_days=5)

    import json
    print(json.dumps(summary, indent=2, default=str))

    backtester.close()
