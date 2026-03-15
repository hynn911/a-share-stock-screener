"""
趋势感知权重优化器
基于时间序列分析各维度预测能力的变化趋势
结合新闻热点自动调整权重
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import SessionLocal
from core.models import StockRecommendation, StockDaily
from datetime import date, timedelta
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression, Ridge
import warnings
warnings.filterwarnings('ignore')


class TrendAwareWeightOptimizer:
    """趋势感知权重优化器"""

    def __init__(self):
        self.db = SessionLocal()
        self.dimensions = ['capital_score', 'technical_score', 'holder_score', 'news_score', 'momentum_score']

    def get_historical_returns(self, start_date: date = None, lookback_days: int = 90) -> pd.DataFrame:
        """获取历史推荐及实际收益数据"""
        if start_date is None:
            start_date = date.today() - timedelta(days=lookback_days)

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
        ).filter(
            StockRecommendation.trade_date >= start_date
        ).order_by(StockRecommendation.trade_date.desc())

        results = query.all()
        df = pd.DataFrame([{
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
        } for r in results])

        return df

    def calculate_forward_returns(self, df: pd.DataFrame, forward_days: int = 5) -> pd.DataFrame:
        """计算前向收益率"""
        results = []

        for idx, row in df.iterrows():
            stock_code = row['stock_code']
            rec_date = row['trade_date']

            # 获取推荐日的收盘价
            entry_query = self.db.query(StockDaily.close).filter(
                StockDaily.stock_code == stock_code,
                StockDaily.trade_date <= rec_date
            ).order_by(StockDaily.trade_date.desc()).first()

            if not entry_query:
                continue

            entry_price = entry_query[0]

            # 获取 forward_days 天后的收盘价
            exit_date = rec_date + timedelta(days=forward_days + 2)
            exit_query = self.db.query(StockDaily.close).filter(
                StockDaily.stock_code == stock_code,
                StockDaily.trade_date <= exit_date
            ).order_by(StockDaily.trade_date.desc()).first()

            if not exit_query or exit_query[0] == 0:
                continue

            exit_price = exit_query[0]
            forward_return = (exit_price - entry_price) / entry_price * 100

            results.append({
                'trade_date': rec_date,
                'stock_code': stock_code,
                f'return_{forward_days}d': forward_return
            })

        returns_df = pd.DataFrame(results)
        if len(returns_df) > 0:
            df = df.merge(returns_df, on=['trade_date', 'stock_code'], how='left')

        return df

    def calculate_rolling_ic(self, df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
        """计算滚动 IC 值（时间序列）"""
        df = df.sort_values('trade_date').copy()
        unique_dates = df['trade_date'].unique()

        rolling_ic = {dim: [] for dim in self.dimensions}
        dates = []

        for i in range(window, len(unique_dates)):
            window_dates = unique_dates[i-window:i]
            window_df = df[df['trade_date'].isin(window_dates)]

            current_date = unique_dates[i]
            dates.append(current_date)

            for dim in self.dimensions:
                valid = window_df[[dim, f'return_5d']].dropna()
                if len(valid) >= 10:
                    ic, p_value = stats.spearmanr(valid[dim], valid[f'return_5d'])
                    rolling_ic[dim].append(ic if not np.isnan(ic) else 0)
                else:
                    rolling_ic[dim].append(0)

        return pd.DataFrame({
            'trade_date': dates,
            **{f'{dim}_ic': rolling_ic[dim] for dim in self.dimensions}
        })

    def detect_trend(self, ic_series: pd.Series) -> Dict:
        """检测 IC 趋势"""
        if len(ic_series) < 5:
            return {'trend': 'insufficient_data', 'slope': 0, 'strength': 0}

        # 线性回归拟合趋势
        X = np.arange(len(ic_series)).reshape(-1, 1)
        y = ic_series.values

        model = LinearRegression()
        model.fit(X, y)

        slope = model.coef_[0]
        r_squared = model.score(X, y)

        # 趋势强度（斜率 * 拟合度）
        trend_strength = slope * r_squared

        # 趋势方向
        if abs(slope) < 0.001:
            trend = 'stable'
        elif slope > 0:
            trend = 'improving'
        else:
            trend = 'declining'

        return {
            'trend': trend,
            'slope': slope,
            'r_squared': r_squared,
            'strength': trend_strength,
            'current_ic': ic_series.iloc[-1] if len(ic_series) > 0 else 0,
            'avg_ic': ic_series.mean()
        }

    def analyze_dimension_trends(self, df: pd.DataFrame, window: int = 10) -> Dict[str, Dict]:
        """分析各维度趋势"""
        rolling_ic = self.calculate_rolling_ic(df, window)

        trend_analysis = {}
        for dim in self.dimensions:
            ic_col = f'{dim}_ic'
            if ic_col in rolling_ic.columns:
                trend_info = self.detect_trend(rolling_ic[ic_col])
                trend_analysis[dim] = trend_info

        return trend_analysis

    def optimize_weights_with_trend(
        self,
        df: pd.DataFrame,
        lookback_days: int = 60,
        trend_weight: float = 0.3,
        min_weight: float = 0.05,
        max_weight: float = 0.40
    ) -> Dict[str, float]:
        """
        基于趋势优化权重

        Args:
            df: 历史数据
            lookback_days: 回看天数
            trend_weight: 趋势因子权重 (0-1)，越大越重视趋势
            min_weight: 最小权重
            max_weight: 最大权重

        Returns:
            优化后的权重
        """
        # 计算当前 IC（最近 30 天）
        recent_df = df[df['trade_date'] >= df['trade_date'].max() - timedelta(days=30)]

        current_ic = {}
        for dim in self.dimensions:
            valid = recent_df[[dim, 'return_5d']].dropna()
            if len(valid) >= 10:
                ic, _ = stats.spearmanr(valid[dim], valid['return_5d'])
                current_ic[dim] = ic if not np.isnan(ic) else 0
            else:
                current_ic[dim] = 0

        # 分析趋势
        trend_analysis = self.analyze_dimension_trends(df)

        # 计算综合得分 = 当前 IC + 趋势调整
        scores = {}
        for dim in self.dimensions:
            base_score = abs(current_ic.get(dim, 0))

            trend = trend_analysis.get(dim, {})
            trend_adjustment = trend.get('strength', 0) * trend_weight

            # 趋势加分：改善的趋势额外加分
            if trend.get('trend') == 'improving':
                trend_adjustment += 0.05
            elif trend.get('trend') == 'declining':
                trend_adjustment -= 0.05

            scores[dim] = max(0, base_score + trend_adjustment)

        # 归一化为权重
        total = sum(scores.values())
        if total == 0:
            # 平均权重
            return {dim.replace('_score', ''): 0.20 for dim in self.dimensions}

        weights = {}
        for dim, score in scores.items():
            weight = score / total
            # 应用边界约束
            weight = max(min_weight, min(max_weight, weight))
            weights[dim.replace('_score', '')] = weight

        # 重新归一化确保总和为 1
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}

        return weights

    def get_news_sentiment_factor(self, stock_codes: List[str]) -> pd.DataFrame:
        """获取新闻情绪因子（用于结合新闻热点）"""
        # 这是一个扩展点，可以接入新闻 API
        # 目前返回一个占位符
        return pd.DataFrame({
            'stock_code': stock_codes,
            'news_sentiment': 0.5,  # 中性
            'news_hotness': 0.5  # 热度中等
        })

    def apply_news_adjustment(
        self,
        weights: Dict[str, float],
        news_factor: float = 0.1
    ) -> Dict[str, float]:
        """
        根据新闻热点调整权重

        Args:
            weights: 基础权重
            news_factor: 新闻调整因子 (0-0.3)，0 表示不调整

        Returns:
            调整后的权重
        """
        # 如果新闻情绪积极，增加 news_score 权重
        # 如果新闻情绪消极，降低 news_score 权重
        adjusted = weights.copy()

        # 简单的线性调整
        news_delta = news_factor * 0.1  # 最多调整 1%
        adjusted['news'] = min(0.40, max(0.05, adjusted.get('news', 0.15) + news_delta))

        # 重新归一化
        total = sum(adjusted.values())
        adjusted = {k: v / total for k, v in adjusted.items()}

        return adjusted

    def print_trend_report(self, df: pd.DataFrame):
        """打印趋势分析报告"""
        print("=" * 70)
        print("维度趋势分析报告")
        print("=" * 70)

        trend_analysis = self.analyze_dimension_trends(df)

        print(f"\n{'维度':<15} {'当前 IC':<10} {'平均 IC':<10} {'趋势':<12} {'斜率':<10} {'强度':<10}")
        print("-" * 70)

        for dim, info in trend_analysis.items():
            dim_name = dim.replace('_score', '').upper()
            current_ic = info.get('current_ic', 0)
            avg_ic = info.get('avg_ic', 0)
            trend = info.get('trend', 'N/A')
            slope = info.get('slope', 0)
            strength = info.get('strength', 0)

            # 趋势符号
            if trend == 'improving':
                trend_str = "↑ 改善"
            elif trend == 'declining':
                trend_str = "↓ 下降"
            else:
                trend_str = "→ 稳定"

            print(f"{dim_name:<15} {current_ic:>8.4f}   {avg_ic:>8.4f}   {trend_str:<12} {slope:>8.6f}   {strength:>8.6f}")

        print("\n趋势说明:")
        print("  - 斜率 > 0: 预测能力随时间增强")
        print("  - 斜率 < 0: 预测能力随时间减弱")
        print("  - 强度 = 斜率 x R 平方，综合考虑趋势方向和拟合度")

        print("=" * 70)

    def close(self):
        self.db.close()


if __name__ == "__main__":
    optimizer = TrendAwareWeightOptimizer()

    print("获取历史数据...")
    df = optimizer.get_historical_returns(lookback_days=90)

    if len(df) < 50:
        print("数据不足，需要至少 50 条记录")
    else:
        print(f"加载了 {len(df)} 条记录")

        print("\n计算前向收益...")
        df = optimizer.calculate_forward_returns(df, forward_days=5)

        valid = df.dropna(subset=['return_5d'])
        print(f"有效记录：{len(valid)} 条")

        if len(valid) >= 50:
            # 打印趋势报告
            optimizer.print_trend_report(valid)

            # 优化权重
            print("\n优化权重...")
            weights = optimizer.optimize_weights_with_trend(valid, lookback_days=60, trend_weight=0.3)

            print("\n优化后的权重:")
            print(f"{'维度':<15} {'权重':<10}")
            print("-" * 30)
            for dim, weight in weights.items():
                print(f"{dim.upper():<15} {weight:>8.1%}")

            print(f"\n总计：{sum(weights.values()):.1%}")

    optimizer.close()
