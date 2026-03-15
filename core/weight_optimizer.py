"""
自适应权重优化器
基于历史回测的 IC 值和残差分析，动态调整各维度权重
支持趋势感知和新闻热点结合
"""
from core.backtester import RecommendationBacktester
from core.trend_optimizer import TrendAwareWeightOptimizer
from datetime import date, timedelta
from typing import Dict, List, Optional
import numpy as np
from scipy.optimize import minimize


class AdaptiveWeightOptimizer:
    """自适应权重优化器"""

    def __init__(self):
        self.backtester = RecommendationBacktester()
        self.trend_optimizer = TrendAwareWeightOptimizer()

        # 默认权重
        self.default_weights = {
            'capital': 0.25,
            'technical': 0.25,
            'holder': 0.20,
            'news': 0.15,
            'momentum': 0.15
        }

    def optimize_weights(
        self,
        lookback_days: int = 60,
        forward_days: int = 5,
        method: str = 'ic_rank',
        use_trend: bool = True
    ) -> Dict[str, float]:
        """
        优化权重

        Args:
            lookback_days: 回看天数
            forward_days: 前向收益天数
            method: 优化方法
                - 'ic_rank': 基于 Rank IC 最大化
                - 'sharpe': 基于夏普比率最大化
                - 'win_rate': 基于胜率最大化
                - 'trend_aware': 趋势感知优化（新）
            use_trend: 是否启用趋势调整（仅对 ic_rank/sharpe/win_rate 有效）

        Returns:
            优化后的权重字典
        """
        # 获取回测数据
        start_date = date.today() - timedelta(days=lookback_days)
        history = self.backtester.get_recommendation_history(start_date=start_date)

        if len(history) < 50:
            print(f"数据不足（{len(history)}条），使用默认权重")
            return self.default_weights.copy()

        # 计算前向收益
        df = self.backtester.calculate_forward_returns(history, forward_days=forward_days)

        if len(df) < 30:
            print(f"有效数据不足（{len(df)}条），使用默认权重")
            return self.default_weights.copy()

        # 优化
        if method == 'trend_aware' or (use_trend and method == 'ic_rank'):
            # 使用趋势感知优化
            weights = self._optimize_with_trend(df)
        elif method == 'ic_rank':
            weights = self._optimize_for_ic(df)
        elif method == 'sharpe':
            weights = self._optimize_for_sharpe(df)
        elif method == 'win_rate':
            weights = self._optimize_for_win_rate(df)
        else:
            weights = self.default_weights.copy()

        return weights

    def _optimize_with_trend(self, df) -> Dict[str, float]:
        """基于趋势感知优化权重"""
        weights = self.trend_optimizer.optimize_weights_with_trend(
            df,
            lookback_days=60,
            trend_weight=0.3,
            min_weight=0.05,
            max_weight=0.40
        )

        print("使用趋势感知优化:")
        for dim, weight in weights.items():
            print(f"  {dim}: {weight:.1%}")

        return weights

    def _optimize_for_ic(self, df) -> Dict[str, float]:
        """基于 Rank IC 最大化优化权重"""
        dimensions = ['capital_score', 'technical_score', 'holder_score', 'news_score', 'momentum_score']
        dim_names = ['capital', 'technical', 'holder', 'news', 'momentum']

        def objective(weights_array):
            # 计算加权总分
            weighted_score = np.zeros(len(df))
            for i, dim in enumerate(dimensions):
                if dim in df.columns:
                    weighted_score += weights_array[i] * df[dim].fillna(0)

            # 计算 Rank IC
            from scipy import stats
            if len(weighted_score) > 10:
                rank_ic, _ = stats.spearmanr(weighted_score, df['return_5d'].fillna(0))
                return -rank_ic  # 最小化负 IC = 最大化 IC
            return 0

        # 约束：权重和为 1
        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1})
        # 边界：每个权重 0-0.5
        bounds = [(0, 0.5) for _ in range(5)]
        # 初始值
        x0 = np.array([self.default_weights[d] for d in dim_names])

        result = minimize(
            objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        if result.success:
            optimized = {dim_names[i]: float(result.x[i]) for i in range(5)}
            print(f"优化后 Rank IC: {-result.fun:.4f}")
            return optimized
        else:
            print("优化失败，使用默认权重")
            return self.default_weights.copy()

    def _optimize_for_sharpe(self, df) -> Dict[str, float]:
        """基于夏普比率最大化优化权重"""
        dimensions = ['capital_score', 'technical_score', 'holder_score', 'news_score', 'momentum_score']
        dim_names = ['capital', 'technical', 'holder', 'news', 'momentum']

        def objective(weights_array):
            # 计算加权总分
            weighted_score = np.zeros(len(df))
            for i, dim in enumerate(dimensions):
                if dim in df.columns:
                    weighted_score += weights_array[i] * df[dim].fillna(0)

            # 按评分分组，模拟投资策略
            df_copy = df.copy()
            df_copy['weighted_score'] = weighted_score
            df_copy['quantile'] = pd.qcut(weighted_score, q=5, labels=False, duplicates='drop')

            # 计算各组平均收益
            quantile_returns = df_copy.groupby('quantile')['return_5d'].mean()

            # 多空组合：做多 Top 组，做空 Bottom 组
            if len(quantile_returns) >= 2:
                long_short_return = quantile_returns.max() - quantile_returns.min()
                long_short_std = df_copy['return_5d'].std()

                if long_short_std > 0:
                    sharpe = long_short_return / long_short_std * np.sqrt(252 / 5)  # 年化
                    return -sharpe
            return 0

        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1})
        bounds = [(0, 0.5) for _ in range(5)]
        x0 = np.array([self.default_weights[d] for d in dim_names])

        result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)

        if result.success:
            optimized = {dim_names[i]: float(result.x[i]) for i in range(5)}
            print(f"优化后夏普比率：{-result.fun:.4f}")
            return optimized
        else:
            return self.default_weights.copy()

    def _optimize_for_win_rate(self, df) -> Dict[str, float]:
        """基于胜率最大化优化权重"""
        import pandas as pd
        dimensions = ['capital_score', 'technical_score', 'holder_score', 'news_score', 'momentum_score']
        dim_names = ['capital', 'technical', 'holder', 'news', 'momentum']

        def objective(weights_array):
            weighted_score = np.zeros(len(df))
            for i, dim in enumerate(dimensions):
                if dim in df.columns:
                    weighted_score += weights_array[i] * df[dim].fillna(0)

            df_copy = df.copy()
            df_copy['weighted_score'] = weighted_score
            df_copy['quantile'] = pd.qcut(weighted_score, q=5, labels=False, duplicates='drop')

            # Top 组胜率
            top_quantile = df_copy[df_copy['quantile'] == df_copy['quantile'].max()]
            win_rate = (top_quantile['return_5d'] > 0).mean() if len(top_quantile) > 0 else 0

            return -win_rate

        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1})
        bounds = [(0, 0.5) for _ in range(5)]
        x0 = np.array([self.default_weights[d] for d in dim_names])

        result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)

        if result.success:
            optimized = {dim_names[i]: float(result.x[i]) for i in range(5)}
            print(f"优化后 Top 组胜率：{-result.fun:.2%}")
            return optimized
        else:
            return self.default_weights.copy()

    def get_dimension_analysis(self, lookback_days: int = 60) -> Dict:
        """获取各维度分析结果"""
        start_date = date.today() - timedelta(days=lookback_days)
        history = self.backtester.get_recommendation_history(start_date=start_date)

        if len(history) < 30:
            return {'error': '数据不足'}

        df = self.backtester.calculate_forward_returns(history, forward_days=5)

        analysis = self.backtester.analyze_dimension_predictive_power(df)

        # 添加当前权重对比
        for dim_key in analysis:
            dim_name = dim_key.replace('_score', '')
            analysis[dim_key]['current_weight'] = self.default_weights.get(dim_name, 0)

        return analysis

    def close(self):
        self.backtester.close()


# 需要导入 pandas
import pandas as pd


if __name__ == "__main__":
    optimizer = AdaptiveWeightOptimizer()

    # 获取维度分析
    print("=== 各维度预测能力分析 ===")
    analysis = optimizer.get_dimension_analysis(lookback_days=60)
    for dim, metrics in analysis.items():
        print(f"\n{dim}:")
        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.4f}")
            else:
                print(f"  {key}: {value}")

    # 优化权重
    print("\n=== 权重优化 ===")
    optimized = optimizer.optimize_weights(lookback_days=60, method='ic_rank')
    print("优化后权重:")
    for k, v in optimized.items():
        print(f"  {k}: {v:.2%}")

    optimizer.close()
