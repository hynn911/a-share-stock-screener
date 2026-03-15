"""
持仓管理与卖点信号
"""
from datetime import datetime
from sqlalchemy import desc
import pandas as pd
import akshare as ak
from core.database import SessionLocal
from core.models import Position, SellSignal, StockDaily, Stock
from core.indicator import IndicatorCalculator
from core.capital import CapitalAnalyzer
from core.stock_scorer import StockScorer
from core.shareholder import ShareholderAnalyzer


class PositionManager:
    """持仓管理器"""

    def __init__(self):
        self.db = SessionLocal()
        self.indicator_calc = IndicatorCalculator()
        self.capital_analyzer = CapitalAnalyzer()
        self.stock_scorer = StockScorer()
        self.holder_analyzer = ShareholderAnalyzer()

    def add_position(self, stock_code: str, stock_name: str, buy_price: float,
                     quantity: int, buy_date: str = None,
                     stop_loss_rate: float = 0.08,
                     target_profit_rate: float = 0.30,
                     max_drawdown_rate: float = 0.10) -> Position:
        """添加持仓"""
        position = Position(
            stock_code=stock_code,
            stock_name=stock_name,
            buy_price=buy_price,
            quantity=quantity,
            buy_date=buy_date or datetime.now().date(),
            stop_loss_rate=stop_loss_rate,
            target_profit_rate=target_profit_rate,
            max_drawdown_rate=max_drawdown_rate
        )

        self.db.add(position)
        self.db.commit()
        self.db.refresh(position)
        return position

    def get_all_positions(self, status: str = "holding") -> list:
        """获取所有持仓"""
        positions = self.db.query(Position).filter(
            Position.status == status
        ).all()
        return positions

    def update_position_price(self, position: Position, current_price: float):
        """更新当前价并计算盈亏"""
        # 避免除以零错误
        if position.buy_price and position.buy_price > 0:
            # 盈亏比例
            position.profit_loss = (current_price - position.buy_price) / position.buy_price
            # 盈亏金额
            position.profit_amount = (current_price - position.buy_price) * position.quantity
        else:
            position.profit_loss = 0
            position.profit_amount = 0

        self.db.commit()

    def get_latest_close_price(self, stock_code: str, use_realtime: bool = True) -> float:
        """获取最新价格（优先实时，休市时使用本地存储）

        Args:
            stock_code: 股票代码
            use_realtime: 是否优先获取实时价格（默认 True）

        Returns:
            最新价格，如果都无法获取则返回 None
        """
        if use_realtime:
            # 1. 优先尝试从 API 获取实时价格
            try:
                df = ak.stock_zh_a_spot_em()
                stock_data = df[df['代码'] == stock_code]
                if not stock_data.empty and pd.notna(stock_data.iloc[0]['最新价']):
                    real_price = float(stock_data.iloc[0]['最新价'])
                    # 检查是否休市（价格为 0 或 NaN）
                    if real_price > 0:
                        return real_price
            except Exception:
                pass  # API 失败，回退到本地数据

        # 2. 从数据库获取最新收盘价（盘后数据或休市时使用）
        try:
            latest = self.db.query(StockDaily).filter(
                StockDaily.stock_code == stock_code
            ).order_by(desc(StockDaily.trade_date)).first()

            if latest:
                return latest.close
            return None
        except Exception:
            return None

    def get_stock_name_from_db(self, stock_code: str) -> str:
        """从数据库获取股票名称（优先使用，避免 API 不稳定）"""
        try:
            stock = self.db.query(Stock).filter(Stock.code == stock_code).first()
            if stock:
                return stock.name
            return ""
        except Exception:
            return ""

    def get_stock_info(self, stock_code: str) -> dict:
        """获取股票信息（优先从数据库获取名称，API 获取实时价格）"""
        try:
            # 从数据库获取股票名称（更可靠）
            stock_name = self.get_stock_name_from_db(stock_code)

            # 获取实时行情数据
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == stock_code]

            if stock_data.empty:
                # API 没有数据，返回数据库名称
                return {
                    'code': stock_code,
                    'name': stock_name,
                    'current_price': None,
                    'change_pct': None,
                    'change': None,
                    'volume': None,
                    'amount': None,
                    'pe_ratio': None,
                    'pb_ratio': None,
                    'market_cap': None,
                    'industry': '',
                    'concept': ''
                } if stock_name else {}

            row = stock_data.iloc[0]
            return {
                'code': stock_code,
                'name': stock_name or str(row['名称']),  # 优先使用数据库名称
                'current_price': float(row['最新价']) if pd.notna(row['最新价']) else None,
                'change_pct': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else None,
                'change': float(row['涨跌额']) if pd.notna(row['涨跌额']) else None,
                'volume': float(row['成交量']) if pd.notna(row['成交量']) else None,
                'amount': float(row['成交额']) if pd.notna(row['成交额']) else None,
                'pe_ratio': float(row['市盈率 - 动态']) if pd.notna(row['市盈率 - 动态']) else None,
                'pb_ratio': float(row['市净率']) if pd.notna(row['市净率']) else None,
                'market_cap': float(row['总市值']) if pd.notna(row['总市值']) else None,
                'industry': str(row.get('行业', '')),
                'concept': str(row.get('概念板块', ''))
            }
        except Exception:
            # 失败时至少返回数据库中的名称
            stock_name = self.get_stock_name_from_db(stock_code)
            return {
                'code': stock_code,
                'name': stock_name,
                'current_price': None
            } if stock_name else {}

    def get_position_analysis(self, position: Position, current_price: float) -> dict:
        """获取持仓的五维度综合分析"""
        stock_code = position.stock_code

        # 获取五维度评分
        capital_score, capital_details = self.stock_scorer.score_capital_flow(stock_code)
        technical_score, technical_details = self.stock_scorer.score_technical(stock_code)
        holder_score, holder_details = self.stock_scorer.score_holder_count(stock_code)
        news_score, news_details = self.stock_scorer.score_news_sentiment(stock_code)
        momentum_score, momentum_details = self.stock_scorer.score_momentum(stock_code)

        # 计算综合评分
        total_score = (
            capital_score * 0.25 +
            technical_score * 0.25 +
            holder_score * 0.20 +
            news_score * 0.15 +
            momentum_score * 0.15
        )

        return {
            'total_score': round(total_score, 2),
            'capital': {'score': capital_score, 'details': capital_details},
            'technical': {'score': technical_score, 'details': technical_details},
            'holder': {'score': holder_score, 'details': holder_details},
            'news': {'score': news_score, 'details': news_details},
            'momentum': {'score': momentum_score, 'details': momentum_details}
        }

    def check_sell_signals(self, position: Position, current_price: float) -> list:
        """检查卖出信号 - 基于五维度综合分析"""
        signals = []

        # 1. 止盈信号
        if position.profit_loss >= position.target_profit_rate:
            signals.append({
                'type': 'TAKE_PROFIT',
                'priority': 'HIGH',
                'description': f'收益率已达{position.profit_loss:.1%}，达到目标止盈位 ({position.target_profit_rate:.0%})',
                'suggestion': f'建议卖出{position.quantity * 0.5:.0f}股（50% 仓位）'
            })

        # 2. 止损信号
        if position.profit_loss <= -position.stop_loss_rate:
            signals.append({
                'type': 'STOP_LOSS',
                'priority': 'CRITICAL',
                'description': f'亏损已达{position.profit_loss:.1%}，触及止损线 (-{position.stop_loss_rate:.0%})',
                'suggestion': '建议立即止损离场'
            })

        # 3. 技术指标信号
        indicator_data = self.indicator_calc.calculate_all(position.stock_code)
        if indicator_data.get('signals'):
            sigs = indicator_data['signals']

            if sigs.get('ma_death_cross'):
                signals.append({
                    'type': 'TECHNICAL',
                    'priority': 'HIGH',
                    'description': '5 日线下穿 10 日线，形成死叉',
                    'suggestion': '短期趋势转弱，建议减仓'
                })

            if sigs.get('macd_bearish'):
                signals.append({
                    'type': 'TECHNICAL',
                    'priority': 'MEDIUM',
                    'description': 'MACD 死叉',
                    'suggestion': '中期趋势转弱'
                })

            if sigs.get('rsi_overbought'):
                signals.append({
                    'type': 'TECHNICAL',
                    'priority': 'MEDIUM',
                    'description': f'RSI={sigs.get("rsi", 0):.1f}，进入超买区',
                    'suggestion': '短期可能回调'
                })

        # 4. 资金流出信号
        capital_trend = self.capital_analyzer.get_capital_trend(position.stock_code)
        if capital_trend.get('net_inflow', 0) < -50000000:  # 净流出超 5000 万
            signals.append({
                'type': 'CAPITAL_OUTFLOW',
                'priority': 'HIGH',
                'description': f'近期主力净流出{capital_trend.get("net_inflow", 0) / 10000:.1f}万元',
                'suggestion': '大资金出逃，建议减仓'
            })

        # 5. 五维度综合评分预警
        analysis = self.get_position_analysis(position, current_price)
        total_score = analysis['total_score']

        if total_score < 40:
            signals.append({
                'type': 'LOW_SCORE',
                'priority': 'HIGH',
                'description': f'综合评分仅{total_score:.1f}分，五维度多项指标偏弱',
                'suggestion': '建议重点关注，考虑减仓或清仓'
            })
        elif total_score < 60:
            signals.append({
                'type': 'LOW_SCORE',
                'priority': 'MEDIUM',
                'description': f'综合评分{total_score:.1f}分，低于平均水平',
                'suggestion': '建议保持警惕，设置好止盈止损'
            })

        # 6. 股东户数大幅增加预警
        holder_score = analysis['holder']['score']
        if holder_score < 30:
            signals.append({
                'type': 'HOLDER_INCREASE',
                'priority': 'HIGH',
                'description': '股东户数大幅增加，筹码趋于分散',
                'suggestion': '主力可能已出货，建议谨慎'
            })

        # 7. 新闻情绪预警
        news_score = analysis['news']['score']
        if news_score < 30:
            signals.append({
                'type': 'NEGATIVE_NEWS',
                'priority': 'MEDIUM',
                'description': '近期负面新闻较多，市场情绪偏空',
                'suggestion': '关注公司基本面变化'
            })

        # 8. 价格动量预警
        momentum_score = analysis['momentum']['score']
        if momentum_score < 40:
            signals.append({
                'type': 'WEAK_MOMENTUM',
                'priority': 'MEDIUM',
                'description': '价格动量偏弱，趋势可能反转',
                'suggestion': '关注支撑位，破位建议减仓'
            })

        # 保存信号到数据库
        for sig in signals:
            sell_signal = SellSignal(
                position_id=position.id,
                signal_type=sig['type'],
                trigger_price=current_price,
                description=sig['description'],
                action_suggestion=sig['suggestion'],
                priority=sig['priority']
            )
            self.db.add(sell_signal)

        self.db.commit()

        return signals

    def sell_position(self, position: Position, sell_price: float,
                      sell_reason: str = None):
        """标记为已卖出"""
        position.status = 'sold'
        position.sell_date = datetime.now().date()
        position.sell_price = sell_price
        position.sell_reason = sell_reason

        self.db.commit()

    def reduce_position(self, position: Position, reduce_qty: int, sell_price: float) -> bool:
        """减仓（部分卖出）"""
        try:
            if reduce_qty >= position.quantity:
                # 全部卖出，标记为已卖出
                self.sell_position(position, sell_price, "全部卖出")
                return True
            else:
                # 部分减仓
                position.quantity -= reduce_qty
                # 重新计算盈亏金额（按剩余数量）
                position.profit_amount = (sell_price - position.buy_price) * position.quantity
                self.db.commit()
                return True
        except Exception:
            return False

    def close(self):
        self.db.close()
