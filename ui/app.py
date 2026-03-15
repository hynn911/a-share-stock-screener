"""
A 股高价值股票发掘系统 - Streamlit 界面
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date
from pathlib import Path
import sys
import importlib
import time

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 强制重新加载所有核心模块（解决 Streamlit 缓存问题）
def reload_core_modules():
    """重新加载核心模块，确保使用最新代码"""
    core_modules = [
        'core.database',
        'core.models',
        'core.data_fetcher',
        'core.indicator',
        'core.capital',
        'core.hot_words',
        'core.position',
        'core.shareholder',
        'core.stock_scorer',
        'core.commodity',
    ]
    for mod_name in core_modules:
        if mod_name in sys.modules:
            importlib.reload(sys.modules[mod_name])

# 每次运行都重新加载模块
reload_core_modules()

from core.database import init_db, SessionLocal
from core.models import Stock, Position, SellSignal
from core.data_fetcher import DataFetcher
from core.indicator import IndicatorCalculator
from core.capital import CapitalAnalyzer
from core.hot_words import HotWordAnalyzer
from core.position import PositionManager
from core.shareholder import ShareholderAnalyzer
from core.stock_scorer import StockScorer
from core.commodity import CommodityMonitor

# 页面配置
st.set_page_config(
    page_title="A 股高价值股票发掘",
    page_icon="📈",
    layout="wide"
)

# 初始化数据库
@st.cache_resource
def init_database():
    init_db()

init_database()

# 侧边栏导航
st.sidebar.title("导航")
page = st.sidebar.radio(
    "选择页面",
    ["首页", "智能荐股", "热点看板", "资金监控", "选股器", "持仓管理", "消息中心", "股东户数", "大宗商品"]
)

# 首页
if page == "首页":
    st.title("📈 A 股高价值股票发掘系统")
    st.markdown("---")

    # 数据新鲜度检查
    def check_data_status():
        """检查数据新鲜度并返回状态"""
        from sqlalchemy import func
        from core.models import StockDaily
        db = SessionLocal()

        today = datetime.now().date()

        # 检查各类数据的最新日期
        from core.models import StockCapitalFlow, StockHolderCount, StockNews

        latest_daily = db.query(func.max(StockDaily.trade_date)).scalar()
        latest_flow = db.query(func.max(StockCapitalFlow.trade_date)).scalar()
        latest_holder = db.query(func.max(StockHolderCount.trade_date)).scalar()
        latest_news = db.query(func.max(StockNews.publish_time)).scalar()

        db.close()

        status = []
        needs_update = False

        if latest_daily:
            days = (today - latest_daily.date()).days
            status.append(("日线数据", latest_daily, days))
            if days > 1:
                needs_update = True

        if latest_flow:
            days = (today - latest_flow.date()).days
            status.append(("资金流", latest_flow, days))
            if days > 1:
                needs_update = True

        if latest_holder:
            days = (today - latest_holder.date()).days
            status.append(("股东户数", latest_holder, days))
            if days > 3:
                needs_update = True

        if latest_news:
            days = (today - latest_news.date()).days
            status.append(("新闻", latest_news, days))
            if days > 1:
                needs_update = True

        return status, needs_update

    try:
        data_status, needs_update = check_data_status()

        if needs_update:
            st.warning("⚠️ 部分数据可能过期，建议运行更新脚本：`python scripts/auto_update.py`")
            st.markdown("")
    except Exception:
        pass  # 如果检查失败，不显示警告

    # 快速统计
    db = SessionLocal()
    stock_count = db.query(Stock).count()
    position_count = db.query(Position).filter(Position.status == "holding").count()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("股票池数量", f"{stock_count:,}")
    with col2:
        st.metric("当前持仓", f"{position_count}")
    with col3:
        st.metric("今日日期", datetime.now().strftime("%Y-%m-%d"))
    with col4:
        st.metric("系统状态", "运行中")

    st.markdown("---")
    st.markdown("### 功能说明")
    st.markdown("""
    - **热点看板**: 查看市场热词和热点方向
    - **资金监控**: 监控连续资金流入的股票
    - **选股器**: 根据技术指标筛选股票
    - **持仓管理**: 管理持仓并获取卖点建议
    - **消息中心**: 查看股票相关新闻
    - **股东户数**: 分析股东户数变化和筹码集中度
    """)

    # 数据更新说明
    with st.expander("📝 数据更新说明"):
        st.markdown("""
        ### 数据更新方式

        **自动更新（推荐）**:
        - 运行 `python scripts/setup_windows_task.bat` 设置定时任务
        - 每周一至周五 16:00 自动更新数据

        **手动更新**:
        ```bash
        # 更新所有数据
        python scripts/auto_update.py

        # 更新前 N 只股票（测试用）
        python scripts/auto_update.py 100
        ```

        **数据说明**:
        - 日线数据：每日收盘后更新
        - 资金流：每日收盘后更新
        - 股东户数：每季度更新（财报披露）
        - 新闻数据：每日更新
        """)

# 热点看板
elif page == "热点看板":
    st.title("🔥 热点看板")
    st.markdown("### 热门板块监测 - 黄金/芯片/有色/新能源等")

    # 选择查看天数
    days = st.slider("查看天数", 1, 7, 3, help="查看最近几天的热点数据")

    col1, col2 = st.columns([3, 1])

    with col1:
        analyzer = HotWordAnalyzer()

        # 获取热门板块
        hot_sectors = analyzer.get_hot_sectors(days=days, top_n=15)

        if hot_sectors:
            # 显示板块热度排行
            st.subheader(f"📊 热门板块 Top {len(hot_sectors)}")

            # 使用卡片式布局显示板块
            sector_cols = st.columns(3)
            for i, sector in enumerate(hot_sectors):
                with sector_cols[i % 3]:
                    with st.container():
                        st.markdown(f"""
                        <div style="
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            padding: 15px;
                            border-radius: 10px;
                            margin: 10px 0;
                            color: white;
                        ">
                            <h3 style="margin: 0; font-size: 18px;">{sector['sector']}</h3>
                            <p style="margin: 5px 0; opacity: 0.9;">热度：{sector['hot_score']:.1f}</p>
                            <p style="margin: 5px 0; opacity: 0.8;">关键词：{', '.join(sector['top_words'][:3])}</p>
                        </div>
                        """, unsafe_allow_html=True)

            # 详细数据表
            st.subheader("📋 板块热度详情")
            sector_df = pd.DataFrame(hot_sectors)
            sector_df['热度等级'] = pd.cut(
                sector_df['hot_score'],
                bins=5,
                labels=['❄️ 冷门', '⚪ 偏冷', '🔥 温和', '🔥🔥 热门', '🔥🔥🔥 超热']
            )
            st.dataframe(
                sector_df[['sector', 'hot_score', 'word_count', '热度等级']],
                use_container_width=True,
                column_config={
                    "sector": "板块名称",
                    "hot_score": "热度分数",
                    "word_count": "关键词数量",
                    "热度等级": "热度等级"
                }
            )

            # 点击板块查看相关股票
            st.subheader("🔍 查看板块相关股票")
            selected_sector = st.selectbox(
                "选择板块",
                options=[s['sector'] for s in hot_sectors],
                format_func=lambda x: f"{x} (热度：{hot_sectors[[s['sector'] for s in hot_sectors].index(x)]['hot_score']:.1f})"
            )

            if selected_sector:
                sector_stocks = analyzer.get_sector_stocks(selected_sector, limit=30)
                if sector_stocks:
                    st.write(f"**{selected_sector}** 相关股票（{len(sector_stocks)}只）:")
                    stock_df = pd.DataFrame(sector_stocks)
                    st.dataframe(
                        stock_df,
                        use_container_width=True,
                        column_config={
                            "stock_code": "股票代码",
                            "stock_name": "股票名称",
                            "industry": "所属行业"
                        }
                    )
                else:
                    st.info(f"未找到与 {selected_sector} 直接相关的股票（通过名称匹配）")
        else:
            st.info("暂无热点板块数据，请先更新新闻数据")

        analyzer.close()

    with col2:
        # 显示热词云图（简化版）
        st.subheader("📝 实时热词")
        analyzer = HotWordAnalyzer()
        hot_words = analyzer.get_hot_words(days=days, top_n=30)

        if hot_words:
            word_cloud_data = {
                '热词': [hw['word'] for hw in hot_words],
                '热度': [hw['hot_score'] for hw in hot_words]
            }
            word_cloud_df = pd.DataFrame(word_cloud_data)
            st.dataframe(
                word_cloud_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "热词": "热词",
                    "热度": "热度分数"
                }
            )
        else:
            st.info("暂无热词数据")
        analyzer.close()

# 资金监控
elif page == "资金监控":
    st.title("💰 资金流入监控")

    min_days = st.slider("连续流入天数", 1, 10, 3)
    min_amount = st.number_input("最小净流入 (万元)", min_value=0, value=1000) * 10000

    if st.button("开始筛选"):
        analyzer = CapitalAnalyzer()
        results = analyzer.get_all_consecutive_inflow(min_days, min_amount)

        if results:
            df = pd.DataFrame(results)
            # 添加股票名称列
            if 'stock_code' in df.columns and 'stock_name' in df.columns:
                df['股票'] = df['stock_code'] + " - " + df['stock_name']
                display_cols = ['股票', 'consecutive_days', 'total_net_inflow']
                st.dataframe(
                    df[display_cols],
                    use_container_width=True,
                    column_config={
                        "股票": "股票",
                        "consecutive_days": "连续流入天数",
                        "total_net_inflow": "净流入 (元)"
                    }
                )
            else:
                st.dataframe(df, use_container_width=True)
        else:
            st.warning("未找到符合条件的股票")

# 选股器
elif page == "选股器":
    st.title("🎯 技术指标选股")

    stock_code = st.text_input("输入股票代码 (如 600519)")

    if st.button("分析"):
        if stock_code:
            # 获取股票名称
            db = SessionLocal()
            from core.models import Stock
            stock = db.query(Stock).filter(Stock.code == stock_code).first()
            stock_name = stock.name if stock else ""
            db.close()

            calc = IndicatorCalculator()
            result = calc.calculate_all(stock_code)

            if result:
                display_name = f"{result['stock_code']} - {stock_name}" if stock_name else result['stock_code']
                st.subheader(display_name)

                # 基础价格信息
                st.subheader("💰 价格信息")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("收盘价", f"{result['close']:.2f}")
                with col2:
                    st.metric("开盘价", f"{result['open']:.2f}" if result.get('open') else "N/A")
                with col3:
                    st.metric("最高价", f"{result['high']:.2f}" if result.get('high') else "N/A")
                with col4:
                    st.metric("最低价", f"{result['low']:.2f}" if result.get('low') else "N/A")

                # 均线系统
                st.subheader("📈 均线系统 (MA & EMA)")
                ma_cols = st.columns(4)
                ma_data = [
                    ("MA5", result.get('ma5')), ("MA10", result.get('ma10')),
                    ("MA20", result.get('ma20')), ("MA60", result.get('ma60')),
                    ("MA120", result.get('ma120')), ("EMA12", result.get('ema12')),
                    ("EMA26", result.get('ema26')), ("EMA200", result.get('ema200'))
                ]
                for i, (label, value) in enumerate(ma_data):
                    with ma_cols[i % 4]:
                        if value:
                            st.metric(label, f"{value:.2f}")
                        else:
                            st.metric(label, "N/A")

                # MACD 指标
                st.subheader("📊 MACD (指数平滑异同移动平均线)")
                macd_cols = st.columns(3)
                with macd_cols[0]:
                    macd_val = result.get('macd')
                    st.metric("MACD", f"{macd_val:.4f}" if macd_val else "N/A")
                with macd_cols[1]:
                    signal_val = result.get('macd_signal')
                    st.metric("Signal", f"{signal_val:.4f}" if signal_val else "N/A")
                with macd_cols[2]:
                    hist_val = result.get('macd_hist')
                    if hist_val:
                        delta_color = "normal" if hist_val >= 0 else "inverse"
                        st.metric("Histogram", f"{hist_val:.4f}", delta=f"{hist_val:.4f}", delta_color=delta_color)
                    else:
                        st.metric("Histogram", "N/A")

                # RSI 指标
                st.subheader("💪 RSI (相对强弱指数)")
                rsi_cols = st.columns(3)
                with rsi_cols[0]:
                    rsi6 = result.get('rsi6')
                    st.metric("RSI6", f"{rsi6:.2f}" if rsi6 else "N/A")
                with rsi_cols[1]:
                    rsi12 = result.get('rsi12')
                    st.metric("RSI12", f"{rsi12:.2f}" if rsi12 else "N/A")
                with rsi_cols[2]:
                    rsi14 = result.get('rsi14')
                    st.metric("RSI14", f"{rsi14:.2f}" if rsi14 else "N/A")

                # KDJ 指标
                st.subheader("🎲 KDJ (随机指标)")
                kdj_cols = st.columns(3)
                with kdj_cols[0]:
                    kdj_k = result.get('kdj_k')
                    st.metric("K", f"{kdj_k:.2f}" if kdj_k else "N/A")
                with kdj_cols[1]:
                    kdj_d = result.get('kdj_d')
                    st.metric("D", f"{kdj_d:.2f}" if kdj_d else "N/A")
                with kdj_cols[2]:
                    kdj_j = result.get('kdj_j')
                    st.metric("J", f"{kdj_j:.2f}" if kdj_j else "N/A")

                # 布林带
                st.subheader("📉 布林带 (Bollinger Bands)")
                boll_cols = st.columns(3)
                with boll_cols[0]:
                    upper = result.get('boll_upper')
                    st.metric("上轨", f"{upper:.2f}" if upper else "N/A")
                with boll_cols[1]:
                    middle = result.get('boll_middle')
                    st.metric("中轨", f"{middle:.2f}" if middle else "N/A")
                with boll_cols[2]:
                    lower = result.get('boll_lower')
                    st.metric("下轨", f"{lower:.2f}" if lower else "N/A")

                # 其他重要指标
                st.subheader("🔍 其他关键指标")
                other_cols = st.columns(4)
                with other_cols[0]:
                    sar = result.get('sar')
                    st.metric("SAR", f"{sar:.2f}" if sar else "N/A")
                with other_cols[1]:
                    adx = result.get('adx')
                    st.metric("ADX", f"{adx:.2f}" if adx else "N/A")
                with other_cols[2]:
                    atr = result.get('atr')
                    st.metric("ATR", f"{atr:.2f}" if atr else "N/A")
                with other_cols[3]:
                    cci = result.get('cci')
                    st.metric("CCI", f"{cci:.2f}" if cci else "N/A")

                # 第二排其他指标
                other_cols2 = st.columns(4)
                with other_cols2[0]:
                    wr = result.get('wr')
                    st.metric("Williams %R", f"{wr:.2f}" if wr else "N/A")
                with other_cols2[1]:
                    mom = result.get('mom')
                    st.metric("Momentum", f"{mom:.2f}" if mom else "N/A")
                with other_cols2[2]:
                    roc = result.get('roc')
                    st.metric("ROC", f"{roc:.2f}" if roc else "N/A")
                with other_cols2[3]:
                    vwap = result.get('vwap')
                    st.metric("VWAP", f"{vwap:.2f}" if vwap else "N/A")

                # 综合信号看板
                st.subheader("🎯 综合信号看板")
                signals = result.get('signals', {})

                # 信号统计
                bullish_count = signals.get('bullish_count', 0)
                bearish_count = signals.get('bearish_count', 0)
                net_signal = signals.get('net_signal', 0)

                signal_cols = st.columns(3)
                with signal_cols[0]:
                    st.metric("看涨信号", f"{bullish_count}个")
                with signal_cols[1]:
                    st.metric("看跌信号", f"{bearish_count}个")
                with signal_cols[2]:
                    delta_color = "normal" if net_signal >= 0 else "inverse"
                    st.metric("净信号", f"{net_signal:+d}", delta=f"{net_signal:+d}", delta_color=delta_color)

                # 详细信号分类展示
                if signals:
                    st.subheader("📋 详细技术信号")

                    # 趋势信号
                    trend_signals = [
                        (k, v) for k, v in signals.items()
                        if v is True and any(x in k for x in ['ma_', 'macd_', 'sar_', 'adx_', 'di_'])
                    ]
                    if trend_signals:
                        with st.expander("📈 趋势信号", expanded=True):
                            for sig, _ in trend_signals:
                                sig_display = sig.replace('_', ' ').title()
                                if 'death' in sig or 'bearish' in sig or 'below' in sig:
                                    st.error(f"⚠️ {sig_display}")
                                elif 'golden' in sig or 'bullish' in sig or 'above' in sig:
                                    st.success(f"✅ {sig_display}")
                                else:
                                    st.info(f"ℹ️ {sig_display}")

                    # 超买超卖信号
                    os_signals = [
                        (k, v) for k, v in signals.items()
                        if v is True and any(x in k for x in ['overbought', 'oversold'])
                    ]
                    if os_signals:
                        with st.expander("🌡️ 超买/超卖信号", expanded=True):
                            for sig, _ in os_signals:
                                sig_display = sig.replace('_', ' ').title()
                                if 'overbought' in sig:
                                    st.warning(f"⚠️ {sig_display} - 注意回调风险")
                                elif 'oversold' in sig:
                                    st.info(f"✅ {sig_display} - 可能存在反弹机会")

                    # 布林带信号
                    boll_signals = [
                        (k, v) for k, v in signals.items()
                        if v is True and any(x in k for x in ['boll_', 'breakout', 'squeeze', 'expansion'])
                    ]
                    if boll_signals:
                        with st.expander("📉 布林带信号", expanded=True):
                            for sig, _ in boll_signals:
                                sig_display = sig.replace('_', ' ').title()
                                st.info(f"ℹ️ {sig_display}")

                    # KDJ 信号
                    kdj_signals = [
                        (k, v) for k, v in signals.items()
                        if v is True and any(x in k for x in ['kdj_'])
                    ]
                    if kdj_signals:
                        with st.expander("🎲 KDJ 信号", expanded=True):
                            for sig, _ in kdj_signals:
                                sig_display = sig.replace('_', ' ').title()
                                if 'death' in sig or 'overbought' in sig:
                                    st.warning(f"⚠️ {sig_display}")
                                elif 'golden' in sig or 'oversold' in sig:
                                    st.success(f"✅ {sig_display}")

                    # 成交量信号
                    vol_signals = [
                        (k, v) for k, v in signals.items()
                        if v is True and any(x in k for x in ['obv_', 'volume', 'divergence'])
                    ]
                    if vol_signals:
                        with st.expander("📊 成交量信号", expanded=True):
                            for sig, _ in vol_signals:
                                sig_display = sig.replace('_', ' ').title()
                                if 'bearish' in sig or 'downtrend' in sig:
                                    st.warning(f"⚠️ {sig_display}")
                                elif 'bullish' in sig or 'uptrend' in sig:
                                    st.success(f"✅ {sig_display}")
                                else:
                                    st.info(f"ℹ️ {sig_display}")

                    # RSI 信号
                    rsi_signals = [
                        (k, v) for k, v in signals.items()
                        if v is True and any(x in k for x in ['rsi_']) and 'overbought' not in k and 'oversold' not in k
                    ]
                    if rsi_signals:
                        with st.expander("💪 RSI 信号", expanded=True):
                            for sig, _ in rsi_signals:
                                sig_display = sig.replace('_', ' ').title()
                                st.info(f"ℹ️ {sig_display}")

                    # 其他信号
                    other_signals = [
                        (k, v) for k, v in signals.items()
                        if v is True and not any(x in k for x in ['ma_', 'macd_', 'sar_', 'adx_', 'di_',
                                                                   'overbought', 'oversold', 'boll_',
                                                                   'kdj_', 'obv_', 'volume', 'divergence',
                                                                   'rsi_', 'bullish_count', 'bearish_count', 'net_signal'])
                    ]
                    if other_signals:
                        with st.expander("🔍 其他信号", expanded=True):
                            for sig, _ in other_signals:
                                sig_display = sig.replace('_', ' ').title()
                                st.info(f"ℹ️ {sig_display}")

                # 详细数据
                with st.expander("📊 查看详细数据"):
                    full_data = result.get('full_data', [])
                    if full_data:
                        df = pd.DataFrame(full_data)
                        st.dataframe(df, use_container_width=True)
            else:
                st.warning("未找到该股票的数据")
        else:
            st.warning("请输入股票代码")

# 持仓管理
elif page == "持仓管理":
    st.title("📊 持仓管理与卖点建议")

    # 添加持仓表单
    with st.expander("➕ 添加持仓"):
        with st.form("add_position"):
            code = st.text_input("股票代码", key="add_stock_code", help="输入 6 位股票代码，如 001309")

            # 自动填充股票信息（从数据库获取，确保准确性）
            stock_info = {}
            stock_name_from_db = ""
            if code and len(code) == 6:
                manager = PositionManager()
                # 优先从数据库获取股票名称
                stock_name_from_db = manager.get_stock_name_from_db(code)
                # 尝试获取实时价格
                try:
                    stock_info = manager.get_stock_info(code)
                except:
                    pass
                manager.close()

                if stock_name_from_db:
                    st.success(f"找到股票：{code} - {stock_name_from_db}")
                elif stock_info.get('name'):
                    st.info(f"数据库中未找到，从 API 获取：{code} - {stock_info['name']}")
                else:
                    st.warning(f"未找到股票信息：{code}")

            name = st.text_input(
                "股票名称",
                value=stock_name_from_db if stock_name_from_db else stock_info.get('name', ''),
                help="输入股票代码后自动填充，以数据库为准"
            )

            # 买入价格
            current_price = stock_info.get('current_price')
            price_default = current_price if current_price else 0.01  # 避免 0 价格
            price = st.number_input("买入价格", min_value=0.01, value=price_default, step=0.01)
            qty = st.number_input("买入数量", min_value=100, step=100, value=100)
            stop_loss = st.number_input("止损比例 (%)", value=8.0, min_value=0.0, max_value=100.0) / 100
            target_profit = st.number_input("止盈比例 (%)", value=30.0, min_value=0.0, max_value=1000.0) / 100

            submitted = st.form_submit_button("添加持仓")
            if submitted and code:
                if not name:
                    st.error("请输入股票名称")
                elif price <= 0:
                    st.error("买入价格必须大于 0")
                else:
                    manager = PositionManager()
                    manager.add_position(
                        stock_code=code,
                        stock_name=name,
                        buy_price=price,
                        quantity=qty,
                        stop_loss_rate=stop_loss,
                        target_profit_rate=target_profit
                    )
                    manager.close()
                    st.success(f"已添加持仓：{code} - {name}")
                    st.rerun()

    # 显示持仓列表
    st.subheader("当前持仓")
    manager = PositionManager()
    positions = manager.get_all_positions()

    if positions:
        for pos in positions:
            with st.container():
                # 获取股票名称（优先使用持仓中保存的名称）
                stock_name = pos.stock_name
                if not stock_name:
                    stock_name = manager.get_stock_name_from_db(pos.stock_code)

                st.markdown(f"#### {pos.stock_code} - {stock_name}")

                # 获取当前价格
                # 1. 优先从数据库获取最新收盘价
                current_price = manager.get_latest_close_price(pos.stock_code)

                if current_price is None:
                    # 2. 数据库没有，尝试从 API 获取
                    try:
                        info = manager.get_stock_info(pos.stock_code)
                        current_price = info.get('current_price')
                    except:
                        current_price = None

                if current_price is None:
                    # 3. 都没有，使用买入价
                    current_price = pos.buy_price
                    st.caption("⚠️ 无法获取最新价格，显示为买入成本价")

                # 更新盈亏
                manager.update_position_price(pos, current_price)

                # 从 position 对象获取盈亏数据
                pnl_pct = pos.profit_loss * 100 if pos.profit_loss else 0.0  # 转换为百分比
                pnl_amt = pos.profit_amount if pos.profit_amount else 0.0

                # 中国股市颜色：红涨绿跌
                # Streamlit 的 delta_color 逻辑：
                # - "normal": 正数显示红色，负数显示绿色（符合中国股市！）
                # - "inverse": 正数显示绿色，负数显示红色
                # 所以直接用 "normal" 即可实现：赚红亏绿

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("成本价", f"{pos.buy_price:.2f}")
                with col2:
                    # 当前价：显示相对于成本的涨跌幅
                    price_delta = f"{pnl_pct:+.1f}%" if pos.buy_price else None
                    st.metric("当前价", f"{current_price:.2f}",
                             delta=price_delta,
                             delta_color="normal")  # 正红负绿
                with col3:
                    # 盈亏：显示盈亏金额和比例
                    pnl_delta = f"{pnl_amt:+.0f}元" if pnl_amt != 0 else None
                    st.metric("盈亏", f"{pnl_pct:+.1f}%",
                             delta=pnl_delta,
                             delta_color="normal")  # 正红负绿
                with col4:
                    st.metric("持仓数量", f"{pos.quantity:,}股")

                # 操作按钮
                btn_cols = st.columns(3)
                with btn_cols[0]:
                    if st.button("📊 查看分析", key=f"analysis_{pos.id}"):
                        st.session_state[f"show_analysis_{pos.id}"] = True
                with btn_cols[1]:
                    if st.button("📉 减仓/卖出", key=f"sell_{pos.id}"):
                        st.session_state[f"show_sell_{pos.id}"] = True
                with btn_cols[2]:
                    if st.button("删除持仓", key=f"delete_{pos.id}"):
                        pos.status = 'sold'
                        pos.sell_reason = "手动删除"
                        manager.db.commit()
                        st.success(f"已删除持仓：{pos.stock_code}")
                        st.rerun()

                # 减仓/卖出表单
                if st.session_state.get(f"show_sell_{pos.id}", False):
                    with st.expander("📉 减仓/卖出操作", expanded=True):
                        sell_form = st.form(key=f"sell_form_{pos.id}")
                        with sell_form:
                            sell_cols = st.columns(3)
                            with sell_cols[0]:
                                sell_price_input = st.number_input(
                                    "卖出价格",
                                    min_value=0.0,
                                    value=current_price,
                                    key=f"sell_price_{pos.id}"
                                )
                            with sell_cols[1]:
                                max_sell = pos.quantity
                                sell_qty = st.number_input(
                                    "卖出数量",
                                    min_value=1,
                                    max_value=max_sell,
                                    value=max_sell,
                                    key=f"sell_qty_{pos.id}"
                                )
                            with sell_cols[2]:
                                sell_reason = st.selectbox(
                                    "卖出原因",
                                    ["止盈", "止损", "调仓", "急用钱", "其他"],
                                    key=f"sell_reason_{pos.id}"
                                )

                            sell_col1, sell_col2 = st.columns(2)
                            with sell_col1:
                                do_sell = st.form_submit_button("确认卖出")
                                if do_sell:
                                    if sell_qty >= pos.quantity:
                                        manager.sell_position(pos, sell_price_input, f"手动卖出：{sell_reason}")
                                        st.success(f"已卖出全部持仓：{pos.stock_code}")
                                    else:
                                        manager.reduce_position(pos, sell_qty, sell_price_input)
                                        st.success(f"已减仓 {sell_qty} 股：{pos.stock_code}")
                                    st.session_state[f"show_sell_{pos.id}"] = False
                                    st.rerun()
                            with sell_col2:
                                if st.form_submit_button("取消"):
                                    st.session_state[f"show_sell_{pos.id}"] = False
                                    st.rerun()

                # 五维度分析（默认隐藏，点击后显示）
                if st.session_state.get(f"show_analysis_{pos.id}", False):
                    with st.expander("📊 五维度分析", expanded=True):
                        analysis = manager.get_position_analysis(pos, current_price)

                        # 显示综合评分
                        total_score = analysis['total_score']
                        score_color = "🟢" if total_score >= 70 else "🟡" if total_score >= 50 else "🔴"
                        st.metric("综合评分", f"{total_score:.1f}", help=f"{score_color} 分数越高越好")
                        st.caption(f"计算公式：资金流×25% + 技术×25% + 股东×20% + 新闻×15% + 动量×15%")

                        # 五维度明细
                        st.markdown("### 各维度评分详情")

                        # 1. 资金流分析
                        with st.expander(f"💰 资金流分析 - 评分：{analysis['capital']['score']:.0f}/100 (权重 25%)", expanded=False):
                            cap = analysis['capital']['details']
                            st.markdown(f"**评分：{analysis['capital']['score']:.0f} 分**")

                            # 原始数据
                            st.markdown("**📊 原始数据**")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("连续流入天数", f"{cap.get('consecutive_days', 0)}天")
                            with col2:
                                st.metric("总净流入", f"{cap.get('total_net_inflow', 0) / 10000:.1f}万元")
                            with col3:
                                st.metric("日均净流入", f"{cap.get('avg_net_inflow', 0) / 10000:.1f}万元")

                            # 计算规则
                            st.markdown("**📐 计算规则**")
                            st.json(cap.get('scoring_rules', {}))

                            # 分数构成
                            st.markdown("**📈 分数构成**")
                            breakdown = cap.get('score_breakdown', {})
                            st.write(f"- 连续流入 score: {breakdown.get('consecutive_score', 0)} 分 (满分 40)")
                            st.write(f"- 净流入金额：{breakdown.get('amount_score', 0)} 分 (满分 60)")

                            # 每日数据
                            if cap.get('daily_data'):
                                st.markdown("**📅 每日资金流数据**")
                                for day in cap.get('daily_data', []):
                                    net_inflow = day.get('net_inflow', 0) / 10000
                                    st.write(f"- {day.get('date')}: 净流入 {net_inflow:+.1f}万元")

                        # 2. 技术分析
                        with st.expander(f"📈 技术指标 - 评分：{analysis['technical']['score']:.0f}/100 (权重 25%)", expanded=False):
                            tech = analysis['technical']['details']
                            st.markdown(f"**评分：{analysis['technical']['score']:.0f} 分**")

                            # 原始数据
                            st.markdown("**📊 原始数据**")
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("MA5", f"{tech.get('ma5', 'N/A')}")
                            with col2:
                                st.metric("MA20", f"{tech.get('ma20', 'N/A')}")
                            with col3:
                                st.metric("MACD", f"{tech.get('macd', 'N/A')}")
                            with col4:
                                st.metric("RSI", f"{tech.get('rsi', 'N/A')}")

                            # 计算规则
                            st.markdown("**📐 计算规则**")
                            st.json(tech.get('scoring_rules', {}))

                            # 分数构成
                            st.markdown("**📈 分数构成**")
                            st.write(f"- 基础分：50 分")
                            st.write(f"- MA 信号：{tech.get('score_breakdown', {}).get('ma_signal', 0)} 分")
                            st.write(f"- MACD 信号：{tech.get('score_breakdown', {}).get('macd_signal', 0)} 分")
                            st.write(f"- RSI 信号：{tech.get('score_breakdown', {}).get('rsi_signal', 0)} 分")

                            # 技术信号
                            if tech.get('signals'):
                                st.markdown("**📉 技术信号**")
                                st.write(", ".join(tech.get('signals', [])))

                        # 3. 股东户数分析
                        with st.expander(f"👥 股东户数 - 评分：{analysis['holder']['score']:.0f}/100 (权重 20%)", expanded=False):
                            holder = analysis['holder']['details']
                            st.markdown(f"**评分：{analysis['holder']['score']:.0f} 分**")

                            # 原始数据
                            st.markdown("**📊 原始数据**")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("股东户数", f"{holder.get('holder_count', 'N/A')}户")
                            with col2:
                                change_count = holder.get('change_count')
                                if change_count is not None and isinstance(change_count, (int, float)):
                                    try:
                                        st.metric("变化数量", f"{change_count:,+}")
                                    except (ValueError, TypeError):
                                        st.metric("变化数量", str(change_count))
                                else:
                                    st.metric("变化数量", "N/A")
                            with col3:
                                st.metric("变化比例", f"{holder.get('change_ratio', 0):+.2f}%")

                            # 计算规则
                            st.markdown("**📐 计算规则**")
                            st.json(holder.get('scoring_rules', {}))

                            # 分数构成
                            st.markdown("**📈 分数构成**")
                            st.write(f"- 基础分：50 分")
                            breakdown = holder.get('score_breakdown', {})
                            st.write(f"- 趋势变化：{breakdown.get('trend_change', 0)} 分")
                            st.write(f"- 连续减少奖励：{breakdown.get('consecutive_bonus', 0)} 分")

                            # 趋势
                            if holder.get('trend'):
                                st.markdown("**📉 趋势**")
                                st.write(", ".join(holder.get('trend', [])))

                        # 4. 新闻情绪分析
                        with st.expander(f"📰 新闻情绪 - 评分：{analysis['news']['score']:.0f}/100 (权重 15%)", expanded=False):
                            news = analysis['news']['details']
                            st.markdown(f"**评分：{analysis['news']['score']:.0f} 分**")

                            # 原始数据
                            st.markdown("**📊 原始数据**")
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("新闻数量", f"{news.get('news_count', 0)}篇")
                            with col2:
                                st.metric("平均情绪", f"{news.get('avg_sentiment', 0):.2f}")
                            with col3:
                                st.metric("正面新闻", f"{news.get('positive_count', 0)}篇")
                            with col4:
                                st.metric("负面新闻", f"{news.get('negative_count', 0)}篇")

                            # 计算规则
                            st.markdown("**📐 计算规则**")
                            st.json(news.get('scoring_rules', {}))

                            # 分数构成
                            st.markdown("**📈 分数构成**")
                            breakdown = news.get('score_breakdown', {})
                            st.write(f"- 情绪分数：{breakdown.get('sentiment_score', 0)} 分")
                            st.write(f"- 数量奖励：{breakdown.get('count_bonus', 0)} 分 (满分 20)")

                            # 最近新闻
                            if news.get('recent_news'):
                                st.markdown("**📝 最近新闻**")
                                for n in news.get('recent_news', [])[:5]:
                                    sentiment_icon = "🟢" if n.get('sentiment') == 'positive' else "🔴" if n.get('sentiment') == 'negative' else "🟡"
                                    st.write(f"{sentiment_icon} {n.get('title', '')} ({n.get('sentiment', '')}, 情绪分:{n.get('sentiment_score', 0):.2f})")

                        # 5. 价格动量分析
                        with st.expander(f"📊 价格动量 - 评分：{analysis['momentum']['score']:.0f}/100 (权重 15%)", expanded=False):
                            mom = analysis['momentum']['details']
                            st.markdown(f"**评分：{analysis['momentum']['score']:.0f} 分**")

                            # 原始数据
                            st.markdown("**📊 原始数据**")
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("当前价", f"{mom.get('close', 'N/A')}")
                            with col2:
                                st.metric("MA20", f"{mom.get('ma20', 'N/A')}")
                            with col3:
                                st.metric("5 日涨幅", f"{mom.get('change_5d', 0):+.1f}%")
                            with col4:
                                st.metric("20 日涨幅", f"{mom.get('change_20d', 0):+.1f}%")

                            # 计算规则
                            st.markdown("**📐 计算规则**")
                            st.json(mom.get('scoring_rules', {}))

                            # 分数构成
                            st.markdown("**📈 分数构成**")
                            st.write(f"- 基础分：50 分")
                            breakdown = mom.get('score_breakdown', {})
                            st.write(f"- MA20 信号：{breakdown.get('ma20_signal', 0)} 分")
                            st.write(f"- 20 日涨幅：{breakdown.get('change_20d_signal', 0)} 分")

                            # 动量信号
                            if mom.get('signals'):
                                st.markdown("**📉 动量信号**")
                                st.write(", ".join(mom.get('signals', [])))

                        # 卖出信号
                        signals = manager.check_sell_signals(pos, current_price)
                        if signals:
                            st.markdown("**⚠️ 卖出信号**")
                            for sig in signals:
                                icon = "🔴" if sig['priority'] == 'CRITICAL' else "⚠️" if sig['priority'] == 'HIGH' else "ℹ️"
                                st.write(f"{icon} **{sig['type']}**: {sig['description']} - {sig['suggestion']}")

                        if st.button("关闭分析", key=f"close_analysis_{pos.id}"):
                            st.session_state[f"show_analysis_{pos.id}"] = False
                            st.rerun()

                # 显示行业信息
                if hasattr(pos, 'industry') and pos.industry:
                    st.caption(f"行业：{pos.industry}")

    else:
        st.info("暂无持仓，点击上方'添加持仓'开始")

    manager.close()

# 消息中心
elif page == "消息中心":
    st.title("📰 消息中心")

    stock_code = st.text_input("输入股票代码查看新闻")

    if stock_code:
        fetcher = DataFetcher()
        news_count = fetcher.fetch_stock_news(stock_code)

        if news_count > 0:
            st.success(f"已获取 {news_count} 条新闻")
        else:
            st.warning("暂无新闻数据")

        fetcher.close()

# 智能荐股
elif page == "智能荐股":
    st.title("🎯 智能荐股")
    st.markdown("基于多维度分析的综合股票推荐系统")

    # 侧边栏：数据管理
    with st.sidebar:
        st.header("💾 数据管理")
        st.markdown("**行业/板块数据来源**：AkShare (东方财富)")

        # 显示当前数据状态
        from core.database import SessionLocal
        from core.models import Stock
        db = SessionLocal()
        total = db.query(Stock).count()
        with_industry = db.query(Stock).filter(Stock.industry != None, Stock.industry != '').count()
        with_concept = db.query(Stock).filter(Stock.concept != None, Stock.concept != '').count()
        db.close()

        st.metric("数据库股票总数", total)
        col1, col2 = st.columns(2)
        with col1:
            pct = with_industry/total*100 if total > 0 else 0
            st.metric("有行业数据", f"{with_industry}", delta=f"{pct:.1f}%")
        with col2:
            pct = with_concept/total*100 if total > 0 else 0
            st.metric("有概念数据", f"{with_concept}", delta=f"{pct:.1f}%")

        if with_industry < total * 0.5:
            st.warning("⚠️ 行业数据覆盖率低，建议刷新")

        # 刷新按钮
        if st.button("🔄 刷新行业/板块数据", use_container_width=True, type="primary"):
            with st.spinner("正在从 AkShare 获取最新行业数据..."):
                try:
                    import akshare as ak
                    from core.database import SessionLocal
                    from core.models import Stock

                    df = ak.stock_zh_a_spot_em()
                    db = SessionLocal()

                    updated = 0
                    for _, row in df.iterrows():
                        code = str(row['代码'])
                        industry = str(row.get('行业', ''))
                        concept = str(row.get('概念板块', ''))

                        stock = db.query(Stock).filter(Stock.code == code).first()
                        if stock:
                            changed = False
                            if industry and industry != 'nan' and industry != stock.industry:
                                stock.industry = industry
                                changed = True
                            if concept and concept != 'nan' and concept != stock.concept:
                                stock.concept = concept
                                changed = True
                            if changed:
                                updated += 1
                        else:
                            exchange = "SH" if code.startswith('6') else ("SZ" if code.startswith('0') or code.startswith('3') else "BJ")
                            new_stock = Stock(
                                code=code,
                                name=str(row['名称']),
                                exchange=exchange,
                                industry=industry if industry and industry != 'nan' else None,
                                concept=concept if concept and concept != 'nan' else None,
                                status="active"
                            )
                            db.add(new_stock)
                            updated += 1

                    db.commit()
                    st.success(f"✅ 更新成功：{updated} 只股票")

                    # 显示统计
                    total = db.query(Stock).count()
                    with_industry = db.query(Stock).filter(Stock.industry != None).count()
                    with_concept = db.query(Stock).filter(Stock.concept != None).count()
                    st.info(f"📊 数据库统计：{with_industry}/{total} 有行业数据，{with_concept}/{total} 有概念数据")
                    db.close()
                except Exception as e:
                    st.error(f"❌ 更新失败：{type(e).__name__}: {str(e)}")
                    with st.expander("💡 为什么更新失败？"):
                        st.markdown("""
                        **AkShare API 说明**：
                        - AkShare 是免费的开源 Python 库，不需要注册或购买
                        - 数据来源于东方财富网，偶尔会出现临时连接问题
                        - 建议等待 15-30 分钟后重试

                        **手动更新方法**：
                        1. 打开命令行（PowerShell 或 CMD）
                        2. 进入项目目录：`cd stock`
                        3. 运行更新命令：`python tasks/update_stock_list.py`

                        或者稍后再试，系统会自动重试 3 次
                        """)

        st.divider()
        st.header("筛选条件")

    # 评分权重说明
    with st.expander("📊 评分体系说明"):
        st.markdown("""
        ### 五维度评分模型

        | 维度 | 权重 | 说明 |
        |------|------|------|
        | 资金流 | 25% | 连续资金流入天数和净流入金额 |
        | 技术指标 | 25% | 均线、MACD、RSI 等技术信号 |
        | 股东户数 | 20% | 筹码集中度变化趋势 |
        | 新闻热度 | 15% | 新闻数量和情绪分析 |
        | 价格动量 | 15% | 相对强度和趋势动量 |

        综合评分 = 各维度分数 × 对应权重
        """)

    # 筛选条件
    col1, col2 = st.columns(2)
    with col1:
        top_n = st.slider("显示 Top N", 5, 50, 20)
    with col2:
        min_score = st.slider("最低评分", 0, 100, 60)

    # 日期选择
    col3, col4 = st.columns(2)
    with col3:
        use_cache = st.checkbox("使用预计算结果", value=True)
    with col4:
        custom_date = st.date_input("选择日期", value=None)

    if st.button("开始智能选股", type="primary"):
        with st.spinner("正在获取推荐股票..."):
            scorer = StockScorer()

            # 确定使用的日期
            trade_date = None
            if custom_date:
                trade_date = custom_date
            elif not use_cache:
                trade_date = date.today()

            # 使用预计算结果
            results = scorer.get_recommendations_from_db(
                trade_date=trade_date,
                top_n=top_n,
                min_score=min_score
            )

            # 如果没有预计算结果，实时计算
            if not results and use_cache:
                st.info("未找到预计算结果，正在实时计算...")
                results = scorer.get_top_stocks(top_n=top_n, min_score=min_score)

            scorer.close()

            if results:
                # 获取实时行情数据用于显示行业信息
                stock_info_map = {}
                api_success = False

                # 尝试多次获取 API 数据
                for attempt in range(3):
                    try:
                        import akshare as ak
                        spot_df = ak.stock_zh_a_spot_em()
                        for _, row in spot_df.iterrows():
                            stock_info_map[str(row['代码'])] = {
                                'latest_price': float(row['最新价']),
                                'change_pct': float(row['涨跌幅']),
                                'industry': str(row.get('行业', '')),
                                'concept': str(row.get('概念板块', ''))
                            }
                        api_success = True
                        break
                    except Exception:
                        if attempt < 2:
                            time.sleep(2 * (attempt + 1))

                # API 失败时，从数据库获取行业和概念信息
                if not api_success:
                    # 从数据库获取行业信息
                    db = SessionLocal()
                    from core.models import Stock
                    db_stock_map = {}
                    for stock in db.query(Stock).all():
                        db_stock_map[stock.code] = {
                            'industry': stock.industry or '',
                            'concept': stock.concept or ''
                        }
                    db.close()

                    # 检查数据库是否有行业数据
                    stocks_with_industry = sum(1 for v in db_stock_map.values() if v.get('industry'))
                    if stocks_with_industry == 0:
                        st.warning("⚠️ 数据库中没有行业数据，请在侧边栏点击'刷新行业/板块数据'按钮更新")
                    else:
                        st.caption(f"ℹ️ 实时 API 不可用，显示数据库中的行业信息（{stocks_with_industry} 只股票有数据）")

                    # 使用数据库数据填充
                    stock_info_map.update(db_stock_map)

                # 显示推荐股票列表
                st.subheader(f"推荐股票 Top {len(results)}")

                # 转换为 DataFrame
                df = pd.DataFrame(results)

                # 展开各维度分数
                for dim in ['capital', 'technical', 'holder', 'news', 'momentum']:
                    df[dim] = df['scores'].apply(lambda x: x.get(dim, 0))

                # 添加股票和行业信息
                df['股票'] = df['stock_code'] + " - " + df['stock_name']

                # 优先使用 API 数据，失败时使用数据库数据（已在上面获取并更新到 stock_info_map）
                df['行业'] = df['stock_code'].apply(lambda x: stock_info_map.get(x, {}).get('industry', ''))
                df['所属板块'] = df['stock_code'].apply(lambda x: stock_info_map.get(x, {}).get('concept', ''))
                df['最新价'] = df['stock_code'].apply(lambda x: stock_info_map.get(x, {}).get('latest_price', 0) if api_success else 0)
                df['涨跌幅'] = df['stock_code'].apply(lambda x: stock_info_map.get(x, {}).get('change_pct', 0) if api_success else 0)

                # 显示表格
                display_cols = ['股票', '行业', '所属板块', '最新价', '涨跌幅', 'total_score', 'capital', 'technical', 'holder', 'news', 'momentum']
                st.dataframe(
                    df[display_cols],
                    use_container_width=True,
                    column_config={
                        "股票": "股票",
                        "行业": "行业",
                        "所属板块": "所属板块",
                        "最新价": st.column_config.NumberColumn("最新价", format="%.2f"),
                        "涨跌幅": st.column_config.NumberColumn("涨跌幅", format="%.1f%%"),
                        "total_score": st.column_config.NumberColumn("综合评分", format="%.1f"),
                        "capital": st.column_config.NumberColumn("资金流", format="%.0f"),
                        "technical": st.column_config.NumberColumn("技术面", format="%.0f"),
                        "holder": st.column_config.NumberColumn("股东户数", format="%.0f"),
                        "news": st.column_config.NumberColumn("新闻", format="%.0f"),
                        "momentum": st.column_config.NumberColumn("动量", format="%.0f")
                    }
                )

                # 显示前 5 名的详细分析
                st.subheader("Top 5 详细分析")
                for i, row in df.head(5).iterrows():
                    with st.container():
                        stock_code = row['stock_code']
                        industry = row.get('行业', '')
                        latest_price = row.get('最新价', 0)
                        change_pct = row.get('涨跌幅', 0)

                        st.markdown(f"#### {row['股票']} (综合评分：{row['total_score']:.1f})")
                        if industry:
                            st.caption(f"行业：{industry} | 最新价：{latest_price:.2f} | 涨跌幅：{change_pct:+.1f}%")

                        # 操作建议
                        score = row['total_score']
                        if score >= 80:
                            st.success(f"**建议**: 强烈推荐 - 综合评分{score:.1f}分，各维度表现优异，可积极关注")
                        elif score >= 70:
                            st.info(f"**建议**: 推荐 - 综合评分{score:.1f}分，整体表现良好，可适当配置")
                        elif score >= 60:
                            st.warning(f"**建议**: 观望 - 综合评分{score:.1f}分，建议等待更好时机")
                        else:
                            st.error(f"**建议**: 谨慎 - 综合评分偏低，建议回避")

                        # 五维度详细分析 - 与持仓管理格式保持一致
                        # 使用 session_state 缓存已获取的详细分析数据，避免重复计算
                        if 'cached_analysis' not in st.session_state:
                            st.session_state.cached_analysis = {}

                        with st.expander("查看五维度详细分析"):
                            stock_code = row['stock_code']

                            # 如果缓存中没有该股票的详细分析，实时计算
                            if stock_code not in st.session_state.cached_analysis:
                                with st.spinner(f"正在计算 {stock_code} 的详细分析..."):
                                    try:
                                        scorer = StockScorer()
                                        analysis_result = scorer.get_stock_analysis(stock_code)
                                        scorer.close()
                                        # get_stock_analysis 返回的数据包含 'details' 键
                                        if analysis_result and 'details' in analysis_result:
                                            st.session_state.cached_analysis[stock_code] = analysis_result['details']
                                        else:
                                            st.session_state.cached_analysis[stock_code] = None
                                    except Exception as e:
                                        st.error(f"计算失败：{e}")
                                        st.session_state.cached_analysis[stock_code] = None

                            details = st.session_state.cached_analysis.get(stock_code)

                            if details and 'capital' in details and 'score' in details.get('capital', {}):
                                # 1. 资金流分析
                                with st.expander(f"💰 资金流分析 - 评分：{details['capital']['score']:.0f}/100 (权重 25%)", expanded=False):
                                    cap = details['capital']
                                    st.markdown(f"**评分：{cap['score']:.0f} 分**")

                                    # 原始数据
                                    st.markdown("**📊 原始数据**")
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("连续流入天数", f"{cap.get('consecutive_days', 0)}天")
                                    with col2:
                                        st.metric("总净流入", f"{cap.get('total_net_inflow', 0) / 10000:.1f}万元")
                                    with col3:
                                        st.metric("日均净流入", f"{cap.get('avg_net_inflow', 0) / 10000:.1f}万元")

                                    # 计算规则
                                    st.markdown("**📐 计算规则**")
                                    st.json(cap.get('scoring_rules', {}))

                                    # 分数构成
                                    st.markdown("**📈 分数构成**")
                                    breakdown = cap.get('score_breakdown', {})
                                    st.write(f"- 连续流入 score: {breakdown.get('consecutive_score', 0)} 分 (满分 40)")
                                    st.write(f"- 净流入金额：{breakdown.get('amount_score', 0)} 分 (满分 60)")

                                    # 每日数据
                                    if cap.get('daily_data'):
                                        st.markdown("**📅 每日资金流数据**")
                                        for day in cap.get('daily_data', []):
                                            net_inflow = day.get('net_inflow', 0) / 10000
                                            st.write(f"- {day.get('date')}: 净流入 {net_inflow:+.1f}万元")

                                # 2. 技术指标分析
                                with st.expander(f"📈 技术指标 - 评分：{details['technical']['score']:.0f}/100 (权重 25%)", expanded=False):
                                    tech = details['technical']
                                    st.markdown(f"**评分：{tech['score']:.0f} 分**")

                                    # 原始数据
                                    st.markdown("**📊 原始数据**")
                                    col1, col2, col3, col4 = st.columns(4)
                                    with col1:
                                        st.metric("MA5", f"{tech.get('ma5', 'N/A')}")
                                    with col2:
                                        st.metric("MA20", f"{tech.get('ma20', 'N/A')}")
                                    with col3:
                                        st.metric("MACD", f"{tech.get('macd', 'N/A')}")
                                    with col4:
                                        st.metric("RSI", f"{tech.get('rsi', 'N/A')}")

                                    # 计算规则
                                    st.markdown("**📐 计算规则**")
                                    st.json(tech.get('scoring_rules', {}))

                                    # 分数构成
                                    st.markdown("**📈 分数构成**")
                                    st.write(f"- 基础分：50 分")
                                    st.write(f"- MA 信号：{tech.get('score_breakdown', {}).get('ma_signal', 0)} 分")
                                    st.write(f"- MACD 信号：{tech.get('score_breakdown', {}).get('macd_signal', 0)} 分")
                                    st.write(f"- RSI 信号：{tech.get('score_breakdown', {}).get('rsi_signal', 0)} 分")

                                    # 技术信号
                                    if tech.get('signals'):
                                        st.markdown("**📉 技术信号**")
                                        st.write(", ".join(tech.get('signals', [])))

                                # 3. 股东户数分析
                                with st.expander(f"👥 股东户数 - 评分：{details['holder']['score']:.0f}/100 (权重 20%)", expanded=False):
                                    holder = details['holder']
                                    st.markdown(f"**评分：{holder['score']:.0f} 分**")

                                    # 原始数据
                                    st.markdown("**📊 原始数据**")
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("股东户数", f"{holder.get('holder_count', 'N/A')}户")
                                    with col2:
                                        change_count = holder.get('change_count')
                                        if change_count is not None and isinstance(change_count, (int, float)):
                                            try:
                                                st.metric("变化数量", f"{change_count:,+}")
                                            except (ValueError, TypeError):
                                                st.metric("变化数量", str(change_count))
                                        else:
                                            st.metric("变化数量", "N/A")
                                    with col3:
                                        st.metric("变化比例", f"{holder.get('change_ratio', 0):+.2f}%")

                                    # 计算规则
                                    st.markdown("**📐 计算规则**")
                                    st.json(holder.get('scoring_rules', {}))

                                    # 分数构成
                                    st.markdown("**📈 分数构成**")
                                    st.write(f"- 基础分：50 分")
                                    breakdown = holder.get('score_breakdown', {})
                                    st.write(f"- 趋势变化：{breakdown.get('trend_change', 0)} 分")
                                    st.write(f"- 连续减少奖励：{breakdown.get('consecutive_bonus', 0)} 分")

                                    # 趋势
                                    if holder.get('trend'):
                                        st.markdown("**📉 趋势**")
                                        st.write(", ".join(holder.get('trend', [])))

                                # 4. 新闻情绪分析
                                with st.expander(f"📰 新闻情绪 - 评分：{details['news']['score']:.0f}/100 (权重 15%)", expanded=False):
                                    news = details['news']
                                    st.markdown(f"**评分：{news['score']:.0f} 分**")

                                    # 原始数据
                                    st.markdown("**📊 原始数据**")
                                    col1, col2, col3, col4 = st.columns(4)
                                    with col1:
                                        st.metric("新闻数量", f"{news.get('news_count', 0)}篇")
                                    with col2:
                                        st.metric("平均情绪", f"{news.get('avg_sentiment', 0):.2f}")
                                    with col3:
                                        st.metric("正面新闻", f"{news.get('positive_count', 0)}篇")
                                    with col4:
                                        st.metric("负面新闻", f"{news.get('negative_count', 0)}篇")

                                    # 计算规则
                                    st.markdown("**📐 计算规则**")
                                    st.json(news.get('scoring_rules', {}))

                                    # 分数构成
                                    st.markdown("**📈 分数构成**")
                                    breakdown = news.get('score_breakdown', {})
                                    st.write(f"- 情绪分数：{breakdown.get('sentiment_score', 0)} 分")
                                    st.write(f"- 数量奖励：{breakdown.get('count_bonus', 0)} 分 (满分 20)")

                                    # 最近新闻
                                    if news.get('recent_news'):
                                        st.markdown("**📝 最近新闻**")
                                        for n in news.get('recent_news', [])[:5]:
                                            sentiment_icon = "🟢" if n.get('sentiment') == 'positive' else "🔴" if n.get('sentiment') == 'negative' else "🟡"
                                            st.write(f"{sentiment_icon} {n.get('title', '')} ({n.get('sentiment', '')}, 情绪分:{n.get('sentiment_score', 0):.2f})")

                                # 5. 价格动量分析
                                with st.expander(f"📊 价格动量 - 评分：{details['momentum']['score']:.0f}/100 (权重 15%)", expanded=False):
                                    mom = details['momentum']
                                    st.markdown(f"**评分：{mom['score']:.0f} 分**")

                                    # 原始数据
                                    st.markdown("**📊 原始数据**")
                                    col1, col2, col3, col4 = st.columns(4)
                                    with col1:
                                        st.metric("当前价", f"{mom.get('close', 'N/A')}")
                                    with col2:
                                        st.metric("MA20", f"{mom.get('ma20', 'N/A')}")
                                    with col3:
                                        st.metric("5 日涨幅", f"{mom.get('change_5d', 0):+.1f}%")
                                    with col4:
                                        st.metric("20 日涨幅", f"{mom.get('change_20d', 0):+.1f}%")

                                    # 计算规则
                                    st.markdown("**📐 计算规则**")
                                    st.json(mom.get('scoring_rules', {}))

                                    # 分数构成
                                    st.markdown("**📈 分数构成**")
                                    st.write(f"- 基础分：50 分")
                                    breakdown = mom.get('score_breakdown', {})
                                    st.write(f"- MA20 信号：{breakdown.get('ma20_signal', 0)} 分")
                                    st.write(f"- 20 日涨幅：{breakdown.get('change_20d_signal', 0)} 分")

                                    # 价格趋势
                                    if mom.get('price_history'):
                                        st.markdown("**📉 价格趋势**")
                                        for p in mom.get('price_history', [])[:5]:
                                            st.write(f"- {p.get('date')}: {p.get('close'):.2f}")

                                    # 动量信号
                                    if mom.get('signals'):
                                        st.markdown("**📉 动量信号**")
                                        st.write(", ".join(mom.get('signals', [])))
                            else:
                                # 数据库推荐模式，显示简化版分析
                                st.info("💡 数据库推荐模式 - 显示简化版分析")
                                st.markdown(f"**💰 资金流**: {row.get('capital', 0):.0f}/100")
                                st.markdown(f"**📈 技术指标**: {row.get('technical', 0):.0f}/100")
                                st.markdown(f"**👥 股东户数**: {row.get('holder', 0):.0f}/100")
                                st.markdown(f"**📰 新闻情绪**: {row.get('news', 0):.0f}/100")
                                st.markdown(f"**📊 价格动量**: {row.get('momentum', 0):.0f}/100")

                        st.divider()

            else:
                st.warning("未找到符合条件的股票，请尝试降低筛选条件")

    # 个股分析
    st.divider()
    st.subheader("个股详细分析")

    stock_code = st.text_input("输入股票代码进行详细分析", key="scorer_stock")

    if st.button("分析个股"):
        if stock_code:
            scorer = StockScorer()
            result = scorer.get_stock_analysis(stock_code)
            scorer.close()

            if result:
                st.markdown(f"#### {result['stock_code']} - {result['stock_name']}")

                # 综合评分
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("综合评分", f"{result['total_score']:.1f}")

                # 各维度分数
                scores = result.get('scores', {})
                col_scores = st.columns(5)
                labels = ["资金流", "技术面", "股东户", "新闻", "动量"]
                for i, (key, label) in enumerate(zip(['capital', 'technical', 'holder', 'news', 'momentum'], labels)):
                    with col_scores[i]:
                        score = scores.get(key, 0)
                        st.metric(label, f"{score:.0f}")

                # 雷达图
                radar_data = {
                    "维度": ["资金流", "技术指标", "股东户数", "新闻热度", "价格动量"],
                    "分数": [scores.get('capital', 0), scores.get('technical', 0),
                           scores.get('holder', 0), scores.get('news', 0), scores.get('momentum', 0)]
                }
                st.bar_chart(pd.DataFrame(radar_data).set_index("维度"))

                # 投资建议
                st.markdown("**投资建议**")
                if result['total_score'] >= 80:
                    st.success("⭐⭐⭐⭐⭐ 强烈推荐 (综合评分≥80)")
                elif result['total_score'] >= 70:
                    st.success("⭐⭐⭐⭐ 推荐 (综合评分≥70)")
                elif result['total_score'] >= 60:
                    st.info("⭐⭐⭐ 关注 (综合评分≥60)")
                else:
                    st.warning("暂不推荐 (综合评分<60)")
            else:
                st.warning("暂无该股票数据")

# 股东户数
elif page == "股东户数":
    st.title("👥 股东户数变化分析")

    menu = st.tabs(["个股查询", "筹码集中"])

    with menu[0]:
        st.subheader("个股股东户数查询")

        stock_code = st.text_input("输入股票代码 (如 600519)", key="holder_stock")

        if st.button("查询"):
            if stock_code:
                analyzer = ShareholderAnalyzer()
                summary = analyzer.get_holder_count_summary(stock_code)
                trend_data = analyzer.get_holder_count_trend(stock_code, limit=10)
                analyzer.close()

                if summary:
                    # 显示股票名称
                    if summary.get('stock_name'):
                        st.subheader(f"{summary['stock_code']} - {summary['stock_name']}")

                    # 基本信息
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("最新股东户数", f"{summary.get('holder_count', 'N/A'):,}" if summary.get('holder_count') is not None else "N/A")
                    with col2:
                        change_count = summary.get('change_count')
                        if change_count is not None:
                            change_icon = "📉" if change_count < 0 else "📈"
                            try:
                                st.metric("较上期变化", f"{change_icon} {change_count:,}户")
                            except (ValueError, TypeError):
                                st.metric("较上期变化", f"{change_icon} {change_count}户")
                        else:
                            st.metric("较上期变化", "N/A")
                    with col3:
                        st.metric("变化比例", f"{summary.get('change_ratio', 0):.2f}%")
                    with col4:
                        avg_holdings = summary.get('avg_holdings')
                        if avg_holdings is not None:
                            st.metric("户均持股", f"{avg_holdings:,.0f}")
                        else:
                            st.metric("户均持股", "N/A")

                    # 趋势判断
                    if summary['trend'] == 'concentrated':
                        st.success("✅ 筹码集中（股东户数减少）")
                    elif summary['trend'] == 'dispersed':
                        st.warning("⚠️ 筹码分散（股东户数增加）")
                    else:
                        st.info("ℹ️ 筹码稳定")

                    # 趋势图表
                    if trend_data:
                        df = pd.DataFrame(trend_data)
                        df['trade_date'] = pd.to_datetime(df['trade_date'])
                        df = df.sort_values('trade_date')

                        st.subheader("股东户数变化趋势")
                        st.line_chart(df.set_index('trade_date')['holder_count'])

                        st.subheader("详细数据")
                        st.dataframe(
                            df[['trade_date', 'holder_count', 'change_count', 'change_ratio', 'avg_holdings']],
                            use_container_width=True,
                            column_config={
                                "trade_date": "统计日期",
                                "holder_count": "股东户数",
                                "change_count": "较上期变化",
                                "change_ratio": "变化比例 (%)",
                                "avg_holdings": "户均持股"
                            }
                        )
                else:
                    st.warning("暂无股东户数数据")
            else:
                st.warning("请输入股票代码")

    with menu[1]:
        st.subheader("连续筹码集中股票")

        min_days = st.slider("连续减少天数", 2, 10, 3)
        min_ratio = st.number_input("最小减少比例 (%)", min_value=-20.0, max_value=0.0, value=-5.0)

        if st.button("筛选筹码集中股票"):
            analyzer = ShareholderAnalyzer()
            results = analyzer.get_all_consecutive_concentrated(min_days, min_ratio)
            analyzer.close()

            if results:
                df = pd.DataFrame(results)
                # 添加股票名称列
                if 'stock_code' in df.columns and 'stock_name' in df.columns:
                    df['股票'] = df['stock_code'] + " - " + df['stock_name']
                    display_cols = ['股票', 'consecutive_days', 'total_change_ratio', 'latest_holder_count', 'latest_change_ratio', 'latest_trade_date']
                    display_cols_config = {
                        "股票": "股票",
                        "consecutive_days": "连续减少天数",
                        "total_change_ratio": "累计变化比例 (%)",
                        "latest_holder_count": "最新股东户数",
                        "latest_change_ratio": "最新变化比例 (%)",
                        "latest_trade_date": "最新统计日期"
                    }
                else:
                    display_cols = df.columns.tolist()
                    display_cols_config = {}

                st.dataframe(
                    df[display_cols] if all(col in df.columns for col in display_cols) else df,
                    use_container_width=True,
                    column_config=display_cols_config
                )
            else:
                st.warning("未找到符合条件的股票")


# 大宗商品监控
elif page == "大宗商品":
    st.title("🛢️ 大宗商品价格监控")
    st.markdown("实时监控大宗商品价格，发现涨跌幅超过 10% 的机会")

    # 初始化监控器
    @st.cache_resource
    def get_monitor():
        return CommodityMonitor()

    monitor = get_monitor()

    # 预警阈值设置
    st.sidebar.subheader("预警设置")
    alert_threshold = st.sidebar.slider("涨跌幅预警阈值 (%)", 5.0, 50.0, 10.0, 0.5)

    # 获取数据
    try:
        summary = monitor.get_all_commodities_summary()
        alerts = monitor.get_commodities_with_alert(threshold=alert_threshold)
    except Exception as e:
        st.error(f"获取数据失败：{e}")
        summary = []
        alerts = []

    # 显示预警信息
    if alerts:
        st.subheader(f"🚨 价格预警 (涨跌幅 > {alert_threshold}%)")
        alert_cols = st.columns(min(len(alerts), 4))
        for idx, alert in enumerate(alerts[:8]):
            col = alert_cols[idx % 4]
            with col:
                # 显示中文名称
                display_name = alert.get('chinese_name', alert['commodity_name'])
                change_dir = "📈" if alert['price_change'] > 0 else "📉"
                change_sign = "+" if alert['price_change'] > 0 else ""
                st.metric(
                    label=f"{display_name}",
                    value=f"{alert['spot_price']:.2f}",
                    delta=f"{change_dir} {change_sign}{alert['price_change']:.1f}%"
                )
        st.markdown("")

    # 主界面
    menu = st.tabs(["全部商品", "重点关注", "预警列表"])

    with menu[0]:
        st.subheader("所有大宗商品价格")

        if summary:
            df = pd.DataFrame(summary)

            # 格式化显示
            display_df = df.copy()
            # 优先使用中文名称显示
            display_df['display_name'] = display_df.apply(
                lambda x: x['chinese_name'] if x.get('chinese_name') else x['commodity_name'],
                axis=1
            )
            display_df['涨跌幅'] = display_df['price_change_1d'].apply(lambda x: f"{x:+.2f}%")
            display_df['重点'] = display_df['is_key_commodity'].apply(lambda x: '⭐' if x else '')

            # 按涨跌幅排序
            display_df['abs_change'] = display_df['price_change_1d'].abs()
            display_df = display_df.sort_values('abs_change', ascending=False)
            display_df = display_df.drop('abs_change', axis=1)

            st.dataframe(
                display_df[['重点', 'display_name', 'spot_price', '涨跌幅', 'dominant_contract', 'dominant_contract_price']],
                use_container_width=True,
                column_config={
                    "重点": "关注",
                    "display_name": "商品名称",
                    "spot_price": "现货价格",
                    "涨跌幅": "涨跌幅",
                    "dominant_contract": "主力合约",
                    "dominant_contract_price": "主力合约价格"
                },
                hide_index=True
            )
        else:
            st.warning("暂无数据")

    with menu[1]:
        st.subheader("重点关注大宗商品")

        if summary:
            key_commodities = [item for item in summary if item['is_key_commodity']]

            if key_commodities:
                # 分成 4 列显示
                cols = st.columns(4)
                for idx, item in enumerate(key_commodities):
                    col = cols[idx % 4]
                    with col:
                        # 显示中文名称
                        display_name = item.get('chinese_name', item['commodity_name'])
                        change_dir = "📈" if item['price_change_1d'] > 0 else "📉" if item['price_change_1d'] < 0 else "➡️"
                        change_sign = "+" if item['price_change_1d'] > 0 else ""
                        st.metric(
                            label=f"{display_name}",
                            value=f"{item['spot_price']:.2f}",
                            delta=f"{change_dir} {change_sign}{item['price_change_1d']:.1f}%"
                        )

                # 详细数据表
                st.markdown("---")
                st.subheader("详细数据")

                df = pd.DataFrame(key_commodities)
                # 优先使用中文名称显示
                df['display_name'] = df.apply(
                    lambda x: x['chinese_name'] if x.get('chinese_name') else x['commodity_name'],
                    axis=1
                )
                df['涨跌幅'] = df['price_change_1d'].apply(lambda x: f"{x:+.2f}%")
                df['abs_change'] = df['price_change_1d'].abs()
                df = df.sort_values('abs_change', ascending=False)
                df = df.drop('abs_change', axis=1)

                st.dataframe(
                    df[['display_name', 'spot_price', '涨跌幅', 'near_contract', 'near_contract_price',
                        'dominant_contract', 'dominant_contract_price']],
                    use_container_width=True,
                    column_config={
                        "display_name": "商品名称",
                        "spot_price": "现货价格",
                        "涨跌幅": "涨跌幅",
                        "near_contract": "近月合约",
                        "near_contract_price": "近月价格",
                        "dominant_contract": "主力合约",
                        "dominant_contract_price": "主力价格"
                    },
                    hide_index=True
                )
            else:
                st.info("暂无重点关注商品")
        else:
            st.warning("暂无数据")

    with menu[2]:
        st.subheader(f"价格预警列表 (>{alert_threshold}%)")

        if alerts:
            df = pd.DataFrame(alerts)
            # 优先使用中文名称显示
            df['display_name'] = df.apply(
                lambda x: x['chinese_name'] if x.get('chinese_name') else x['commodity_name'],
                axis=1
            )
            df['涨跌幅'] = df['price_change'].apply(lambda x: f"{x:+.2f}%")
            df['类型'] = df['price_change'].apply(lambda x: '上涨' if x > 0 else '下跌')
            df['关注'] = df['is_key_commodity'].apply(lambda x: '⭐ 重点' if x else '-')

            # 分开显示上涨和下跌
            gainers = df[df['price_change'] > 0].sort_values('price_change', ascending=False)
            losers = df[df['price_change'] < 0].sort_values('price_change', ascending=True)

            if not gainers.empty:
                st.markdown("### 📈 上涨预警")
                st.dataframe(
                    gainers[['关注', 'display_name', 'spot_price', '涨跌幅', 'trade_date']],
                    use_container_width=True,
                    column_config={
                        "关注": "关注",
                        "display_name": "商品名称",
                        "spot_price": "现货价格",
                        "涨跌幅": "涨跌幅",
                        "trade_date": "日期"
                    },
                    hide_index=True
                )

            if not losers.empty:
                st.markdown("### 📉 下跌预警")
                st.dataframe(
                    losers[['关注', 'display_name', 'spot_price', '涨跌幅', 'trade_date']],
                    use_container_width=True,
                    column_config={
                        "关注": "关注",
                        "display_name": "商品名称",
                        "spot_price": "现货价格",
                        "涨跌幅": "涨跌幅",
                        "trade_date": "日期"
                    },
                    hide_index=True
                )

            # 显示预警统计
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("预警商品数量", len(alerts))
            with col2:
                gains = len([a for a in alerts if a['price_change'] > 0])
                st.metric("上涨预警", gains)
            with col3:
                losses = len([a for a in alerts if a['price_change'] < 0])
                st.metric("下跌预警", losses)
        else:
            st.success(f"暂无涨跌幅超过 {alert_threshold}% 的大宗商品")
