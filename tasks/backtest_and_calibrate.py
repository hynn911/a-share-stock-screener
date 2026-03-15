"""
回测与权重校准任务
分析历史推荐表现，优化评分权重
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.stock_scorer import StockScorer
from datetime import date, timedelta
import json


def run_backtest_analysis():
    """运行回测分析"""
    scorer = StockScorer()

    print("=" * 60)
    print("智能荐股回测与权重校准系统")
    print("=" * 60)

    # 1. 回测统计
    print("\n【1. 回测统计】")
    start_date = date.today() - timedelta(days=60)
    summary = scorer.get_backtest_summary(start_date=start_date, forward_days=5)

    if 'error' in summary:
        print(f"错误：{summary['error']}")
    else:
        print(f"\n回测期间：{summary['period']['start']} 至 {summary['period']['end']}")
        print(f"推荐记录：{summary['period']['total_recommendations']} 条")
        print(f"_unique_stocks：{summary['period']['unique_stocks']} 只")

        print(f"\n【预测能力】")
        total = summary['predictive_power']['total_score']
        print(f"  总评分 IC: {total['ic']:.4f} (p={total['ic_p_value']:.4f})")
        print(f"  总评分 Rank IC: {total['rank_ic']:.4f} (p={total['rank_ic_p_value']:.4f})")

        print(f"\n【收益表现】")
        print(f"  平均前向收益：{summary['returns']['avg_forward_return']:.2f}%")
        print(f"  Top 10 平均收益：{summary['returns']['top_10_avg_return']:.2f}%" if summary['returns']['top_10_avg_return'] else "  Top 10 平均收益：N/A")
        print(f"  胜率：{summary['returns']['win_rate']:.1f}%")

        if summary['residual_stats']['mean_residual']:
            print(f"\n【残差统计】")
            print(f"  平均残差：{summary['residual_stats']['mean_residual']:.4f}")
            print(f"  残差标准差：{summary['residual_stats']['std_residual']:.4f}")
            print(f"  偏度：{summary['residual_stats']['skew']:.4f}")

    # 2. 各维度预测能力
    print("\n【2. 各维度预测能力分析】")
    analysis = scorer.get_dimension_analysis(lookback_days=60)

    if 'error' in analysis:
        print(f"错误：{analysis['error']}")
    else:
        print(f"{'维度':<15} {'IC':<10} {'p 值':<10} {'Rank IC':<10} {'p 值':<10}")
        print("-" * 55)
        for dim, metrics in analysis.items():
            dim_name = dim.replace('_score', '').upper()
            ic = metrics.get('ic', 0)
            ic_p = metrics.get('ic_p_value', 1)
            rank_ic = metrics.get('rank_ic', 0)
            rank_ic_p = metrics.get('rank_ic_p_value', 1)
            flag = "**" if ic_p < 0.05 else ("*" if ic_p < 0.1 else "")
            print(f"{dim_name:<15} {ic:>8.4f}{flag:<2} {ic_p:>8.4f}   {rank_ic:>8.4f}{flag:<2} {rank_ic_p:>8.4f}")

    # 2.5 趋势分析
    print("\n【2.5 维度趋势分析】")
    print("  正在分析各维度预测能力变化趋势...")

    from core.trend_optimizer import TrendAwareWeightOptimizer
    trend_opt = TrendAwareWeightOptimizer()

    try:
        history_df = trend_opt.get_historical_returns(lookback_days=90)
        history_df = trend_opt.calculate_forward_returns(history_df, forward_days=5)
        valid_df = history_df.dropna(subset=['return_5d'])

        if len(valid_df) >= 50:
            trend_opt.print_trend_report(valid_df)
        else:
            print("  数据不足，跳过趋势分析")
    except Exception as e:
        print(f"  趋势分析失败：{e}")
    finally:
        trend_opt.close()

    # 3. 权重优化
    print("\n【3. 权重优化】")
    print("请选择优化目标：")
    print("  1. IC 最大化（推荐）- 提高评分与收益的相关性")
    print("  2. 夏普比率最大化 - 提高风险调整后收益")
    print("  3. 胜率最大化 - 提高 Top 组合胜率")
    print("  4. 趋势感知优化 - 结合趋势预测（新）")
    print("  5. 取消，返回主菜单")

    choice = input("\n请选择 (1-5): ").strip()

    methods = {
        '1': ('ic_rank', 'IC 最大化'),
        '2': ('sharpe', '夏普比率最大化'),
        '3': ('win_rate', '胜率最大化'),
        '4': ('trend_aware', '趋势感知优化')
    }

    if choice in methods:
        method, method_name = methods[choice]
        print(f"\n正在使用 {method_name} 优化权重...")

        optimized = scorer.optimize_weights(lookback_days=60, method=method)

        print(f"\n【优化后权重】")
        print(f"{'维度':<15} {'原权重':<10} {'优化后':<10} {'变化':<10}")
        print("-" * 50)

        default_weights = scorer.get_default_weights()

        for dim in ['capital', 'technical', 'holder', 'news', 'momentum']:
            old = default_weights.get(dim, 0.20)
            new = optimized.get(dim, old)
            change = new - old
            change_str = f"+{change:.2%}" if change > 0 else f"{change:.2%}"
            print(f"{dim.upper():<15} {old:>8.1%}   {new:>8.1%}   {change_str:>8}")

        # 询问是否应用
        apply = input("\n是否应用新权重？(y/n): ").strip().lower()
        if apply == 'y':
            scorer.apply_calibrated_weights(lookback_days=60)
            print("权重已更新！下次计算将使用新权重。")
        else:
            print("已取消，继续使用原权重。")

    elif choice == '5':
        print("已取消。")
    else:
        print("无效选择。")

    scorer.close()
    print("\n" + "=" * 60)


def export_backtest_report():
    """导出回测报告"""
    scorer = StockScorer()
    start_date = date.today() - timedelta(days=90)
    summary = scorer.get_backtest_summary(start_date=start_date, forward_days=5)

    # 保存为 JSON
    output_file = 'docs/backtest_report.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"回测报告已导出至：{output_file}")
    scorer.close()


if __name__ == "__main__":
    print("请选择操作：")
    print("  1. 运行回测分析")
    print("  2. 导出回测报告")
    print("  3. 退出")

    choice = input("\n请选择 (1-3): ").strip()

    if choice == '1':
        run_backtest_analysis()
    elif choice == '2':
        export_backtest_report()
    elif choice == '3':
        print("退出。")
    else:
        print("无效选择。")
