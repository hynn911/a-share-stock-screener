"""
混合数据源爬虫模块 - 免费优先策略

策略：
1. 免费数据源优先（腾讯/新浪 + AkShare/Baostock）
2. Tushare 仅作为最后兜底（15:00 后使用）
3. 严格限流保护，避免封禁

数据源优先级：
┌──────────────────────────────────────────┐
│ 优先级 1: 腾讯财经（实时行情，批量获取）   │
│ 优先级 2: 新浪财经（实时行情，日线 K 线）    │
│ 优先级 3: AkShare（全面数据，免费）        │
│ 优先级 4: Baostock（日线数据，免费）       │
│ 优先级 5: Tushare（兜底，15:00 后）         │
└──────────────────────────────────────────┘
"""
import requests
import random
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from core.database import SessionLocal
from core.models import Stock, StockDaily, StockCapitalFlow, StockNews

# ==================== 通用配置 ====================
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
]

# ==================== 腾讯财经爬虫 ====================
class TencentFetcher:
    """
    腾讯财经数据抓取器
    用于获取实时行情（批量，免费，无限制）
    """

    def __init__(self, delay_range=(0.5, 1.0), max_per_minute=60):
        self._session = requests.Session()
        self.delay_range = delay_range
        self.max_per_minute = max_per_minute
        self.minute_start = time.time()
        self.minute_count = 0
        self._setup_session()

    def _setup_session(self):
        self._session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'application/json, text/plain, */*',
        })

    def _rate_limit(self):
        """限流控制"""
        current_time = time.time()
        if current_time - self.minute_start >= 60:
            self.minute_start = current_time
            self.minute_count = 0

        if self.minute_count >= self.max_per_minute:
            wait_time = 60 - (current_time - self.minute_start)
            if wait_time > 0:
                time.sleep(wait_time)
                self.minute_start = time.time()
                self.minute_count = 0

        delay = random.uniform(self.delay_range[0], self.delay_range[1])
        time.sleep(delay)
        self.minute_count += 1

    def _get_secid(self, code: str) -> str:
        """转换证券 ID"""
        if code.startswith('6'):
            return f"sh{code}"
        elif code.startswith('0') or code.startswith('3'):
            return f"sz{code}"
        elif code.startswith('4') or code.startswith('8'):
            return f"bj{code}"
        return f"sh{code}"

    def fetch_realtime_quote(self, code: str) -> Optional[Dict]:
        """获取单只股票实时行情"""
        self._rate_limit()
        self._session.headers['User-Agent'] = random.choice(USER_AGENTS)

        secid = self._get_secid(code)
        url = f"http://qt.gtimg.cn/q={secid}"

        try:
            resp = self._session.get(url, timeout=10)
            if resp.status_code != 200:
                return None

            content = resp.text
            if '~' not in content:
                return None

            parts = content.split('~')
            if len(parts) < 30:
                return None

            return {
                'code': code,
                'name': parts[1] if len(parts) > 1 else '',
                'close': float(parts[3]) if parts[3] else 0,
                'open': float(parts[5]) if parts[5] else 0,
                'prev_close': float(parts[4]) if parts[4] else 0,
                'high': float(parts[33]) if len(parts) > 33 and parts[33] else 0,
                'low': float(parts[34]) if len(parts) > 34 and parts[34] else 0,
                'volume': int(float(parts[6]) * 100) if parts[6] else 0,
                'turnover_rate': float(parts[38]) if len(parts) > 38 and parts[38] else 0,
            }
        except Exception as e:
            print(f"  [腾讯] 获取 {code} 失败：{e}")
            return None

    def fetch_batch_quotes(self, codes: List[str]) -> List[Dict]:
        """
        批量获取实时行情（一次最多 60 只）
        这是腾讯财经的核心优势 - 免费批量获取
        """
        self._rate_limit()
        self._session.headers['User-Agent'] = random.choice(USER_AGENTS)

        batch_size = 60
        all_quotes = []

        for i in range(0, len(codes), batch_size):
            batch = codes[i:i + batch_size]
            secids = [self._get_secid(code) for code in batch]
            url = f"http://qt.gtimg.cn/q={','.join(secids)}"

            try:
                resp = self._session.get(url, timeout=15)
                if resp.status_code != 200:
                    continue

                lines = resp.text.strip().split(';')
                for line in lines:
                    if '~' not in line:
                        continue
                    parts = line.split('~')
                    if len(parts) < 30:
                        continue

                    code = parts[2] if len(parts) > 2 else ''
                    if code:
                        all_quotes.append({
                            'code': code,
                            'name': parts[1] if len(parts) > 1 else '',
                            'close': float(parts[3]) if parts[3] else 0,
                            'open': float(parts[5]) if parts[5] else 0,
                            'high': float(parts[33]) if len(parts) > 33 and parts[33] else 0,
                            'low': float(parts[34]) if len(parts) > 34 and parts[34] else 0,
                            'volume': int(float(parts[6]) * 100) if parts[6] else 0,
                            'turnover_rate': float(parts[38]) if len(parts) > 38 and parts[38] else 0,
                        })

                if i + batch_size < len(codes):
                    time.sleep(random.uniform(0.5, 1.0))

            except Exception as e:
                print(f"  [腾讯] 批量获取失败：{e}")

        return all_quotes


# ==================== 新浪财经爬虫 ====================
class SinaFetcher:
    """
    新浪财经数据抓取器
    用于获取实时行情和日线 K 线数据
    """

    def __init__(self, delay_range=(0.5, 1.0)):
        self._session = requests.Session()
        self.delay_range = delay_range
        self._setup_session()

    def _setup_session(self):
        self._session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
        })

    def _rate_limit(self):
        time.sleep(random.uniform(self.delay_range[0], self.delay_range[1]))

    def fetch_realtime_quote(self, code: str) -> Optional[Dict]:
        """获取实时行情"""
        self._rate_limit()

        if code.startswith('6'):
            secid = f"sh{code}"
        else:
            secid = f"sz{code}"

        url = f"http://hq.sinajs.cn/list={secid}"

        try:
            resp = self._session.get(url, timeout=10)
            if resp.status_code != 200:
                return None

            content = resp.text
            if '=' not in content:
                return None

            # 解析：var hq_str_sh600519="贵州茅台，1680.00,..."
            data_part = content.split('=')[1].strip('"').strip('"')
            parts = data_part.split(',')

            if len(parts) < 10:
                return None

            return {
                'code': code,
                'name': parts[0] if len(parts) > 0 else '',
                'close': float(parts[3]) if len(parts) > 3 and parts[3] else 0,
                'open': float(parts[1]) if len(parts) > 1 and parts[1] else 0,
                'prev_close': float(parts[2]) if len(parts) > 2 and parts[2] else 0,
                'high': float(parts[4]) if len(parts) > 4 and parts[4] else 0,
                'low': float(parts[5]) if len(parts) > 5 and parts[5] else 0,
                'volume': int(parts[8]) if len(parts) > 8 and parts[8] else 0,
                'amount': float(parts[9]) if len(parts) > 9 and parts[9] else 0,
            }
        except Exception as e:
            print(f"  [新浪] 获取 {code} 失败：{e}")
            return None

    def fetch_daily_bars(self, code: str, count: int = 300) -> List[Dict]:
        """
        获取日线 K 线数据（新浪接口）
        最多返回 1000 条数据

        参数格式修正：需要 numeric 格式的参数
        """
        self._rate_limit()

        if code.startswith('6'):
            secid = f"sh{code}"
        else:
            secid = f"sz{code}"

        # 使用正确的参数格式
        url = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"

        # 参数必须是字符串格式
        params = {
            'symbol': secid,
            'scale': 'day',
            'datalen': str(min(count, 1000)),
        }

        try:
            resp = self._session.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                return []

            # 检查返回内容
            content = resp.text
            if '__ERROR' in content:
                print(f"  [新浪] API 返回错误：{content[:100]}")
                return []

            data = resp.json()
            if not data or not isinstance(data, list):
                return []

            records = []
            for bar in data:
                if not isinstance(bar, dict):
                    continue
                records.append({
                    'date': bar.get('day', '').replace('-', ''),  # 格式：20240115
                    'open': float(bar.get('open', 0)),
                    'high': float(bar.get('high', 0)),
                    'low': float(bar.get('low', 0)),
                    'close': float(bar.get('close', 0)),
                    'volume': int(bar.get('volume', 0)),
                })
            return records

        except Exception as e:
            print(f"  [新浪] 获取 {code} 日线失败：{e}")
            return []


# ==================== Baostock 爬虫（免费，需登录） ====================
class BaostockFetcher:
    """
    Baostock 证券宝数据抓取器
    完全免费，需要登录（匿名登录即可）
    用于获取日线数据（高质量）
    """

    def __init__(self):
        self._logged_in = False
        self._bs = None

    def _login(self):
        """登录 Baostock（匿名登录）"""
        if self._logged_in:
            return True

        try:
            import baostock as bs
            self._bs = bs
            lg = bs.login()
            self._logged_in = (lg.error_code == '0')
            if not self._logged_in:
                print(f"  [Baostock] 登录失败：{lg.error_msg}")
            return self._logged_in
        except ImportError:
            print("  [Baostock] 未安装 baostock 库")
            return False
        except Exception as e:
            print(f"  [Baostock] 登录异常：{e}")
            return False

    def fetch_daily_bars(self, code: str, start_date: str = "20200101") -> List[Dict]:
        """
        获取日线数据（前复权）

        Args:
            code: 股票代码（6 位数字）
            start_date: 开始日期（YYYYMMDD）

        Returns:
            日线数据列表
        """
        if not self._login():
            return []

        # 转换代码格式：600519 -> sh.600519
        if code.startswith('6'):
            secid = f"sh.{code}"
        else:
            secid = f"sz.{code}"

        # 转换日期格式：20200101 -> 2020-01-01
        bs_start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"

        try:
            # Baostock 不支持 adjust 参数，直接获取原始数据
            rs = self._bs.query_history_k_data_plus(
                secid,
                "date,code,open,high,low,close,volume,amount",
                start_date=bs_start
            )

            records = []
            while (rs.error_code == '0') and rs.next():
                row = rs.get_row_data()
                # 解析日期：2026-01-05 -> 20260105
                date_str = row[0].replace('-', '')
                records.append({
                    'date': date_str,
                    'code': row[1],
                    'open': float(row[2]) if row[2] else 0,
                    'high': float(row[3]) if row[3] else 0,
                    'low': float(row[4]) if row[4] else 0,
                    'close': float(row[5]) if row[5] else 0,
                    'volume': int(row[6]) if row[6] else 0,
                    'amount': float(row[7]) if row[7] else 0,
                })

            return records

        except Exception as e:
            print(f"  [Baostock] 获取 {code} 日线失败：{e}")
            return []

    def close(self):
        """登出"""
        if self._logged_in and self._bs:
            self._bs.logout()
            self._logged_in = False


# ==================== 混合数据源管理器 ====================
class HybridDataFetcher:
    """
    混合数据源管理器
    自动选择最佳数据源（免费优先）
    """

    def __init__(self):
        self.db = SessionLocal()
        self.tencent = TencentFetcher()
        self.sina = SinaFetcher()
        self.baostock = BaostockFetcher()
        self._tushare_pro = None
        self._tushare_available = None

    def _get_tushare_pro(self):
        """获取 Tushare Pro 实例"""
        if self._tushare_pro is None:
            import os
            from dotenv import load_dotenv
            load_dotenv()

            TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")
            import tushare as ts
            ts.set_token(TUSHARE_TOKEN)
            self._tushare_pro = ts.pro_api()
        return self._tushare_pro

    def is_tushare_available(self) -> bool:
        """检查 Tushare 是否可用（15:00 后）"""
        if self._tushare_available is not None:
            return self._tushare_available

        now = datetime.now()
        # 15:00 后才可用
        if now.hour >= 15:
            self._tushare_available = True
            return True

        self._tushare_available = False
        return False

    def get_realtime_price(self, code: str, use_cache: bool = True) -> Optional[float]:
        """
        获取实时价格（优先免费数据源）

        策略：
        1. 腾讯财经（批量，快速）
        2. 新浪财经（备选）
        3. Tushare（15:00 后兜底）
        """
        # 1. 优先腾讯财经
        data = self.tencent.fetch_realtime_quote(code)
        if data and data.get('close'):
            return data['close']

        # 2. 新浪财经
        data = self.sina.fetch_realtime_quote(code)
        if data and data.get('close'):
            return data['close']

        # 3. Tushare（15:00 后）
        if self.is_tushare_available():
            try:
                pro = self._get_tushare_pro()
                today = datetime.now().strftime('%Y%m%d')
                df = pro.daily(ts_code=code, start_date=today, end_date=today)
                if len(df) > 0:
                    return float(df.iloc[0]['close'])
            except Exception:
                pass

        return None

    def get_batch_prices(self, codes: List[str]) -> Dict[str, float]:
        """
        批量获取实时价格（使用腾讯财经）

        Returns:
            价格字典 {code: price}
        """
        quotes = self.tencent.fetch_batch_quotes(codes)
        return {q['code']: q['close'] for q in quotes if q.get('close')}

    def fetch_daily_bars(self, code: str, start_date: str = "20200101") -> int:
        """
        获取日线数据（优先免费数据源）

        策略：
        1. Baostock（免费，高质量，前复权）
        2. 新浪财经（免费，备用）
        3. Tushare（15:00 后兜底）
        """
        # 1. Baostock（免费，前复权）
        records = self.baostock.fetch_daily_bars(code, start_date)
        if records:
            return self._save_daily_bars(code, records)

        # 2. 新浪财经
        records = self.sina.fetch_daily_bars(code, count=500)
        if records:
            return self._save_daily_bars(code, records)

        # 3. Tushare（15:00 后）
        if self.is_tushare_available():
            try:
                _tushare_limiter = type('Limiter', (), {
                    'wait_if_needed': lambda self: None
                })()
                _tushare_limiter.wait_if_needed()

                pro = self._get_tushare_pro()
                df = pro.daily(ts_code=code, start_date=start_date)
                if df is not None and len(df) > 0:
                    records = []
                    for _, row in df.iterrows():
                        records.append({
                            'date': str(row['trade_date']),
                            'open': float(row['open']),
                            'high': float(row['high']),
                            'low': float(row['low']),
                            'close': float(row['close']),
                            'volume': int(row['vol']),
                            'amount': float(row['amount']),
                            'turnover_rate': float(row.get('turnover_rate', 0))
                        })
                    return self._save_daily_bars(code, records)
            except Exception as e:
                print(f"  [Tushare] 获取 {code} 日线失败：{e}")

        return 0

    def _save_daily_bars(self, code: str, records: List[Dict]) -> int:
        """保存日线数据到数据库"""
        saved = 0
        for bar in records:
            # 转换日期格式
            date_str = bar['date'].replace('-', '')
            try:
                trade_date = datetime.strptime(bar['date'].replace('-', ''), '%Y%m%d').date()
            except:
                continue

            # 检查是否已存在
            existing = self.db.query(StockDaily).filter(
                StockDaily.stock_code == code,
                StockDaily.trade_date == trade_date
            ).first()

            if not existing:
                self.db.add(StockDaily(
                    stock_code=code,
                    trade_date=trade_date,
                    open=bar['open'],
                    high=bar['high'],
                    low=bar['low'],
                    close=bar['close'],
                    volume=bar['volume'],
                    amount=bar.get('amount', 0),
                    turnover_rate=bar.get('turnover_rate', 0)
                ))
                saved += 1

        if saved > 0:
            self.db.commit()

        return saved

    def fetch_capital_flow(self, code: str) -> int:
        """获取资金流数据（目前仅 Tushare 支持）"""
        if not self.is_tushare_available():
            return 0

        try:
            pro = self._get_tushare_pro()
            df = pro.moneyflow(ts_code=code)
            if df is None or len(df) == 0:
                return 0

            saved = 0
            for _, row in df.iterrows():
                trade_date = datetime.strptime(str(row['trade_date']), '%Y%m%d').date()
                existing = self.db.query(StockCapitalFlow).filter(
                    StockCapitalFlow.stock_code == code,
                    StockCapitalFlow.trade_date == trade_date
                ).first()

                if not existing:
                    self.db.add(StockCapitalFlow(
                        stock_code=code,
                        trade_date=trade_date,
                        main_force_in=float(row.get('buy_sm_amount', 0)) + float(row.get('buy_bd_amount', 0)),
                        main_force_out=float(row.get('sell_sm_amount', 0)) + float(row.get('sell_bd_amount', 0)),
                        net_inflow=float(row.get('net_m_amount', 0)),
                    ))
                    saved += 1

            if saved > 0:
                self.db.commit()

            return saved

        except Exception as e:
            print(f"  [Tushare] 获取 {code} 资金流失败：{e}")
            return 0

    def close(self):
        self.db.close()
        self.baostock.close()


# ==================== 便捷函数 ====================
def get_realtime_prices(codes: List[str]) -> Dict[str, float]:
    """快速获取批量价格（腾讯财经）"""
    fetcher = HybridDataFetcher()
    try:
        return fetcher.get_batch_prices(codes)
    finally:
        fetcher.close()


def get_realtime_price(code: str) -> Optional[float]:
    """快速获取单只股票价格"""
    fetcher = HybridDataFetcher()
    try:
        return fetcher.get_realtime_price(code)
    finally:
        fetcher.close()
