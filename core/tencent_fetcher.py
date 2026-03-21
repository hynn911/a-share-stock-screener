"""
腾讯财经数据爬虫模块
作为 Tushare 的补充，可在 15:00 前使用

数据源：腾讯财经 API
- 稳定性：较高（相对东方财富）
- 限流：较宽松
- 数据：实时行情（主）、日线数据（受限）

绕开封禁策略：
1. 随机 User-Agent 轮换
2. 严格控制请求频率（>=2 秒/次）
3. 使用 SESSION 保持连接
4. 与 Tushare 轮换使用
"""
import requests
import time
import random
from datetime import datetime
from typing import Optional, List, Dict
from core.database import SessionLocal
from core.models import Stock, StockDaily, StockCapitalFlow, StockNews


# 多个 User-Agent 轮换，降低被封风险
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
]

# 腾讯财经 API 配置
# 交易所代码：sh=上交所，sz=深交所，bj=北交所
class TencentDataFetcher:
    """腾讯财经数据抓取器 - 限流保护版本"""

    def __init__(self, delay_range=(2.0, 3.0), max_calls_per_minute=20):
        """
        初始化抓取器

        Args:
            delay_range: 请求间隔范围（秒），默认 2-3 秒，避免触发反爬
            max_calls_per_minute: 每分钟最大调用次数
        """
        self.db = SessionLocal()
        self.delay_range = delay_range
        self._session = requests.Session()
        self._setup_session()

        # 限流控制
        self.max_calls_per_minute = max_calls_per_minute
        self.call_count = 0
        self.minute_start = time.time()

        self.call_count = 0
        self.minute_start = time.time()

    def _setup_session(self):
        """配置会话 - 随机 User-Agent"""
        self._session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://quote.eastmoney.com/',
        })

    def _rate_limit(self):
        """限流保护 - 避免再次被封"""
        current_time = time.time()

        # 每分钟检查
        if current_time - self.minute_start >= 60:
            self.minute_start = current_time
            self.call_count = 0
            print(f"  [限流] 重置计数器，当前调用数：{self.call_count}/{self.max_calls_per_minute}")

        # 达到限制则等待
        if self.call_count >= self.max_calls_per_minute:
            wait_time = 60 - (current_time - self.minute_start)
            if wait_time > 0:
                print(f"  [限流] 已达到每分钟{self.max_calls_per_minute}次限制，等待{wait_time:.1f}秒...")
                time.sleep(wait_time)
                self.minute_start = time.time()
                self.call_count = 0

        # 随机延迟（2-3 秒，避免触发反爬）
        delay = random.uniform(self.delay_range[0], self.delay_range[1])
        time.sleep(delay)
        self.call_count += 1

    def _rotate_user_agent(self):
        """轮换 User-Agent"""
        self._session.headers['User-Agent'] = random.choice(USER_AGENTS)

    def _get_secid(self, code: str) -> str:
        """
        获取证券 ID（腾讯格式）

        Args:
            code: 6 位股票代码

        Returns:
            腾讯格式证券 ID，如 'sh600519'
        """
        if code.startswith('6'):
            return f"sh{code}"
        elif code.startswith('0') or code.startswith('3'):
            return f"sz{code}"
        elif code.startswith('4') or code.startswith('8'):
            return f"bj{code}"
        else:
            return f"sh{code}"  # 默认沪市

    def fetch_realtime_quote(self, code: str) -> Optional[Dict]:
        """
        获取实时行情

        Args:
            code: 股票代码

        Returns:
            实时行情数据字典
        """
        secid = self._get_secid(code)
        url = f"http://qt.gtimg.cn/q={secid}"

        try:
            self._random_delay()
            resp = self._session.get(url, timeout=10)
            resp.encoding = 'gbk'  # 腾讯返回 GBK 编码

            if resp.status_code != 200:
                return None

            # 解析返回数据
            # 格式：v_sh600519="51~贵州茅台~600519~1680.00~..."
            content = resp.text.strip()
            if '~' not in content:
                return None

            parts = content.split('~')
            if len(parts) < 50:
                return None

            # 提取关键字段（腾讯字段索引）
            data = {
                'code': code,
                'name': parts[1] if len(parts) > 1 else '',
                'open': float(parts[5]) if parts[5] else 0,
                'prev_close': float(parts[4]) if parts[4] else 0,
                'close': float(parts[3]) if parts[3] else 0,
                'high': float(parts[33]) if parts[33] else 0,
                'low': float(parts[34]) if parts[34] else 0,
                'volume': int(float(parts[6]) * 100) if parts[6] else 0,  # 手 -> 股
                'amount': float(parts[37]) if parts[37] else 0,
                'turnover_rate': float(parts[38]) if parts[38] else 0,
                'total_shares': float(parts[43]) if parts[43] else 0,
                'float_shares': float(parts[44]) if parts[44] else 0,
                'pe_ratio': float(parts[39]) if parts[39] else 0,
                'pb_ratio': float(parts[45]) if parts[45] else 0,
            }

            return data

        except Exception as e:
            print(f"  [腾讯] 获取 {code} 实时行情失败：{e}")
            return None

    def fetch_daily_bars(self, code: str, start_date: str = "20200101") -> int:
        """
        获取日线数据（前复权）

        Args:
            code: 股票代码
            start_date: 开始日期 YYYYMMDD

        Returns:
            获取到的数据条数
        """
        secid = self._get_secid(code)
        # 腾讯财经 K 线 API
        url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        params = {
            "param": f"{secid},,,day,{start_date},",
            "fq": "qfq",  # 前复权
        }

        try:
            self._random_delay()
            resp = self._session.get(url, params=params, timeout=15)

            if resp.status_code != 200:
                print(f"  [腾讯] 获取 {code} 日线失败：状态码 {resp.status_code}")
                return 0

            data = resp.json()

            # 解析数据
            if 'data' not in data:
                return 0

            stock_data = data['data'].get(secid, {})
            qfq_data = stock_data.get('qfqday', [])

            if not qfq_data:
                # 尝试不复权数据
                qfq_data = stock_data.get('day', [])

            if not qfq_data:
                return 0

            records = []
            for bar in qfq_data:
                # bar 格式：[日期，开盘，收盘，最高，最低，成交量，成交额，换手率]
                if len(bar) < 6:
                    continue

                trade_date = bar[0].replace('-', '')
                if trade_date < start_date:
                    continue

                records.append(StockDaily(
                    stock_code=code,
                    trade_date=datetime.strptime(bar[0], '%Y-%m-%d').date(),
                    open=float(bar[1]) if bar[1] else 0,
                    close=float(bar[2]) if bar[2] else 0,
                    high=float(bar[3]) if bar[3] else 0,
                    low=float(bar[4]) if bar[4] else 0,
                    volume=int(float(bar[5]) * 100) if bar[5] else 0,  # 手->股
                    amount=float(bar[6]) if len(bar) > 6 and bar[6] else 0,
                    turnover_rate=float(bar[7]) if len(bar) > 7 and bar[7] else 0,
                ))

            if records:
                # 批量插入或更新
                for record in records:
                    existing = self.db.query(StockDaily).filter(
                        StockDaily.stock_code == record.stock_code,
                        StockDaily.trade_date == record.trade_date
                    ).first()
                    if not existing:
                        self.db.add(record)

                self.db.commit()
                return len(records)

            return 0

        except Exception as e:
            self.db.rollback()
            print(f"  [腾讯] 获取 {code} 日线异常：{e}")
            return 0

    def fetch_capital_flow(self, code: str) -> int:
        """
        获取资金流向数据

        注意：腾讯财经的资金流数据需要 VIP 权限，免费用户可能无法获取
        这里使用简化版本，从实时行情中提取部分数据

        Args:
            code: 股票代码

        Returns:
            获取到的数据条数
        """
        # 腾讯财经没有免费的资金流接口
        # 返回 0，表示无法获取
        # 实际使用建议用 Tushare
        return 0

    def fetch_stock_news(self, code: str) -> int:
        """
        获取个股新闻

        腾讯财经新闻接口返回格式特殊，暂不实现
        建议使用 Tushare

        Returns:
            0（未实现）
        """
        return 0

    def fetch_all_stocks(self) -> int:
        """
        获取全部 A 股列表

        通过遍历获取所有股票（用于首次建仓）

        Returns:
            获取到的股票数量
        """
        all_stocks = []

        # 腾讯不支持直接获取全部列表，需要通过其他方式
        # 这里返回 0，建议使用 Tushare 获取股票列表
        return 0

    def close(self):
        """关闭连接"""
        self.db.close()
        self._session.close()


# 便捷函数
def get_realtime_price(code: str) -> Optional[float]:
    """快速获取实时价格"""
    fetcher = TencentDataFetcher()
    try:
        data = fetcher.fetch_realtime_quote(code)
        return data.get('close') if data else None
    finally:
        fetcher.close()


def get_daily_history(code: str, start_date: str = "20240101") -> int:
    """快速获取日线历史"""
    fetcher = TencentDataFetcher()
    try:
        return fetcher.fetch_daily_bars(code, start_date)
    finally:
        fetcher.close()
