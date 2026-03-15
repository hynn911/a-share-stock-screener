"""
技术指标计算 - 完整专业版
包含：均线、MACD、RSI、KDJ、布林带、EMA、SAR、ADX、ATR、OBV、CCI 等
"""
import pandas as pd
import pandas_ta as ta
from core.database import SessionLocal
from core.models import StockDaily
from sqlalchemy import and_
from typing import Dict, List, Optional
import numpy as np


class IndicatorCalculator:
    """技术指标计算器 - 专业版"""

    def get_stock_data(self, stock_code: str, days: int = 120) -> pd.DataFrame:
        """获取股票历史数据（默认 120 天用于计算长期指标）"""
        db = SessionLocal()
        data = db.query(StockDaily).filter(
            StockDaily.stock_code == stock_code
        ).order_by(StockDaily.trade_date.desc()).limit(days).all()
        db.close()

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame([{
            'date': d.trade_date,
            'open': d.open,
            'high': d.high,
            'low': d.low,
            'close': d.close,
            'volume': d.volume
        } for d in data])

        return df.sort_values('date')

    def calculate_ma(self, df: pd.DataFrame, periods: list = None) -> pd.DataFrame:
        """计算简单均线 (SMA)"""
        if periods is None:
            periods = [5, 10, 20, 30, 60, 120, 250]  # 增加长期均线

        for period in periods:
            df[f'sma_{period}'] = ta.sma(df['close'], length=period)

        return df

    def calculate_ema(self, df: pd.DataFrame, periods: list = None) -> pd.DataFrame:
        """计算指数均线 (EMA) - 对近期价格更敏感"""
        if periods is None:
            periods = [12, 26, 50, 200]

        for period in periods:
            df[f'ema_{period}'] = ta.ema(df['close'], length=period)

        return df

    def calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """计算 MACD ( Moving Average Convergence Divergence)"""
        macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
        df = pd.concat([df, macd], axis=1)
        return df

    def calculate_rsi(self, df: pd.DataFrame, periods: list = None) -> pd.DataFrame:
        """计算 RSI (Relative Strength Index) - 多周期"""
        if periods is None:
            periods = [6, 12, 14, 24]  # 增加多个周期

        for period in periods:
            df[f'rsi_{period}'] = ta.rsi(df['close'], length=period)

        return df

    def calculate_kdj(self, df: pd.DataFrame, k_period: int = 9, d_period: int = 3) -> pd.DataFrame:
        """计算 KDJ (随机指标)"""
        kdj = ta.stoch(df['high'], df['low'], df['close'], k=k_period, d=d_period)
        df = pd.concat([df, kdj], axis=1)
        return df

    def calculate_bollinger(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2) -> pd.DataFrame:
        """计算布林带 (Bollinger Bands)"""
        bbands = ta.bbands(df['close'], length=period, std=std_dev)
        df = pd.concat([df, bbands], axis=1)
        return df

    def calculate_sar(self, df: pd.DataFrame, accel: float = 0.02, max_accel: float = 0.2) -> pd.DataFrame:
        """计算抛物线转向 SAR (Parabolic SAR) - 趋势跟踪指标"""
        sar = ta.psar(df['high'], df['low'], df['close'], step=accel, max_af=max_accel)
        df = pd.concat([df, sar], axis=1)
        return df

    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """计算 ADX (Average Directional Index) - 趋势强度指标"""
        adx = ta.adx(df['high'], df['low'], df['close'], length=period)
        df = pd.concat([df, adx], axis=1)
        return df

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """计算 ATR (Average True Range) - 波动率指标"""
        atr = ta.atr(df['high'], df['low'], df['close'], length=period)
        df = pd.concat([df, atr], axis=1)
        return df

    def calculate_obv(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算 OBV (On Balance Volume) - 能量潮指标"""
        df['obv'] = ta.obv(df['close'], df['volume'])
        return df

    def calculate_cci(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """计算 CCI (Commodity Channel Index) - 商品通道指数"""
        df['cci'] = ta.cci(df['high'], df['low'], df['close'], length=period)
        return df

    def calculate_wr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """计算威廉指标 (Williams %R)"""
        df['wr'] = ta.willr(df['high'], df['low'], df['close'], length=period)
        return df

    def calculate_momentum(self, df: pd.DataFrame, period: int = 10) -> pd.DataFrame:
        """计算动量指标 (Momentum)"""
        df['mom'] = ta.mom(df['close'], length=period)
        return df

    def calculate_roc(self, df: pd.DataFrame, period: int = 10) -> pd.DataFrame:
        """计算变化率 ROC (Rate of Change)"""
        df['roc'] = ta.roc(df['close'], length=period)
        return df

    def calculate_vwap(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算成交量加权平均价 VWAP"""
        df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        return df

    def calculate_all(self, stock_code: str) -> dict:
        """计算所有指标并返回信号和详细数据"""
        df = self.get_stock_data(stock_code)

        if df.empty:
            return {}

        # 计算所有指标
        df = self.calculate_ma(df, [5, 10, 20, 60, 120])
        df = self.calculate_ema(df, [12, 26, 50, 200])
        df = self.calculate_macd(df)
        df = self.calculate_rsi(df, [6, 12, 14])
        df = self.calculate_kdj(df)
        df = self.calculate_bollinger(df)
        df = self.calculate_sar(df)
        df = self.calculate_adx(df)
        df = self.calculate_atr(df)
        df = self.calculate_obv(df)
        df = self.calculate_cci(df)
        df = self.calculate_wr(df)
        df = self.calculate_momentum(df)
        df = self.calculate_roc(df)
        df = self.calculate_vwap(df)

        # 获取信号
        signals = self.get_signals(df)

        # 返回最新数据
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        result = {
            'stock_code': stock_code,
            'date': latest['date'],
            'close': latest['close'],
            'open': latest['open'],
            'high': latest['high'],
            'low': latest['low'],
            'volume': latest['volume'],
            # 均线
            'ma5': latest.get('sma_5'),
            'ma10': latest.get('sma_10'),
            'ma20': latest.get('sma_20'),
            'ma60': latest.get('sma_60'),
            'ma120': latest.get('sma_120'),
            'ema12': latest.get('ema_12'),
            'ema26': latest.get('ema_26'),
            'ema50': latest.get('ema_50'),
            'ema200': latest.get('ema_200'),
            # MACD
            'macd': latest.get('MACD_12_26_9'),
            'macd_signal': latest.get('MACDs_12_26_9'),
            'macd_hist': latest.get('MACDh_12_26_9'),
            # RSI
            'rsi6': latest.get('rsi_6'),
            'rsi12': latest.get('rsi_12'),
            'rsi14': latest.get('rsi_14'),
            # KDJ
            'kdj_k': latest.get('STOCHk_9_3_3'),
            'kdj_d': latest.get('STOCHd_9_3_3'),
            'kdj_j': latest.get('STOCHd_9_3_3') * 3 - latest.get('STOCHk_9_3_3') * 2 if latest.get('STOCHk_9_3_3') is not None else None,
            # 布林带
            'boll_upper': latest.get('BBU_20_2.0'),
            'boll_middle': latest.get('BBM_20_2.0'),
            'boll_lower': latest.get('BBL_20_2.0'),
            # SAR
            'sar': latest.get('PSARs_0.02_0.2'),
            'sar_trend': latest.get('PSARl_0.02_0.2'),  # SAR 趋势方向
            # ADX
            'adx': latest.get('ADX_14'),
            'plus_di': latest.get('PLUS_DI_14'),
            'minus_di': latest.get('MINUS_DI_14'),
            # ATR
            'atr': latest.get('ATR_14'),
            # CCI
            'cci': latest.get('cci'),
            # Williams %R
            'wr': latest.get('wr'),
            # 动量
            'mom': latest.get('mom'),
            'roc': latest.get('roc'),
            # VWAP
            'vwap': latest.get('vwap'),
            # OBV
            'obv': latest.get('obv'),
            # 信号
            'signals': signals,
            # 全部数据（用于详细分析）
            'full_data': df.to_dict('records')
        }

        return result

    def get_signals(self, df: pd.DataFrame) -> dict:
        """生成综合技术信号 - 增强版"""
        if df.empty or len(df) < 2:
            return {}

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        prev2 = df.iloc[-3] if len(df) > 2 else prev

        signals = {}

        # ====== MA 信号 ======
        if 'sma_5' in latest and 'sma_10' in latest:
            # 金叉死叉
            if latest['sma_5'] > latest['sma_10'] and prev['sma_5'] <= prev['sma_10']:
                signals['ma_golden_cross'] = True
            elif latest['sma_5'] < latest['sma_10'] and prev['sma_5'] >= prev['sma_10']:
                signals['ma_death_cross'] = True

            # 多头/空头排列
            ma_bullish = (latest['sma_5'] > latest['sma_10'] > latest['sma_20'] > latest['sma_60'])
            ma_bearish = (latest['sma_5'] < latest['sma_10'] < latest['sma_20'] < latest['sma_60'])
            signals['ma_bullish排列'] = ma_bullish
            signals['ma_bearish 排列'] = ma_bearish

            # 价格与均线关系
            signals['price_above_ma5'] = latest['close'] > latest['sma_5']
            signals['price_above_ma20'] = latest['close'] > latest['sma_20']
            signals['price_above_ma60'] = latest['close'] > latest['sma_60']

        # ====== MACD 信号 ======
        if 'MACD_12_26_9' in latest and 'MACDs_12_26_9' in latest:
            macd = latest['MACD_12_26_9']
            signal = latest['MACDs_12_26_9']
            hist = latest.get('MACDh_12_26_9', macd - signal)

            # 多空信号
            signals['macd_bullish'] = macd > signal
            signals['macd_bearish'] = macd < signal

            # 金叉死叉
            if macd > signal and prev['MACD_12_26_9'] <= prev['MACDs_12_26_9']:
                signals['macd_golden_cross'] = True
            elif macd < signal and prev['MACD_12_26_9'] >= prev['MACDs_12_26_9']:
                signals['macd_death_cross'] = True

            # 顶背离/底背离
            if len(df) > 5:
                price_high = max(df.iloc[-5:]['close'])
                macd_high = max(df.iloc[-5:]['MACD_12_26_9'])
                if latest['close'] > price_high and macd < macd_high:
                    signals['macd_bearish_divergence'] = True  # 顶背离

                price_low = min(df.iloc[-5:]['close'])
                macd_low = min(df.iloc[-5:]['MACD_12_26_9'])
                if latest['close'] < price_low and macd > macd_low:
                    signals['macd_bullish_divergence'] = True  # 底背离

            # 零轴穿越
            if macd > 0 and prev['MACD_12_26_9'] <= 0:
                signals['macd_above_zero'] = True
            elif macd < 0 and prev['MACD_12_26_9'] >= 0:
                signals['macd_below_zero'] = True

        # ====== RSI 信号 ======
        rsi_cols = [c for c in df.columns if c.startswith('rsi_')]
        for rsi_col in rsi_cols:
            period = rsi_col.replace('rsi_', '')
            rsi = latest[rsi_col]

            if rsi > 70:
                signals[f'rsi_{period}_overbought'] = True
            elif rsi < 30:
                signals[f'rsi_{period}_oversold'] = True

            # RSI 趋势
            if len(df) > 3:
                rsi_trend = 'up' if latest[rsi_col] > prev[rsi_col] > prev2[rsi_col] else 'down'
                signals[f'rsi_{period}_trend'] = rsi_trend

        # ====== KDJ 信号 ======
        if 'STOCHk_9_3_3' in latest and 'STOCHd_9_3_3' in latest:
            k = latest['STOCHk_9_3_3']
            d = latest['STOCHd_9_3_3']

            # 金叉死叉
            if k > d and prev['STOCHk_9_3_3'] <= prev['STOCHd_9_3_3']:
                signals['kdj_golden_cross'] = True
            elif k < d and prev['STOCHk_9_3_3'] >= prev['STOCHd_9_3_3']:
                signals['kdj_death_cross'] = True

            # 超买超卖
            if k > 80:
                signals['kdj_overbought'] = True
            elif k < 20:
                signals['kdj_oversold'] = True

        # ====== 布林带信号 ======
        if 'BBU_20_2.0' in latest and 'BBL_20_2.0' in latest:
            upper = latest['BBU_20_2.0']
            lower = latest['BBL_20_2.0']
            middle = latest.get('BBM_20_2.0', (upper + lower) / 2)

            # 价格位置
            if latest['close'] > upper:
                signals['boll_breakout_upper'] = True  # 突破上轨
            elif latest['close'] < lower:
                signals['boll_breakout_lower'] = True  # 突破下轨

            # 布林带收窄/扩张
            if len(df) > 5:
                prev_bandwidth = (df['BBU_20_2.0'] - df['BBL_20_2.0']).iloc[-2]
                curr_bandwidth = upper - lower
                signals['boll_squeeze'] = curr_bandwidth < prev_bandwidth * 0.9  # 收窄
                signals['boll_expansion'] = curr_bandwidth > prev_bandwidth * 1.1  # 扩张

        # ====== SAR 信号 ======
        if 'PSARs_0.02_0.2' in latest:
            sar = latest['PSARs_0.02_0.2']
            signals['sar_bullish'] = latest['close'] > sar
            signals['sar_bearish'] = latest['close'] < sar

            # SAR 翻转
            if len(df) > 1:
                prev_sar = prev['PSARs_0.02_0.2']
                if latest['close'] > sar and prev['close'] < prev_sar:
                    signals['sar_flip_bullish'] = True
                elif latest['close'] < sar and prev['close'] > prev_sar:
                    signals['sar_flip_bearish'] = True

        # ====== ADX 信号 ======
        if 'ADX_14' in latest:
            adx = latest['ADX_14']
            signals['adx_trend_strong'] = adx > 25  # 趋势强劲
            signals['adx_trend_weak'] = adx < 20  # 趋势弱/盘整

            # +/-DI 交叉
            plus_di = latest.get('PLUS_DI_14', 0)
            minus_di = latest.get('MINUS_DI_14', 0)
            signals['di_bullish'] = plus_di > minus_di
            signals['di_bearish'] = plus_di < minus_di

        # ====== CCI 信号 ======
        if 'cci' in latest:
            cci = latest['cci']
            if cci > 100:
                signals['cci_overbought'] = True
            elif cci < -100:
                signals['cci_oversold'] = True

        # ====== 威廉指标信号 ======
        if 'wr' in latest:
            wr = latest['wr']
            if wr > -20:
                signals['wr_overbought'] = True
            elif wr < -80:
                signals['wr_oversold'] = True

        # ====== 成交量信号 ======
        if 'obv' in latest and len(df) > 10:
            # OBV 趋势
            obv_trend_5 = latest['obv'] > df['obv'].iloc[-5] if len(df) > 5 else None
            obv_trend_10 = latest['obv'] > df['obv'].iloc[-10] if len(df) > 10 else None
            signals['obv_uptrend'] = obv_trend_5 and obv_trend_10
            signals['obv_downtrend'] = not signals['obv_uptrend'] if obv_trend_5 is not None else None

            # 量价背离
            if latest['close'] > df['close'].iloc[-5] and not obv_trend_5:
                signals['price_obv_bearish_divergence'] = True
            elif latest['close'] < df['close'].iloc[-5] and obv_trend_5:
                signals['price_obv_bullish_divergence'] = True

        # ====== 综合评分 ======
        bullish_count = sum(1 for k, v in signals.items() if v is True and not 'bearish' in k and not 'overbought' in k and not 'oversold' in k)
        bearish_count = sum(1 for k, v in signals.items() if v is True and ('bearish' in k or 'death' in k or 'below' in k))
        signals['bullish_count'] = bullish_count
        signals['bearish_count'] = bearish_count
        signals['net_signal'] = bullish_count - bearish_count

        return signals
