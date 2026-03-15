"""
大宗商品价格监控模块
数据来源：akshare 期货现货价格 API
"""
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from core.database import SessionLocal
from core.models import CommodityPrice


class CommodityMonitor:
    """大宗商品价格监控器"""

    # 期货合约代码到中文名称的映射
    SYMBOL_TO_CHINESE = {
        # 农产品
        "C": "玉米",
        "A": "豆一",
        "M": "豆粕",
        "Y": "豆油",
        "P": "棕榈油",
        "JD": "鸡蛋",
        "L": "塑料",
        "V": "PVC",
        "PP": "聚丙烯",
        "EB": "苯乙烯",
        "EG": "乙二醇",
        "PG": "丙烷",
        "LH": "生猪",
        "WH": "强麦",
        "PM": "普麦",
        "CF": "棉花",
        "SR": "白糖",
        "TA": "PTA",
        "OI": "菜油",
        "MA": "甲醇",
        "FG": "玻璃",
        "RM": "菜粕",
        "SF": "硅铁",
        "SM": "硅锰",
        "CY": "棉纱",
        "UR": "尿素",
        "SA": "纯碱",
        "PF": "短纤",
        "PX": "对二甲苯",
        "SH": "烧碱",
        # 有色金属
        "CU": "沪铜",
        "AL": "沪铝",
        "ZN": "沪锌",
        "PB": "沪铅",
        "NI": "沪镍",
        "SN": "沪锡",
        "BR": "碳酸锂",
        "SI": "工业硅",
        "LC": "锂碳",
        # 贵金属
        "AU": "黄金",
        "AG": "白银",
        # 黑色系
        "RB": "螺纹钢",
        "WR": "线材",
        "HC": "热卷",
        "I": "铁矿石",
        "J": "焦炭",
        "JM": "焦煤",
        "FU": "燃油",
        "SS": "不锈钢",
        # 能源化工
        "SC": "原油",
        "BU": "沥青",
        "RU": "橡胶",
        "SP": "纸浆",
    }

    # 重点关注的大宗商品列表
    KEY_COMMODITIES = [
        "铜", "铝", "锌", "铅", "镍", "锡",  # 有色金属
        "黄金", "白银",  # 贵金属
        "原油", "燃油", "液化天然气",  # 能源
        "螺纹钢", "热卷", "铁矿石", "焦炭", "焦煤",  # 黑色系
        "棉花", "白糖", "豆粕", "豆油", "棕榈油",  # 农产品
        "生猪", "玉米", "大豆",  # 粮食
    ]

    def __init__(self):
        self.db = SessionLocal()

    def get_chinese_name(self, symbol: str) -> str:
        """将期货合约代码转换为中文名称"""
        # 如果已经是中文，直接返回
        if any('\u4e00' <= c <= '\u9fff' for c in symbol):
            return symbol
        # 如果是英文代码，查表转换
        return self.SYMBOL_TO_CHINESE.get(symbol, symbol)

    def fetch_commodity_prices(self) -> pd.DataFrame:
        """获取最新的大宗商品现货价格"""
        try:
            # 获取期货现货价格数据
            data = ak.futures_spot_price()
            if data is None or data.empty:
                return pd.DataFrame()

            # 数据清洗
            data['trade_date'] = pd.to_datetime(data['date'], format='%Y%m%d')
            data['trade_date'] = data['trade_date'].dt.date

            # 重命名以便理解
            data = data.rename(columns={
                'symbol': 'commodity_name',
                'spot_price': 'spot_price',
                'near_contract': 'near_contract',
                'near_contract_price': 'near_contract_price',
                'dominant_contract': 'dominant_contract',
                'dominant_contract_price': 'dominant_contract_price'
            })

            return data
        except Exception:
            return pd.DataFrame()

    def fetch_previous_prices(self) -> pd.DataFrame:
        """获取历史价格及涨跌幅数据"""
        try:
            data = ak.futures_spot_price_previous()
            if data is None or data.empty:
                return pd.DataFrame()

            # 由于编码问题，使用列索引而不是列名
            # 列顺序：品名，现货价格，近月合约，主力合约价格，主力合约，近月合约变动百分比，180 日最高，180 日最低，180 日平均
            if len(data.columns) >= 6:
                data.columns = ['commodity_name', 'spot_price', 'near_contract',
                               'dominant_contract_price', 'dominant_contract',
                               'price_change_pct', '180d_high', '180d_low', '180d_avg']

            return data
        except Exception:
            return pd.DataFrame()

    def calculate_price_changes(self, current_data: pd.DataFrame) -> pd.DataFrame:
        """计算价格涨跌幅"""
        if current_data.empty:
            return current_data

        # 计算涨跌幅 (如果有主力合约价格变动数据)
        if 'dom_basis_rate' in current_data.columns:
            # 使用基差变动率作为参考
            current_data['price_change_1d'] = current_data.get('dom_basis_rate', 0) * 100

        return current_data

    def get_commodities_with_alert(self, threshold: float = 10.0) -> List[Dict]:
        """获取涨跌幅超过阈值的大宗商品"""
        alerts = []

        try:
            # 获取当前价格
            current_data = self.fetch_commodity_prices()
            if current_data.empty:
                return alerts

            # 使用当前数据的 dom_basis_rate 作为涨跌幅参考
            for _, row in current_data.iterrows():
                commodity_name = row.get('commodity_name', '')
                # 获取中文名称
                chinese_name = self.get_chinese_name(commodity_name)

                # 检查是否在关注列表中
                is_key = any(key in chinese_name for key in self.KEY_COMMODITIES)

                # 计算涨跌幅 - 使用 dom_basis_rate 作为参考
                price_change = 0.0
                if 'dom_basis_rate' in row and pd.notna(row['dom_basis_rate']):
                    try:
                        price_change = float(row['dom_basis_rate']) * 100
                    except (ValueError, TypeError):
                        price_change = 0.0

                # 检查是否超过阈值
                if abs(price_change) >= threshold:
                    alerts.append({
                        'commodity_name': commodity_name,
                        'chinese_name': chinese_name,
                        'spot_price': row.get('spot_price', 0),
                        'price_change': price_change,
                        'is_key_commodity': is_key,
                        'trade_date': datetime.now().date()
                    })

            # 按涨跌幅排序
            alerts.sort(key=lambda x: abs(x['price_change']), reverse=True)

        except Exception:
            pass

        return alerts

    def get_all_commodities_summary(self) -> List[Dict]:
        """获取所有大宗商品价格摘要"""
        summaries = []

        try:
            current_data = self.fetch_commodity_prices()
            if current_data.empty:
                return summaries

            for _, row in current_data.iterrows():
                commodity_name = row.get('commodity_name', '')
                # 获取中文名称
                chinese_name = self.get_chinese_name(commodity_name)

                # 使用 dom_basis_rate 作为涨跌幅
                price_change_1d = 0.0
                if 'dom_basis_rate' in row and pd.notna(row['dom_basis_rate']):
                    try:
                        price_change_1d = float(row['dom_basis_rate']) * 100
                    except (ValueError, TypeError):
                        price_change_1d = 0.0

                summaries.append({
                    'commodity_name': commodity_name,
                    'chinese_name': chinese_name,
                    'spot_price': row.get('spot_price', 0),
                    'near_contract': row.get('near_contract', ''),
                    'near_contract_price': row.get('near_contract_price', 0),
                    'dominant_contract': row.get('dominant_contract', ''),
                    'dominant_contract_price': row.get('dominant_contract_price', 0),
                    'price_change_1d': price_change_1d,
                    'is_key_commodity': any(k in chinese_name for k in self.KEY_COMMODITIES)
                })

            # 按涨跌幅排序
            summaries.sort(key=lambda x: abs(x['price_change_1d']), reverse=True)

        except Exception:
            pass

        return summaries

    def close(self):
        """关闭数据库连接"""
        self.db.close()


def get_commodity_alerts(threshold: float = 10.0) -> List[Dict]:
    """便捷函数：获取大宗商品价格预警"""
    monitor = CommodityMonitor()
    try:
        return monitor.get_commodities_with_alert(threshold)
    finally:
        monitor.close()


def get_commodity_summary() -> List[Dict]:
    """便捷函数：获取大宗商品价格摘要"""
    monitor = CommodityMonitor()
    try:
        return monitor.get_all_commodities_summary()
    finally:
        monitor.close()


def format_alert_text(alerts: List[Dict], threshold: float = 10.0) -> str:
    """
    格式化预警信息为易读的中文文本

    Args:
        alerts: 预警列表
        threshold: 预警阈值

    Returns:
        格式化的中文预警文本
    """
    if not alerts:
        return f"[OK] 暂无涨跌幅超过 {threshold}% 的大宗商品"

    lines = []
    lines.append(f"[ALERT] 大宗商品价格预警 (涨跌幅 > {threshold}%)")
    lines.append("=" * 60)

    # 分类：上涨和下跌
    gainers = [a for a in alerts if a['price_change'] > 0]
    losers = [a for a in alerts if a['price_change'] < 0]

    if gainers:
        lines.append(f"\n[上涨] {len(gainers)} 个商品:")
        lines.append("-" * 40)
        for alert in sorted(gainers, key=lambda x: x['price_change'], reverse=True):
            symbol = "[重点]" if alert['is_key_commodity'] else "      "
            lines.append(f"{symbol} {alert['commodity_name']}: {alert['spot_price']:.2f} (+{alert['price_change']:.2f}%)")

    if losers:
        lines.append(f"\n[下跌] {len(losers)} 个商品:")
        lines.append("-" * 40)
        for alert in sorted(losers, key=lambda x: x['price_change']):
            symbol = "[重点]" if alert['is_key_commodity'] else "      "
            lines.append(f"{symbol} {alert['commodity_name']}: {alert['spot_price']:.2f} ({alert['price_change']:.2f}%)")

    lines.append("=" * 60)
    lines.append(f"共 {len(alerts)} 个商品触发预警")

    return "\n".join(lines)
