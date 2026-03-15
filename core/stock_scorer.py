"""
股票综合评分与推荐系统
"""
from core.database import SessionLocal
from core.models import Stock, StockDaily, StockCapitalFlow, StockHolderCount, StockNews
from core.indicator import IndicatorCalculator
from sqlalchemy import desc, func, and_
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
import pandas as pd


class StockScorer:
    """股票综合评分器"""

    def __init__(self):
        self.db = SessionLocal()

        # 评分权重
        self.weights = {
            'capital': 0.25,      # 资金流
            'technical': 0.25,    # 技术指标
            'holder': 0.20,       # 股东户数
            'news': 0.15,         # 新闻热度
            'momentum': 0.15      # 价格动量
        }

    def score_capital_flow(self, stock_code: str) -> tuple:
        """资金流评分 (0-100) - 返回 (分数，详细数据)"""
        # 获取最近 5 天的资金流数据
        flows = self.db.query(StockCapitalFlow).filter(
            StockCapitalFlow.stock_code == stock_code
        ).order_by(
            desc(StockCapitalFlow.trade_date)
        ).limit(5).all()

        if not flows:
            return 0, {
                "consecutive_days": 0,
                "total_net_inflow": 0,
                "avg_net_inflow": 0,
                "score_breakdown": {"consecutive_score": 0, "amount_score": 0},
                "daily_data": []
            }

        score = 0
        # 连续流入天数
        consecutive_inflow = 0
        total_net_inflow = 0
        daily_data = []

        for flow in flows:
            daily_info = {
                "date": str(flow.trade_date),
                "net_inflow": flow.net_inflow,
                "main_force_in": flow.main_force_in,
                "main_force_out": flow.main_force_out,
                "large_order_in": flow.large_order_in
            }
            daily_data.append(daily_info)

            if flow.net_inflow > 0:
                consecutive_inflow += 1
                total_net_inflow += flow.net_inflow
            else:
                break

        # 连续流入评分 (最多 40 分)
        consecutive_score = min(consecutive_inflow * 10, 40)
        score += consecutive_score

        # 净流入评分 (最多 60 分)
        avg_inflow = total_net_inflow / len(flows)
        if avg_inflow > 10000000:  # 大于 1000 万
            amount_score = 60
        elif avg_inflow > 5000000:
            amount_score = 45
        elif avg_inflow > 1000000:
            amount_score = 30
        elif avg_inflow > 0:
            amount_score = 15
        else:
            amount_score = 0
        score += amount_score

        details = {
            "consecutive_days": consecutive_inflow,
            "total_net_inflow": total_net_inflow,
            "avg_net_inflow": avg_inflow,
            "latest_trade_date": str(flows[0].trade_date) if flows else None,
            "score_breakdown": {
                "consecutive_score": consecutive_score,
                "amount_score": amount_score,
                "max_consecutive_score": 40,
                "max_amount_score": 60
            },
            "scoring_rules": {
                "consecutive": "连续流入天数 × 10 分，最高 40 分",
                "amount": "日均净流入>1000 万得 60 分，>500 万得 45 分，>100 万得 30 分，>0 得 15 分"
            },
            "daily_data": daily_data
        }
        return min(score, 100), details

    def score_technical(self, stock_code: str) -> tuple:
        """技术指标评分 (0-100) - 返回 (分数，详细数据)"""
        calc = IndicatorCalculator()
        result = calc.calculate_all(stock_code)

        if not result:
            return 50, {
                "ma5": None, "ma20": None, "macd": None, "rsi": None,
                "signals": [], "score_breakdown": {"base": 50}
            }

        score = 50  # 基础分
        signals = result.get('signals', {})
        signal_details = []
        score_changes = [{"item": "基础分", "change": 0, "score": 50}]

        # 均线信号 (+/- 20 分)
        if signals.get('ma_golden_cross'):
            score += 20
            signal_details.append("MA 金叉")
            score_changes.append({"item": "MA 金叉", "change": 20, "score": score})
        if signals.get('ma_death_cross'):
            score -= 20
            signal_details.append("MA 死叉")
            score_changes.append({"item": "MA 死叉", "change": -20, "score": score})

        # MACD 信号 (+/- 15 分)
        if signals.get('macd_bullish'):
            score += 15
            signal_details.append("MACD 多头")
            score_changes.append({"item": "MACD 多头", "change": 15, "score": score})
        if signals.get('macd_bearish'):
            score -= 15
            signal_details.append("MACD 空头")
            score_changes.append({"item": "MACD 空头", "change": -15, "score": score})

        # RSI 信号 (+/- 15 分)
        if signals.get('rsi_oversold'):
            score += 15  # 超卖是买入机会
            signal_details.append("RSI 超卖")
            score_changes.append({"item": "RSI 超卖", "change": 15, "score": score})
        if signals.get('rsi_overbought'):
            score -= 15  # 超买是风险
            signal_details.append("RSI 超买")
            score_changes.append({"item": "RSI 超买", "change": -15, "score": score})

        details = {
            "ma5": result.get('ma5'),
            "ma20": result.get('ma20'),
            "macd": result.get('macd'),
            "rsi": result.get('rsi'),
            "close": result.get('close'),
            "kdj_k": result.get('kdj_k'),
            "kdj_d": result.get('kdj_d'),
            "boll_upper": result.get('boll_upper'),
            "boll_lower": result.get('boll_lower'),
            "signals": signal_details,
            "score_breakdown": {
                "base": 50,
                "ma_signal": 20 if signals.get('ma_golden_cross') else (-20 if signals.get('ma_death_cross') else 0),
                "macd_signal": 15 if signals.get('macd_bullish') else (-15 if signals.get('macd_bearish') else 0),
                "rsi_signal": 15 if signals.get('rsi_oversold') else (-15 if signals.get('rsi_overbought') else 0)
            },
            "scoring_rules": {
                "base": "基础分 50 分",
                "ma": "金叉 +20 分，死叉 -20 分",
                "macd": "多头 +15 分，空头 -15 分",
                "rsi": "超卖 +15 分 (买入机会), 超买 -15 分 (风险)"
            },
            "score_history": score_changes
        }
        return max(0, min(score, 100)), details

    def score_holder_count(self, stock_code: str) -> tuple:
        """股东户数评分 (0-100) - 返回 (分数，详细数据)"""
        latest = self.db.query(StockHolderCount).filter(
            StockHolderCount.stock_code == stock_code
        ).order_by(
            desc(StockHolderCount.trade_date)
        ).first()

        if not latest:
            return 50, {
                "holder_count": None,
                "change_ratio": None,
                "trend": "unknown",
                "score_breakdown": {"base": 50}
            }

        score = 50
        trend_signals = []
        score_changes = [{"item": "基础分", "change": 0, "score": 50}]

        # 最新一期变化
        if latest.change_ratio < -5:  # 股东户数减少 5% 以上
            score += 30
            trend_signals.append("筹码大幅集中 (>5%)")
            score_changes.append({"item": "筹码大幅集中", "change": 30, "score": score})
        elif latest.change_ratio < -2:
            score += 20
            trend_signals.append("筹码集中 (2-5%)")
            score_changes.append({"item": "筹码集中", "change": 20, "score": score})
        elif latest.change_ratio < 0:
            score += 10
            trend_signals.append("筹码小幅集中")
            score_changes.append({"item": "筹码小幅集中", "change": 10, "score": score})
        elif latest.change_ratio > 5:
            score -= 20
            trend_signals.append("筹码分散")
            score_changes.append({"item": "筹码分散", "change": -20, "score": score})
        elif latest.change_ratio > 10:
            score -= 30
            trend_signals.append("筹码大幅分散")
            score_changes.append({"item": "筹码大幅分散", "change": -30, "score": score})
        else:
            trend_signals.append("筹码稳定")
            score_changes.append({"item": "筹码稳定", "change": 0, "score": score})

        # 检查连续减少趋势
        recent = self.db.query(StockHolderCount).filter(
            StockHolderCount.stock_code == stock_code
        ).order_by(
            desc(StockHolderCount.trade_date)
        ).limit(3).all()

        consecutive_decrease = 0
        if len(recent) >= 3:
            for r in recent:
                if r.change_count < 0:
                    consecutive_decrease += 1
                else:
                    break

            if consecutive_decrease >= 3:
                score += 20  # 连续 3 期减少，额外加分
                trend_signals.append(f"连续{consecutive_decrease}期减少")
                score_changes.append({"item": f"连续{consecutive_decrease}期减少", "change": 20, "score": score})

        details = {
            "holder_count": latest.holder_count,
            "change_count": latest.change_count,
            "change_ratio": latest.change_ratio,
            "avg_holdings": latest.avg_holdings,
            "trend": trend_signals,
            "consecutive_decrease": consecutive_decrease,
            "trade_date": str(latest.trade_date),
            "score_breakdown": {
                "base": 50,
                "trend_change": score_changes[-1]["change"] if len(score_changes) > 1 else 0,
                "consecutive_bonus": 20 if consecutive_decrease >= 3 else 0
            },
            "scoring_rules": {
                "base": "基础分 50 分",
                "trend": "股东户数减少 5% 以上 +30 分，2-5% +20 分，减少 +10 分",
                "risk": "股东户数增加 5% 以上 -20 分，10% 以上 -30 分",
                "consecutive": "连续 3 期减少额外 +20 分"
            },
            "score_history": score_changes,
            "history_data": [
                {
                    "date": str(r.trade_date),
                    "holder_count": r.holder_count,
                    "change_ratio": r.change_ratio
                }
                for r in recent
            ]
        }
        return max(0, min(score, 100)), details

    def score_news_sentiment(self, stock_code: str) -> tuple:
        """新闻情绪评分 (0-100) - 返回 (分数，详细数据)"""
        # 获取最近 7 天的新闻
        cutoff_date = datetime.now() - timedelta(days=7)
        news_list = self.db.query(StockNews).filter(
            StockNews.stock_code == stock_code,
            StockNews.publish_time >= cutoff_date
        ).all()

        if not news_list:
            return 50, {
                "news_count": 0,
                "avg_sentiment": 0,
                "positive_count": 0,
                "negative_count": 0,
                "score_breakdown": {"base": 50}
            }

        # 计算平均情绪分数
        avg_sentiment = sum(n.sentiment_score for n in news_list) / len(news_list)

        # 统计正负面新闻数量
        positive_count = sum(1 for n in news_list if n.sentiment_score > 0.5)
        negative_count = sum(1 for n in news_list if n.sentiment_score < -0.5)

        # 转换为 0-100 分数
        score = avg_sentiment * 100

        # 新闻数量加分 (最多 20 分)
        if len(news_list) > 10:
            score += 20
            count_bonus = 20
        elif len(news_list) > 5:
            score += 10
            count_bonus = 10
        else:
            count_bonus = 0

        # 获取最新的几条新闻
        recent_news = sorted(news_list, key=lambda x: x.publish_time, reverse=True)[:5]

        details = {
            "news_count": len(news_list),
            "avg_sentiment": avg_sentiment,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": len(news_list) - positive_count - negative_count,
            "score_breakdown": {
                "sentiment_score": round(avg_sentiment * 100, 2),
                "count_bonus": count_bonus,
                "max_count_bonus": 20
            },
            "scoring_rules": {
                "sentiment": "平均情绪分数 × 100 (范围 -100 到 100)",
                "count": "新闻数量>10 篇 +20 分，>5 篇 +10 分"
            },
            "recent_news": [
                {
                    "title": n.title[:50] + "..." if len(n.title) > 50 else n.title,
                    "sentiment": n.sentiment,
                    "sentiment_score": n.sentiment_score,
                    "publish_time": str(n.publish_time)
                }
                for n in recent_news
            ]
        }
        return max(0, min(score, 100)), details

    def score_momentum(self, stock_code: str) -> tuple:
        """价格动量评分 (0-100) - 返回 (分数，详细数据)"""
        # 获取最近 20 天的数据
        data = self.db.query(StockDaily).filter(
            StockDaily.stock_code == stock_code
        ).order_by(
            desc(StockDaily.trade_date)
        ).limit(20).all()

        if len(data) < 20:
            return 50, {
                "close": None, "ma20": None, "change_5d": None, "change_20d": None,
                "score_breakdown": {"base": 50}
            }

        latest_close = data[0].close
        ma20 = sum(d.close for d in data) / len(data)
        price_20d_ago = data[-1].close

        # 计算 5 日涨幅
        price_5d_ago = data[4].close if len(data) > 4 else latest_close
        change_5d = (latest_close - price_5d_ago) / price_5d_ago * 100 if price_5d_ago else 0

        score = 50
        momentum_signals = []
        score_changes = [{"item": "基础分", "change": 0, "score": 50}]
        score_breakdown = {"base": 50, "ma20_signal": 0, "change_20d_signal": 0}

        # 价格在 20 日线上
        if latest_close > ma20:
            score += 20
            score_breakdown["ma20_signal"] = 20
            momentum_signals.append("价格>MA20")
            score_changes.append({"item": "价格>MA20", "change": 20, "score": score})
        else:
            score_breakdown["ma20_signal"] = -20
            momentum_signals.append("价格<MA20")
            score_changes.append({"item": "价格<MA20", "change": -20, "score": score})

        # 20 日涨幅
        change_20d = (latest_close - price_20d_ago) / price_20d_ago * 100 if price_20d_ago else 0
        if change_20d > 20:
            score += 30
            score_breakdown["change_20d_signal"] = 30
            momentum_signals.append("20 日大涨 (>20%)")
        elif change_20d > 10:
            score += 20
            score_breakdown["change_20d_signal"] = 20
            momentum_signals.append("20 日上涨 (10-20%)")
        elif change_20d > 5:
            score += 10
            score_breakdown["change_20d_signal"] = 10
            momentum_signals.append("20 日小幅上涨 (5-10%)")
        elif change_20d < -20:
            score -= 20
            score_breakdown["change_20d_signal"] = -20
            momentum_signals.append("20 日大跌 (<-20%)")
        elif change_20d < -10:
            score -= 10
            score_breakdown["change_20d_signal"] = -10
            momentum_signals.append("20 日下跌 (-10~-20%)")
        else:
            score_breakdown["change_20d_signal"] = 0
            momentum_signals.append("20 日震荡")

        score_changes.append({"item": "20 日涨幅", "change": score_breakdown["change_20d_signal"], "score": score})

        details = {
            "close": latest_close,
            "ma20": ma20,
            "change_5d": round(change_5d, 2),
            "change_20d": round(change_20d, 2),
            "signals": momentum_signals,
            "score_breakdown": score_breakdown,
            "scoring_rules": {
                "base": "基础分 50 分",
                "ma20": "价格>MA20 +20 分，否则 -20 分",
                "change_20d": "20 日涨幅>20% +30 分，>10% +20 分，>5% +10 分，<-20% -20 分，<-10% -10 分"
            },
            "score_history": score_changes,
            "price_history": [
                {
                    "date": str(d.trade_date),
                    "close": d.close,
                    "volume": d.volume
                }
                for d in data[:10]  # 最近 10 天
            ]
        }
        return max(0, min(score, 100)), details

    def calculate_total_score(self, stock_code: str) -> Dict:
        """计算股票综合评分"""
        capital_score, capital_details = self.score_capital_flow(stock_code)
        technical_score, technical_details = self.score_technical(stock_code)
        holder_score, holder_details = self.score_holder_count(stock_code)
        news_score, news_details = self.score_news_sentiment(stock_code)
        momentum_score, momentum_details = self.score_momentum(stock_code)

        scores = {
            'capital': capital_score,
            'technical': technical_score,
            'holder': holder_score,
            'news': news_score,
            'momentum': momentum_score
        }

        # 加权总分
        total = sum(
            scores[k] * self.weights[k]
            for k in scores.keys()
        )

        return {
            'stock_code': stock_code,
            'total_score': round(total, 2),
            'scores': scores,
            'details': {
                'capital': capital_details,
                'technical': technical_details,
                'holder': holder_details,
                'news': news_details,
                'momentum': momentum_details
            }
        }

    def get_top_stocks(self, top_n: int = 20, min_score: float = 60) -> List[Dict]:
        """获取推荐股票 Top N - 优化版本，使用分批查询和早期过滤"""
        from datetime import date, timedelta

        # 1. 批量获取日线数据 - 只获取最近 30 天的数据，用于过滤活跃股票
        # 使用子查询限定每个股票只取最近 30 条
        from sqlalchemy import distinct

        # 先获取所有股票代码
        all_stocks = self.db.query(Stock).all()
        stock_name_map = {s.code: s.name for s in all_stocks}

        # 获取最近 60 天的日线数据（限定日期范围，减少数据量）
        cutoff_date = date.today() - timedelta(days=60)
        daily_data_all = self.db.query(StockDaily).filter(
            StockDaily.trade_date >= cutoff_date
        ).order_by(desc(StockDaily.trade_date)).all()

        # 按股票代码分组
        daily_map = {}
        for d in daily_data_all:
            if d.stock_code not in daily_map:
                daily_map[d.stock_code] = []
            daily_map[d.stock_code].append(d)

        # 早期过滤：只分析有足够数据且活跃的股票
        filtered_codes = []
        today = date.today()
        for code, data in daily_map.items():
            # 至少需要 26 天数据用于 MACD 计算
            if len(data) < 26:
                continue
            # 最近 7 天内有交易数据（活跃股票）- 放宽条件以包含更多股票
            latest_date = data[0].trade_date if data else None
            if latest_date and (today - latest_date).days > 7:
                continue
            filtered_codes.append(code)

        print(f"过滤后剩余 {len(filtered_codes)} 只活跃股票（60 天内有 26+ 天数据）")

        # 2. 批量获取资金流数据 - 只获取最近 5 天
        capital_cutoff = date.today() - timedelta(days=7)
        capital_flows = self.db.query(StockCapitalFlow).filter(
            StockCapitalFlow.stock_code.in_(filtered_codes),
            StockCapitalFlow.trade_date >= capital_cutoff
        ).all()
        capital_map = {}
        for flow in capital_flows:
            if flow.stock_code not in capital_map:
                capital_map[flow.stock_code] = []
            capital_map[flow.stock_code].append(flow)

        # 3. 批量获取股东户数数据 - 只获取最近的数据
        holder_cutoff = date.today() - timedelta(days=30)
        holder_data = self.db.query(StockHolderCount).filter(
            StockHolderCount.stock_code.in_(filtered_codes),
            StockHolderCount.trade_date >= holder_cutoff
        ).all()
        holder_map = {}
        for h in holder_data:
            if h.stock_code not in holder_map:
                holder_map[h.stock_code] = []
            holder_map[h.stock_code].append(h)

        # 4. 批量获取新闻数据 (最近 7 天)
        news_cutoff = datetime.now() - timedelta(days=7)
        news_data = self.db.query(StockNews).filter(
            StockNews.stock_code.in_(filtered_codes),
            StockNews.publish_time >= news_cutoff
        ).all()
        news_map = {}
        for n in news_data:
            if n.stock_code not in news_map:
                news_map[n.stock_code] = []
            news_map[n.stock_code].append(n)

        # 5. 计算每只股票的分数 - 使用快速预筛选
        results = []
        for code in filtered_codes:
            try:
                stock = next((s for s in all_stocks if s.code == code), None)
                if not stock:
                    continue

                # 快速预筛选：先计算资金流评分（最快）
                capital_score = self._score_capital_from_data(capital_map.get(code, []))

                # 如果资金流评分太低，跳过（快速失败）
                if capital_score < 30:
                    continue

                # 通过预筛选后才计算其他分数
                technical_score = self._score_technical_fast(code, daily_map.get(code, []))
                holder_score = self._score_holder_from_data(holder_map.get(code, []))
                news_score = self._score_news_from_data(news_map.get(code, []))
                momentum_score = self._score_momentum_from_data(daily_map.get(code, []))

                scores = {
                    'capital': capital_score,
                    'technical': technical_score,
                    'holder': holder_score,
                    'news': news_score,
                    'momentum': momentum_score
                }

                total = sum(scores[k] * self.weights[k] for k in scores.keys())

                if total >= min_score:
                    results.append({
                        'stock_code': code,
                        'stock_name': stock.name,
                        'total_score': round(total, 2),
                        'scores': scores
                    })
            except Exception:
                pass

        # 按总分排序
        results.sort(key=lambda x: x['total_score'], reverse=True)
        return results[:top_n]

    def _score_capital_from_data(self, flows: list) -> int:
        """资金流评分 - 使用已查询的数据"""
        if not flows:
            return 0
        flows = flows[:5]  # 最近 5 天
        consecutive_inflow = 0
        total_net_inflow = 0
        for flow in flows:
            if flow.net_inflow > 0:
                consecutive_inflow += 1
                total_net_inflow += flow.net_inflow
            else:
                break
        consecutive_score = min(consecutive_inflow * 10, 40)
        avg_inflow = total_net_inflow / len(flows)
        if avg_inflow > 10000000:
            amount_score = 60
        elif avg_inflow > 5000000:
            amount_score = 45
        elif avg_inflow > 1000000:
            amount_score = 30
        elif avg_inflow > 0:
            amount_score = 15
        else:
            amount_score = 0
        return min(consecutive_score + amount_score, 100)

    def _sma(self, values: list, period: int) -> float:
        """Simple Moving Average - pure Python"""
        if len(values) < period:
            return float('nan')
        return sum(values[-period:]) / period

    def _rsi(self, values: list, period: int = 14) -> float:
        """RSI - pure Python implementation"""
        if len(values) < period + 1:
            return float('nan')
        gains = []
        losses = []
        for i in range(1, len(values)):
            change = values[i] - values[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        if len(gains) < period:
            return float('nan')
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _macd(self, values: list, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """MACD - pure Python implementation"""
        if len(values) < slow + signal:
            return (float('nan'), float('nan'), float('nan'))
        # Calculate EMA fast and slow
        def ema(vals, period):
            if not vals:
                return float('nan')
            multiplier = 2 / (period + 1)
            ema_val = sum(vals[:period]) / period
            for val in vals[period:]:
                ema_val = (val * multiplier) + (ema_val * (1 - multiplier))
            return ema_val
        ema_fast = ema(values, fast)
        ema_slow = ema(values, slow)
        macd_line = ema_fast - ema_slow
        # For signal line, we need historical MACD values - simplified version
        # Just use MACD line position relative to zero
        signal_line = macd_line * 0.8  # Simplified approximation
        histogram = macd_line - signal_line
        return (macd_line, signal_line, histogram)

    def _score_technical_fast(self, stock_code: str, daily_data: list) -> int:
        """技术评分 - 快速版本（纯 Python 实现，避免 pandas_ta 开销）"""
        if len(daily_data) < 26:  # Need at least 26 days for MACD
            return 50
        try:
            # Extract closes in chronological order
            closes = [d.close for d in reversed(daily_data[:26])]
            highs = [d.high for d in reversed(daily_data[:26])]
            lows = [d.low for d in reversed(daily_data[:26])]

            score = 50
            current_price = closes[-1]

            # MA signals (pure Python)
            ma5 = self._sma(closes, 5)
            ma20 = self._sma(closes, 20)
            if not (ma5 != ma5 or ma20 != ma20):  # Check for NaN using self-comparison
                if ma5 > ma20:
                    score += 20
                elif ma5 < ma20:
                    score -= 20

            # MACD signals (pure Python)
            macd_line, signal_line, histogram = self._macd(closes)
            if not (macd_line != macd_line or signal_line != signal_line):
                if macd_line > signal_line:
                    score += 15
                else:
                    score -= 15

            # RSI signals (pure Python)
            rsi = self._rsi(closes)
            if not (rsi != rsi):  # Check for NaN
                if rsi < 30:
                    score += 15
                elif rsi > 70:
                    score -= 15

            return max(0, min(score, 100))
        except Exception:
            return 50

    def _score_holder_from_data(self, holder_list: list) -> int:
        """股东户数评分 - 使用已查询的数据"""
        if not holder_list:
            return 50
        latest = holder_list[0]
        score = 50
        if latest.change_ratio < -5:
            score += 30
        elif latest.change_ratio < -2:
            score += 20
        elif latest.change_ratio < 0:
            score += 10
        elif latest.change_ratio > 10:
            score -= 30
        elif latest.change_ratio > 5:
            score -= 20
        # 连续减少检查
        if len(holder_list) >= 3:
            consecutive = sum(1 for h in holder_list[:3] if h.change_count < 0)
            if consecutive >= 3:
                score += 20
        return max(0, min(score, 100))

    def _score_news_from_data(self, news_list: list) -> int:
        """新闻评分 - 使用已查询的数据"""
        if not news_list:
            return 50
        avg_sentiment = sum(n.sentiment_score for n in news_list) / len(news_list)
        score = avg_sentiment * 100
        if len(news_list) > 10:
            score += 20
        elif len(news_list) > 5:
            score += 10
        return max(0, min(score, 100))

    def _score_momentum_from_data(self, daily_data: list) -> int:
        """动量评分 - 使用已查询的数据"""
        if len(daily_data) < 20:
            return 50
        score = 50
        closes = [d.close for d in daily_data[:20]]
        latest_close = closes[0]
        ma20 = sum(closes) / len(closes)
        price_20d_ago = closes[-1]
        price_5d_ago = closes[4] if len(closes) > 4 else latest_close
        change_20d = (latest_close - price_20d_ago) / price_20d_ago * 100 if price_20d_ago else 0
        # 价格在 20 日线上
        if latest_close > ma20:
            score += 20
        else:
            score -= 20
        # 20 日涨幅
        if change_20d > 20:
            score += 30
        elif change_20d > 10:
            score += 20
        elif change_20d > 5:
            score += 10
        elif change_20d < -20:
            score -= 20
        elif change_20d < -10:
            score -= 10
        return max(0, min(score, 100))

    def get_stock_analysis(self, stock_code: str) -> Optional[Dict]:
        """获取单只股票的详细分析"""
        stock = self.db.query(Stock).filter(Stock.code == stock_code).first()
        if not stock:
            return None

        # 使用 calculate_total_score 获取完整的分析数据（包含 details）
        analysis_result = self.calculate_total_score(stock_code)
        analysis_result['stock_name'] = stock.name

        return analysis_result

    def get_recommendations_from_db(self, trade_date: date = None, top_n: int = 20, min_score: float = 60) -> List[Dict]:
        """从数据库获取预计算的推荐结果"""
        from core.models import StockRecommendation

        if trade_date is None:
            # 获取最新的推荐日期
            latest = self.db.query(
                func.max(StockRecommendation.trade_date)
            ).scalar()
            if not latest:
                return self.get_top_stocks(top_n=top_n, min_score=min_score)
            trade_date = latest

        # 从预计算结果中获取
        recommendations = self.db.query(StockRecommendation).filter(
            StockRecommendation.trade_date == trade_date,
            StockRecommendation.total_score >= min_score
        ).order_by(
            StockRecommendation.rank
        ).limit(top_n).all()

        return [{
            'stock_code': rec.stock_code,
            'stock_name': rec.stock_name,
            'total_score': rec.total_score,
            'scores': {
                'capital': rec.capital_score,
                'technical': rec.technical_score,
                'holder': rec.holder_score,
                'news': rec.news_score,
                'momentum': rec.momentum_score
            },
            'rank': rec.rank
        } for rec in recommendations]

    def get_top_stocks_raw(self, trade_date: date = None) -> List[Dict]:
        """获取所有股票的原始评分数据（用于预计算存储）"""
        from datetime import date as date_type
        from core.models import StockDaily

        if trade_date is None:
            trade_date = date.today()

        # 1. 获取所有股票
        stocks = self.db.query(Stock).all()
        stock_codes = [s.code for s in stocks]

        # 2. 获取日线数据（最近 60 天）
        cutoff_date = trade_date - timedelta(days=60)
        daily_data_all = self.db.query(StockDaily).filter(
            StockDaily.trade_date >= cutoff_date
        ).all()

        daily_map = {}
        for d in daily_data_all:
            if d.stock_code not in daily_map:
                daily_map[d.stock_code] = []
            daily_map[d.stock_code].append(d)

        # 过滤活跃股票
        filtered_codes = []
        for code, data in daily_map.items():
            if len(data) < 26:
                continue
            filtered_codes.append(code)

        print(f"过滤后剩余 {len(filtered_codes)} 只活跃股票")

        # 3. 批量获取其他数据
        capital_cutoff = trade_date - timedelta(days=7)
        capital_flows = self.db.query(StockCapitalFlow).filter(
            StockCapitalFlow.stock_code.in_(filtered_codes),
            StockCapitalFlow.trade_date >= capital_cutoff
        ).all()
        capital_map = {}
        for flow in capital_flows:
            if flow.stock_code not in capital_map:
                capital_map[flow.stock_code] = []
            capital_map[flow.stock_code].append(flow)

        holder_cutoff = trade_date - timedelta(days=30)
        holder_data = self.db.query(StockHolderCount).filter(
            StockHolderCount.stock_code.in_(filtered_codes),
            StockHolderCount.trade_date >= holder_cutoff
        ).all()
        holder_map = {}
        for h in holder_data:
            if h.stock_code not in holder_map:
                holder_map[h.stock_code] = []
            holder_map[h.stock_code].append(h)

        news_cutoff = datetime.now() - timedelta(days=7)
        news_data = self.db.query(StockNews).filter(
            StockNews.stock_code.in_(filtered_codes),
            StockNews.publish_time >= news_cutoff
        ).all()
        news_map = {}
        for n in news_data:
            if n.stock_code not in news_map:
                news_map[n.stock_code] = []
            news_map[n.stock_code].append(n)

        # 4. 计算评分
        results = []
        for code in filtered_codes:
            try:
                stock = next((s for s in stocks if s.code == code), None)
                if not stock:
                    continue

                capital_score = self._score_capital_from_data(capital_map.get(code, []))
                if capital_score < 20:  # 更宽松的预筛选
                    continue

                technical_score = self._score_technical_fast(code, daily_map.get(code, []))
                holder_score = self._score_holder_from_data(holder_map.get(code, []))
                news_score = self._score_news_from_data(news_map.get(code, []))
                momentum_score = self._score_momentum_from_data(daily_map.get(code, []))

                scores = {
                    'capital': capital_score,
                    'technical': technical_score,
                    'holder': holder_score,
                    'news': news_score,
                    'momentum': momentum_score
                }

                total = sum(scores[k] * self.weights[k] for k in scores.keys())

                results.append({
                    'stock_code': code,
                    'stock_name': stock.name,
                    'total_score': round(total, 2),
                    'scores': scores
                })
            except Exception:
                pass

        # 按总分排序
        results.sort(key=lambda x: x['total_score'], reverse=True)
        return results

    def get_backtest_summary(self, start_date: date = None, forward_days: int = 5) -> Dict:
        """获取回测统计摘要"""
        from core.backtester import RecommendationBacktester

        backtester = RecommendationBacktester()
        try:
            summary = backtester.get_backtest_summary(start_date=start_date, forward_days=forward_days)
        finally:
            backtester.close()
        return summary

    def get_dimension_analysis(self, lookback_days: int = 60) -> Dict:
        """获取各维度预测能力分析"""
        from core.backtester import RecommendationBacktester

        backtester = RecommendationBacktester()
        try:
            history = backtester.get_recommendation_history(
                start_date=date.today() - timedelta(days=lookback_days)
            )
            if len(history) < 30:
                return {'error': '数据不足', 'n': len(history)}

            df = backtester.calculate_forward_returns(history, forward_days=5)
            analysis = backtester.analyze_dimension_predictive_power(df)
            return analysis
        finally:
            backtester.close()

    def optimize_weights(self, lookback_days: int = 60, method: str = 'ic_rank') -> Dict[str, float]:
        """优化评分权重"""
        from core.weight_optimizer import AdaptiveWeightOptimizer

        optimizer = AdaptiveWeightOptimizer()
        try:
            optimized = optimizer.optimize_weights(lookback_days=lookback_days, method=method)
            return optimized
        finally:
            optimizer.close()

    def apply_calibrated_weights(self, lookback_days: int = 60):
        """应用校准后的权重"""
        optimized = self.optimize_weights(lookback_days=lookback_days)
        self.weights = optimized
        return optimized

    def get_default_weights(self) -> Dict[str, float]:
        """获取默认权重"""
        from core.weight_optimizer import AdaptiveWeightOptimizer
        optimizer = AdaptiveWeightOptimizer()
        try:
            return optimizer.default_weights.copy()
        finally:
            optimizer.close()

    def close(self):
        self.db.close()
