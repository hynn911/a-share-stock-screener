"""
热词分析模块 - 市场热点检测
"""
import jieba
from collections import Counter
from datetime import datetime, timedelta
from core.database import SessionLocal
from core.models import HotWord, StockNews
from sqlalchemy import desc


class HotWordAnalyzer:
    """热词分析器"""

    # 股票相关词典
    STOCK_KEYWORDS = [
        '涨停', '跌停', '拉升', '跳水', '突破', '回调',
        '利好', '利空', '重组', '收购', '并购', '定增',
        '业绩', '财报', '分红', '配股', '减持', '增持',
        '龙头', '板块', '概念', '题材', '热点'
    ]

    # 行业/概念关键词分类
    SECTOR_KEYWORDS = {
        '芯片半导体': ['芯片', '半导体', '集成电路', '晶圆', '光刻机', 'EDA', '封装', '测试', '中芯国际', '台积电'],
        '人工智能': ['人工智能', 'AI', '大模型', '机器学习', '深度学习', 'NLP', 'AIGC', 'ChatGPT', '智谱'],
        '新能源': ['新能源', '光伏', '风电', '锂电', '电池', '储能', '氢能', '宁德时代', '比亚迪'],
        '医药生物': ['医药', '生物', '疫苗', '创新药', '医疗器械', '中药', 'CXO', '恒瑞医药'],
        '大消费': ['消费', '白酒', '食品', '零售', '家电', '汽车', '贵州茅台', '五粮液'],
        '金融': ['金融', '银行', '保险', '券商', '信托', '证券'],
        '科技': ['科技', '互联网', '软件', '云计算', '大数据', '物联网', '5G', '通信'],
        '军工': ['军工', '航空', '航天', '国防', '武器', '战斗机', '航母'],
        '房地产': ['房地产', '楼市', '物业', '建材', '万科'],
        '基建': ['基建', '建筑', '工程', '水泥', '钢铁', '高铁', '桥梁'],
        '有色金属': ['有色', '黄金', '白银', '铜', '铝', '锌', '铅', '镍', '钴', '稀土', '锂矿', '紫金矿业'],
        '石油石化': ['石油', '石化', '原油', '天然气', '中海油', '中石油', '中石化'],
        '煤炭': ['煤炭', '焦煤', '动力煤', '中国神华'],
        '农业': ['农业', '养殖', '种植', '猪肉', '鸡肉', '牧原股份', '温氏股份'],
        '电子': ['电子', '消费电子', '元器件', '面板', 'LED', '立讯精密', '京东方'],
        '机械': ['机械', '机器人', '自动化', '工程机械', '三一重工'],
        '交通': ['交通', '物流', '快递', '航空', '机场', '港口', '高速公路'],
        '传媒': ['传媒', '游戏', '影视', '广告', '出版', '抖音', '快手'],
        '纺织': ['纺织', '服装', '家纺', '耐克', '安踏'],
        '化工': ['化工', '化肥', '农药', '塑料', '橡胶', '万华化学']
    }

    # 政策相关关键词
    POLICY_KEYWORDS = {
        '碳中和': ['碳中和', '碳达峰', '减排', '绿色低碳'],
        '国产替代': ['国产替代', '自主可控', '卡脖子', '核心技术'],
        '数字经济': ['数字经济', '数字化', '智能化', '工业互联网'],
        '乡村振兴': ['乡村振兴', '农业', '农村', '扶贫']
    }

    def __init__(self):
        # 添加股票词典
        for word in self.STOCK_KEYWORDS:
            jieba.add_word(word)

        self.db = SessionLocal()

    def analyze_news(self, text: str) -> list:
        """从新闻中提取关键词"""
        # 分词
        words = jieba.lcut(text)

        # 过滤停用词和短词
        stopwords = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '中', '为', '以', '等', '及', '与', '或', '其', '但', '而', '之', '把', '被', '让', '给', '向', '从', '到', '对', '关于', '作为'}
        words = [w for w in words if len(w) > 1 and w not in stopwords]

        return words

    def classify_hot_words(self, hot_words: list) -> dict:
        """将热词按行业/概念分类"""
        result = {
            'sectors': {},  # 行业热点
            'policies': {},  # 政策热点
            'others': []  # 其他热词
        }

        for hw in hot_words:
            word = hw['word']
            score = hw['hot_score']

            # 检查行业分类
            categorized = False
            for sector, keywords in self.SECTOR_KEYWORDS.items():
                if word in keywords or any(k in word for k in keywords):
                    if sector not in result['sectors']:
                        result['sectors'][sector] = []
                    result['sectors'][sector].append({'word': word, 'score': score})
                    categorized = True
                    break

            # 检查政策分类
            if not categorized:
                for policy, keywords in self.POLICY_KEYWORDS.items():
                    if word in keywords or any(k in word for k in keywords):
                        if policy not in result['policies']:
                            result['policies'][policy] = []
                        result['policies'][policy].append({'word': word, 'score': score})
                        categorized = True
                        break

            # 未分类的放入其他
            if not categorized:
                result['others'].append({'word': word, 'score': score})

        return result

    def get_hot_words(self, days: int = 3, top_n: int = 50) -> list:
        """获取热词 Top N"""
        # 获取最近 N 天的新闻
        cutoff_date = datetime.now() - timedelta(days=days)

        news_list = self.db.query(StockNews).filter(
            StockNews.publish_time >= cutoff_date
        ).all()

        # 提取所有词
        all_words = []
        word_dates = {}

        for news in news_list:
            title_words = self.analyze_news(news.title)
            content_words = self.analyze_news(news.content) if news.content else []

            # 标题词权重更高（x2）
            for w in title_words:
                all_words.append(w)
                all_words.append(w)  # 标题词算两次

            for w in content_words:
                all_words.append(w)

            # 记录词的最新日期
            for w in title_words + content_words:
                if w not in word_dates:
                    word_dates[w] = news.publish_time
                else:
                    word_dates[w] = max(word_dates[w], news.publish_time)

        # 统计词频
        word_counts = Counter(all_words)

        # 计算热度分数（考虑时效性）
        now = datetime.now()
        hot_words = []
        for word, count in word_counts.most_common(top_n * 2):  # 多取一些，后面会过滤
            if count < 2:  # 至少出现 2 次
                continue

            # 时效性加权（越近越热）
            if word in word_dates:
                days_ago = (now - word_dates[word]).days
                time_weight = 1.0 / (days_ago + 1)  # 当天=1, 1 天前=0.5, 2 天前=0.33
            else:
                time_weight = 1.0

            hot_score = count * time_weight

            hot_words.append({
                'word': word,
                'count': count,
                'hot_score': round(hot_score, 2)
            })

        # 按热度分数排序
        hot_words.sort(key=lambda x: x['hot_score'], reverse=True)

        return hot_words[:top_n]

    def get_hot_sectors(self, days: int = 3, top_n: int = 10) -> list:
        """获取热门行业/概念 Top N"""
        hot_words = self.get_hot_words(days, top_n=100)
        classified = self.classify_hot_words(hot_words)

        # 计算行业热度
        sector_scores = []
        for sector, words in classified['sectors'].items():
            total_score = sum(w['score'] for w in words)
            sector_scores.append({
                'sector': sector,
                'hot_score': round(total_score, 2),
                'word_count': len(words),
                'top_words': [w['word'] for w in words[:5]]
            })

        sector_scores.sort(key=lambda x: x['hot_score'], reverse=True)
        return sector_scores[:top_n]

    def get_sector_stocks(self, sector_name: str, limit: int = 20) -> list:
        """获取特定板块相关的股票"""
        from core.models import Stock
        from sqlalchemy import or_

        # 获取该板块的关键词
        keywords = self.SECTOR_KEYWORDS.get(sector_name, [])
        if not keywords:
            return []

        # 构建搜索条件
        conditions = []
        for kw in keywords:
            conditions.append(Stock.name.like(f'%{kw}%'))
            conditions.append(Stock.code.like(f'%{kw}%'))

        if not conditions:
            return []

        # 查询相关股票
        stocks = self.db.query(Stock).filter(
            or_(*conditions)
        ).limit(limit).all()

        return [{
            'stock_code': s.code,
            'stock_name': s.name,
            'industry': s.industry if hasattr(s, 'industry') else ''
        } for s in stocks]

    def get_all_sectors_with_stocks(self, days: int = 3, top_n: int = 10) -> list:
        """获取所有热门板块及其相关股票"""
        hot_sectors = self.get_hot_sectors(days, top_n)

        result = []
        for sector_info in hot_sectors:
            sector_name = sector_info['sector']
            stocks = self.get_sector_stocks(sector_name)

            result.append({
                'sector': sector_name,
                'hot_score': sector_info['hot_score'],
                'top_words': sector_info['top_words'],
                'stock_count': len(stocks),
                'stocks': stocks[:10]  # 只显示前 10 只
            })

        return result

    def save_hot_words(self, hot_words: list, source: str = "news"):
        """保存热词到数据库"""
        records = []
        for hw in hot_words:
            records.append(HotWord(
                word=hw['word'],
                source=source,
                hot_score=hw['hot_score']
            ))

        self.db.add_all(records)
        self.db.commit()

    def close(self):
        self.db.close()
