# -*- coding: utf-8 -*-
"""
热门板块分析 - 板块热度、龙头股识别、荐股分析
"""
from core.database import SessionLocal
from core.models import Stock, StockDaily, StockCapitalFlow, StockNews, StockHolderCount
from core.capital import CapitalAnalyzer
from core.stock_scorer import StockScorer
from core.hot_words import HotWordAnalyzer
from sqlalchemy import desc, func, and_
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
import jieba


class SectorAnalyzer:
    """
    板块分析器

    功能:
    1. 识别热门板块
    2. 筛选板块内龙头股票
    3. 热点股票综合荐股分析
    """

    # 行业/概念板块映射
    SECTOR_MAPPING = {
        # 新能源相关
        '新能源': ['新能源', '光伏', '风电', '锂电', '电池', '储能', '氢能', '核电'],
        '芯片半导体': ['芯片', '半导体', '集成电路', '晶圆', '光刻机', 'EDA', '电子'],

        # 科技相关
        'AI 人工智能': ['人工智能', 'AI', '大模型', '机器学习', '深度学习', 'NLP', '智能'],
        '云计算': ['云计算', '云服务', 'SaaS', 'PaaS', '数据中心'],
        '大数据': ['大数据', '数据分析', '数据服务'],
        '物联网': ['物联网', 'IoT', '传感器', 'RFID'],
        '5G 通信': ['5G', '通信', '基站', '光模块', '光纤'],
        '消费电子': ['消费电子', '手机', '可穿戴', 'VR', 'AR', 'MR'],

        # 医药健康
        '医药生物': ['医药', '生物', '疫苗', '创新药', '医疗器械', '中药', '医疗服务'],
        '医疗器械': ['医疗器械', '医疗设备', '诊断'],

        # 大消费
        '白酒': ['白酒', '酒业'],
        '食品饮料': ['食品', '饮料', '乳制品', '调味品', '零食'],
        '家电': ['家电', '智能家居'],
        '汽车': ['汽车', '整车', '零部件', '特斯拉'],
        '新能源汽车': ['新能源汽车', '电动车', '比亚迪', '特斯拉'],

        # 金融
        '银行': ['银行'],
        '证券': ['证券', '券商'],
        '保险': ['保险'],
        '多元金融': ['信托', '期货', '金融科技'],

        # 周期股
        '房地产': ['房地产', '物业', '房企'],
        '建材': ['建材', '水泥', '玻璃', '陶瓷'],
        '基建': ['基建', '建筑', '工程', '路桥'],
        '钢铁': ['钢铁', '钢材'],
        '煤炭': ['煤炭', '焦煤'],
        '有色金属': ['有色金属', '铜', '铝', '锌', '锂', '钴', '稀土', '黄金'],
        '石油石化': ['石油', '石化', '油气', '炼化'],
        '化工': ['化工', '化肥', '农药', '塑料', '橡胶'],

        # 军工
        '军工': ['军工', '航空', '航天', '国防', '武器', '船舶'],

        # 其他
        '传媒游戏': ['传媒', '游戏', '影视', '广告', '出版'],
        '纺织服装': ['纺织', '服装', '家纺'],
        '轻工制造': ['轻工', '家具', '造纸', '包装'],
        '交通运输': ['物流', '快递', '航空', '港口', '高速'],
        '农林牧渔': ['农业', '林业', '畜牧', '渔业', '饲料'],
        '商贸零售': ['零售', '电商', '百货', '超市'],
        '环保': ['环保', '污水处理', '大气治理', '固废'],
        '公用事业': ['电力', '水务', '燃气'],
    }

    def __init__(self):
        self.db = SessionLocal()
        self.hot_word_analyzer = HotWordAnalyzer()
        self.capital_analyzer = CapitalAnalyzer()
        self.stock_scorer = StockScorer()

    def get_sector_stocks(self, sector_name: str) -> List[Dict]:
        """获取板块内的所有股票"""
        keywords = self.SECTOR_MAPPING.get(sector_name, [sector_name])

        # 构建查询条件
        conditions = []
        for kw in keywords:
            conditions.append(Stock.concept.like(f"%{kw}%"))
            conditions.append(Stock.industry.like(f"%{kw}%"))

        if not conditions:
            return []

        stocks = self.db.query(Stock).filter(
            and_(True, *conditions)  # type: ignore
        ).all()

        return [
            {
                'code': s.code,
                'name': s.name,
                'industry': s.industry,
                'concept': s.concept
            }
            for s in stocks
        ]

    def calculate_sector_heat(self, sector_name: str, days: int = 5) -> Dict:
        """
        计算板块热度

        维度:
        - 新闻热度：板块相关新闻数量、情绪
        - 资金热度：板块资金净流入
        - 价格动量：板块平均涨幅
        - 涨停数量：板块内涨停股票数
        """
        stocks = self.get_sector_stocks(sector_name)

        if not stocks:
            return {
                'sector': sector_name,
                'heat_score': 0,
                'stock_count': 0,
                'details': {}
            }

        stock_codes = [s['code'] for s in stocks]
        cutoff_date = datetime.now().date() - timedelta(days=days)

        # 1. 新闻热度
        news_query = self.db.query(
            StockNews.stock_code,
            func.count(StockNews.id).label('news_count'),
            func.avg(StockNews.sentiment_score).label('avg_sentiment')
        ).filter(
            StockNews.stock_code.in_(stock_codes),
            StockNews.publish_time >= datetime.now() - timedelta(days=days)
        ).group_by(StockNews.stock_code).all()

        total_news = sum(n.news_count for n in news_query)
        avg_sentiment = sum(n.avg_sentiment * n.news_count for n in news_query) / max(total_news, 1)

        # 2. 资金热度
        flow_query = self.db.query(
            StockCapitalFlow.stock_code,
            func.sum(StockCapitalFlow.net_inflow).label('total_net_inflow')
        ).filter(
            StockCapitalFlow.stock_code.in_(stock_codes),
            StockCapitalFlow.trade_date >= cutoff_date
        ).group_by(StockCapitalFlow.stock_code).all()

        total_net_inflow = sum(f.total_net_inflow or 0 for f in flow_query)

        # 3. 价格动量
        price_data = self.db.query(
            StockDaily.stock_code,
            StockDaily.close,
            StockDaily.trade_date
        ).filter(
            StockDaily.stock_code.in_(stock_codes)
        ).order_by(desc(StockDaily.trade_date)).all()

        # 计算每只股票的 5 日涨幅
        stock_prices = defaultdict(list)
        for pd in price_data:
            stock_prices[pd.stock_code].append(pd.close)

        changes = []
        limit_up_count = 0
        for code, prices in stock_prices.items():
            if len(prices) >= 2:
                change = (prices[0] - prices[-1]) / prices[-1] * 100
                changes.append(change)
                # 涨停判断 (10% 以上)
                if change >= 9.5:
                    limit_up_count += 1

        avg_change = sum(changes) / max(len(changes), 1)

        # 4. 综合热度分数 (0-100)
        news_score = min(total_news / 10, 25) * (1 + avg_sentiment)  # 0-50
        capital_score = min(max(total_net_inflow / 10000000, 0), 25)  # 0-25 (1 亿以上满分)
        momentum_score = min(max(avg_change + 10, 0), 25)  # 0-25
        limit_up_score = min(limit_up_count * 5, 25)  # 0-25

        heat_score = news_score + capital_score + momentum_score + limit_up_score

        return {
            'sector': sector_name,
            'heat_score': round(heat_score, 2),
            'stock_count': len(stocks),
            'details': {
                'news_score': round(news_score, 2),
                'capital_score': round(capital_score, 2),
                'momentum_score': round(momentum_score, 2),
                'limit_up_score': round(limit_up_score, 2),
                'total_news': total_news,
                'avg_sentiment': round(avg_sentiment, 3),
                'total_net_inflow': round(total_net_inflow, 0),
                'avg_price_change': round(avg_change, 2),
                'limit_up_count': limit_up_count
            }
        }

    def get_hot_sectors(self, top_n: int = 10, days: int = 5) -> List[Dict]:
        """获取热门板块 Top N"""
        all_sectors = []

        for sector_name in self.SECTOR_MAPPING.keys():
            heat_data = self.calculate_sector_heat(sector_name, days)
            if heat_data['stock_count'] > 0:
                all_sectors.append(heat_data)

        # 按热度排序
        all_sectors.sort(key=lambda x: x['heat_score'], reverse=True)

        return all_sectors[:top_n]

    def identify_sector_leaders(self, sector_name: str, top_n: int = 5) -> List[Dict]:
        """
        识别板块内龙头股票

        筛选维度:
        - 市值 (用成交额近似)
        - 涨幅
        - 资金流入
        - 涨停次数
        - 行业地位
        """
        stocks = self.get_sector_stocks(sector_name)

        if not stocks:
            return []

        stock_codes = [s['code'] for s in stocks]
        cutoff_date = datetime.now().date() - timedelta(days=10)

        leaders = []

        for stock in stocks:
            code = stock['code']

            # 1. 获取成交金额
            amount_data = self.db.query(
                func.sum(StockDaily.amount).label('total_amount')
            ).filter(
                StockDaily.stock_code == code,
                StockDaily.trade_date >= cutoff_date
            ).scalar()

            # 2. 获取涨幅
            price_data = self.db.query(
                StockDaily.close
            ).filter(
                StockDaily.stock_code == code
            ).order_by(desc(StockDaily.trade_date)).limit(10).all()

            if len(price_data) >= 2:
                price_change = (price_data[0][0] - price_data[-1][0]) / price_data[-1][0] * 100
            else:
                price_change = 0

            # 3. 获取资金流入
            flow_data = self.db.query(
                func.sum(StockCapitalFlow.net_inflow).label('total_inflow')
            ).filter(
                StockCapitalFlow.stock_code == code,
                StockCapitalFlow.trade_date >= cutoff_date
            ).scalar()

            # 4. 涨停次数
            limit_up_days = self.db.query(
                func.count(StockDaily.id)
            ).filter(
                StockDaily.stock_code == code,
                StockDaily.trade_date >= cutoff_date,
                StockDaily.close / func.lag(StockDaily.close).over(
                    order_by=desc(StockDaily.trade_date)
                ) >= 1.095
            ).scalar()

            # 5. 综合评分
            score = 0
            score += min((amount_data or 0) / 100000000, 30)  # 成交额 30 亿满分
            score += min(max(price_change, 0), 30)  # 涨幅 30 分满分
            score += min(max((flow_data or 0) / 10000000, 0), 25)  # 资金 25 分满分
            score += min((limit_up_days or 0) * 5, 15)  # 涨停 15 分满分

            leaders.append({
                'code': code,
                'name': stock['name'],
                'score': round(score, 2),
                'details': {
                    'total_amount': amount_data or 0,
                    'price_change': round(price_change, 2),
                    'net_inflow': flow_data or 0,
                    'limit_up_days': limit_up_days or 0,
                    'industry': stock['industry'],
                    'concept': stock['concept']
                }
            })

        # 按评分排序
        leaders.sort(key=lambda x: x['score'], reverse=True)

        return leaders[:top_n]

    def get_stock_recommendation(self, stock_code: str) -> Optional[Dict]:
        """
        单只股票的综合荐股分析

        整合所有分析指标:
        - 资金流
        - 技术指标
        - 股东户数
        - 新闻情绪
        - 板块热度
        """
        stock = self.db.query(Stock).filter(Stock.code == stock_code).first()
        if not stock:
            return None

        # 使用 StockScorer 获取各维度评分
        analysis = self.stock_scorer.get_stock_analysis(stock_code)

        if not analysis:
            return None

        # 获取所属板块
        sectors = []
        for sector_name, keywords in self.SECTOR_MAPPING.items():
            concept = stock.concept or ''
            industry = stock.industry or ''
            for kw in keywords:
                if kw in concept or kw in industry:
                    sectors.append(sector_name)
                    break

        # 获取板块热度
        sector_heat = {}
        for sector in sectors[:3]:  # 只看前 3 个板块
            heat = self.calculate_sector_heat(sector, days=5)
            sector_heat[sector] = heat['heat_score']

        # 综合推荐评级
        total_score = analysis['total_score']
        sector_bonus = max(sector_heat.values()) / 100 * 10 if sector_heat else 0
        final_score = min(total_score + sector_bonus, 100)

        if final_score >= 85:
            rating = '强烈推荐'
        elif final_score >= 70:
            rating = '推荐'
        elif final_score >= 55:
            rating = '谨慎推荐'
        else:
            rating = '观望'

        return {
            'stock_code': stock_code,
            'stock_name': stock.name,
            'industry': stock.industry,
            'concept': stock.concept,
            'sectors': sectors,
            'sector_heat': sector_heat,
            'scores': analysis['scores'],
            'total_score': round(total_score, 2),
            'final_score': round(final_score, 2),
            'rating': rating,
            'details': analysis['details'],
            'analysis_time': datetime.now().isoformat()
        }

    def get_hot_sector_stocks(self, top_n: int = 20) -> List[Dict]:
        """
        获取热门板块中的热门股票

        综合筛选:
        1. 属于热门板块
        2. 个股评分高
        3. 资金流入
        4. 技术面好
        """
        # 获取热门板块
        hot_sectors = self.get_hot_sectors(top_n=5, days=5)

        candidates = []

        for sector in hot_sectors:
            leaders = self.identify_sector_leaders(sector['sector'], top_n=10)
            for leader in leaders:
                # 获取综合评分
                analysis = self.stock_scorer.get_stock_analysis(leader['code'])
                if analysis and analysis['total_score'] >= 60:
                    candidates.append({
                        **leader,
                        'total_score': analysis['total_score'],
                        'sector': sector['sector'],
                        'sector_heat': sector['heat_score']
                    })

        # 按综合评分排序
        candidates.sort(key=lambda x: x['total_score'], reverse=True)

        return candidates[:top_n]

    def get_sector_comparison(self, sector_names: List[str]) -> Dict:
        """比较多个板块的热度和指标"""
        comparison = {}

        for sector_name in sector_names:
            heat_data = self.calculate_sector_heat(sector_name)
            leaders = self.identify_sector_leaders(sector_name, top_n=3)
            comparison[sector_name] = {
                'heat_data': heat_data,
                'top_leaders': leaders
            }

        return comparison

    def close(self):
        self.db.close()
        self.hot_word_analyzer.close()
        self.capital_analyzer.close()
        self.stock_scorer.close()
