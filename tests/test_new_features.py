"""
新功能集成测试 - 趋势感知优化与热点看板
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.trend_optimizer import TrendAwareWeightOptimizer
from core.hot_words import HotWordAnalyzer
from core.weight_optimizer import AdaptiveWeightOptimizer
import pandas as pd
import numpy as np


def test_trend_aware_optimization():
    """测试趋势感知权重优化功能"""
    print("=" * 60)
    print("测试：趋势感知权重优化")
    print("=" * 60)

    optimizer = TrendAwareWeightOptimizer()

    try:
        # 获取历史数据
        history_df = optimizer.get_historical_returns(lookback_days=90)
        history_df = optimizer.calculate_forward_returns(history_df, forward_days=5)
        valid_df = history_df.dropna(subset=['return_5d'])

        print(f"有效数据：{len(valid_df)} 条")

        if len(valid_df) < 50:
            print("WARN: 数据不足，跳过测试")
            return False

        # 测试趋势检测
        print("\n【趋势检测】")
        test_scores = pd.Series(np.random.randn(30))
        trend = optimizer.detect_trend(test_scores)
        print(f"  斜率：{trend.get('slope', 0):.6f}")
        print(f"  R 平方：{trend.get('r_squared', 0):.4f}")
        print(f"  趋势强度：{trend.get('strength', 0):.6f}")
        print(f"  趋势方向：{trend.get('trend', 'unknown')}")

        # 测试权重优化
        print("\n【权重优化】")
        weights = optimizer.optimize_weights_with_trend(
            valid_df,
            lookback_days=60,
            trend_weight=0.3,
            min_weight=0.05,
            max_weight=0.40
        )

        print("优化后权重:")
        for dim, w in weights.items():
            print(f"  {dim}: {w:.1%}")

        # 验证权重和为 1
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01, f"权重和不为 1: {total}"
        print(f"\n[PASS] 权重和验证通过：{total:.4f}")

        # 打印趋势报告
        print("\n【趋势分析报告】")
        optimizer.print_trend_report(valid_df)

        optimizer.close()
        print("\n[PASS] 趋势感知优化测试通过")
        return True

    except Exception as e:
        print(f"\nX 测试失败：{e}")
        optimizer.close()
        return False


def test_hot_sector_dashboard():
    """测试热点看板功能"""
    print("\n" + "=" * 60)
    print("测试：热点看板功能")
    print("=" * 60)

    analyzer = HotWordAnalyzer()

    try:
        # 测试热词获取
        print("\n【热词获取】")
        hot_words = analyzer.get_hot_words(days=3, top_n=20)
        print(f"获取到 {len(hot_words)} 个热词")
        if hot_words:
            print(f"Top 5 热词:")
            for hw in hot_words[:5]:
                print(f"  - {hw['word']}: {hw['hot_score']}")

        # 测试热门板块
        print("\n【热门板块】")
        hot_sectors = analyzer.get_hot_sectors(days=3, top_n=10)
        print(f"获取到 {len(hot_sectors)} 个热门板块")
        for i, sector in enumerate(hot_sectors[:5], 1):
            print(f"  {i}. {sector['sector']}: {sector['hot_score']} (关键词：{len(sector['top_words'])}个)")

        # 测试板块相关股票
        print("\n【板块相关股票】")
        test_sectors = ['芯片半导体', '有色金属', '新能源', '医药生物', '金融']
        for sector in test_sectors:
            stocks = analyzer.get_sector_stocks(sector, limit=5)
            if stocks:
                print(f"  [OK] {sector}: {len(stocks)} 只相关股票")
                for s in stocks[:2]:
                    print(f"    - {s['stock_code']} {s['stock_name']}")
            else:
                print(f"  [WARN] {sector}: 未找到相关股票")

        # 测试全量板块
        print("\n【全量板块与股票】")
        all_sectors = analyzer.get_all_sectors_with_stocks(days=3, top_n=5)
        for sector_info in all_sectors:
            print(f"  {sector_info['sector']}: {sector_info['stock_count']} 只股票")

        analyzer.close()
        print("\n[PASS] 热点看板测试通过")
        return True

    except Exception as e:
        print(f"\n[FAIL] 测试失败：{e}")
        import traceback
        traceback.print_exc()
        analyzer.close()
        return False


def test_weight_optimizer_integration():
    """测试权重优化器集成"""
    print("\n" + "=" * 60)
    print("测试：权重优化器集成")
    print("=" * 60)

    optimizer = AdaptiveWeightOptimizer()

    try:
        # 测试默认权重
        print("\n【默认权重】")
        default = optimizer.default_weights
        print("默认权重配置:")
        for dim, w in default.items():
            print(f"  {dim}: {w:.1%}")

        # 验证权重和为 1
        total = sum(default.values())
        assert abs(total - 1.0) < 0.01, f"权重和不为 1: {total}"
        print(f"[PASS] 权重和验证通过：{total:.4f}")

        optimizer.close()
        print("\n[PASS] 权重优化器集成测试通过")
        return True

    except Exception as e:
        print(f"\nX 测试失败：{e}")
        optimizer.close()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("新功能集成测试套件")
    print("=" * 60)

    results = {
        '趋势感知优化': test_trend_aware_optimization(),
        '热点看板': test_hot_sector_dashboard(),
        '权重优化器集成': test_weight_optimizer_integration()
    }

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "V 通过" if passed else "X 失败"
        print(f"  {test_name}: {status}")

    total_passed = sum(results.values())
    total_tests = len(results)
    print(f"\n总计：{total_passed}/{total_tests} 测试通过")

    return total_passed == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
