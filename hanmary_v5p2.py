import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import platform
from datetime import datetime, timedelta
import pytz
import json
import os

# ==========================================
# 0. Font & Global Settings
# ==========================================
@st.cache_resource
def font_setting():
    system_name = platform.system()
    if system_name == 'Windows':
        plt.rc('font', family='Malgun Gothic')
    elif system_name == 'Darwin':
        plt.rc('font', family='AppleGothic')
    else:
        plt.rc('font', family='NanumGothic') 
    plt.rcParams['axes.unicode_minus'] = False

font_setting()

PORTFOLIO_FILE = "custom_portfolios.json"
DEFAULT_PORTFOLIOS = {
    "Slot_A": {"name": "미국 핵심 (A)", "tickers": "MSTR, QQQ, NVDA, PLTR, TSLA"},
    "Slot_B": {"name": "한국/ETF (B)", "tickers": "005930.KS=Samsung Elec, 005380.KS=Hyundai Motors, 006800.KS=Mirae Asset, 139230.KS=Tiger Heavy, 438900.KS=HANARO K-Food, 360750.KS=Tiger S&P500, 102110.KS=Tiger 200, 139220.KS=Tiger Construction, 453850.KS=Tiger India, 411060.KS=Tiger Gold"},
    "Slot_C": {"name": "관심주 (C)", "tickers": ""},
    "Slot_D": {"name": "단기 관찰 (D)", "tickers": ""}
}

def load_portfolios():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return DEFAULT_PORTFOLIOS.copy()
    return DEFAULT_PORTFOLIOS.copy()

def save_portfolios(data):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# 1. Design & Core Rules
# ==========================================
CATEGORY_COLORS = {
    'Macro': '#C29200', 'Crypto': '#FF5E00', 'US Tech': '#004A99', 
    'K-Market': '#228B22', 'Others': '#777777'
}

TICKERS = {
    'Gold': 'GC=F', 'Silver': 'SI=F', 'Copper': 'HG=F', 'BTC': 'BTC-USD', 'ETH': 'ETH-USD',
    'KOSPI': '^KS11', 'NASDAQ': '^IXIC', 'S&P 500': '^GSPC', 'Dollar Index': 'DX-Y.NYB', 'USD/KRW': 'KRW=X',
    'NVDA': 'NVDA', 'AAPL': 'AAPL', 'MSFT': 'MSFT', 'AMZN': 'AMZN', 'GOOG': 'GOOG', 
    'TSMC': 'TSM', 'AVGO': 'AVGO', 'TSLA': 'TSLA', 'META': 'META', 
    'Samsung': '005930.KS', 'SK Hynix': '000660.KS', 'QQQ': 'QQQ', 'MSTR': 'MSTR',
    'TIGER 200': '102110.KS', 'TIGER Heavy': '139230.KS', 'TIGER Nasdaq': '133690.KS', 
    'TIGER US Tech': '381170.KS', 'TIGER Gold': '411060.KS'
}

SHARES_B = {
    'Gold': 6.83, 'Silver': 56.0, 'AAPL': 15.4, 'NVDA': 24.5, 'MSFT': 7.43, 'AMZN': 10.39, 
    'GOOG': 12.43, 'TSMC': 5.18, 'AVGO': 4.63, 'TSLA': 3.18, 'META': 2.54, 'BTC': 0.01999,
    'Samsung': 6.791, 'PLTR': 2.3, 'ETH': 0.12, 'SK Hynix': 0.728
}

def get_text_color(change_val):
    if abs(change_val) < 0.005: return 'black'
    return 'blue' if change_val > 0 else 'red'

def format_value_auto(value):
    if value >= 100: return f"{value:,.0f}"
    if value >= 10: return f"{value:,.1f}"
    return f"{value:,.2f}"

def format_price(value, name, category='Others'):
    krw_assets = ['Samsung', 'SK Hynix', 'Tiger']
    no_sym_assets = ['KOSPI', 'USD/KRW', 'Dollar Index']
    if any(x in name for x in no_sym_assets): prefix = ""
    elif any(x in name for x in krw_assets) or category == 'K-Market' or 'Tiger' in name or 'HANARO' in name: prefix = "₩"
    else: prefix = "$"
    return f"{prefix}{format_value_auto(value)}"

def get_korea_time():
    return datetime.now(pytz.utc).astimezone(pytz.timezone('Asia/Seoul'))

# ==========================================
# 2. Data Engine 
# ==========================================
@st.cache_data(ttl=300) 
def download_all_data():
    df = yf.download(list(TICKERS.values()), period="10y", interval="1d", progress=False)
    close_df, high_df = parse_downloaded_data(df)
    return close_df, high_df, df

@st.cache_data(ttl=300)
def download_extra_data(tickers_tuple):
    if not tickers_tuple: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = yf.download(list(tickers_tuple), period="10y", interval="1d", progress=False)
    close_df, high_df = parse_downloaded_data(df)
    return close_df, high_df, df

def parse_downloaded_data(df):
    if df.empty: return pd.DataFrame(), pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        level = 0 if 'Close' in df.columns.get_level_values(0) else 1
        close_df = df.xs('Close', axis=1, level=level)
        high_df = df.xs('High', axis=1, level=level)
    else:
        close_df = pd.DataFrame(df['Close'])
        high_df = pd.DataFrame(df['High'])
    close_df.index = pd.to_datetime(close_df.index).tz_localize(None)
    high_df.index = pd.to_datetime(high_df.index).tz_localize(None)
    return close_df, high_df

def process_data(target_names, period, status_mode, close_df, high_df, custom_mapping=None):
    if custom_mapping is None: custom_mapping = {}
    res = []
    kst_now = get_korea_time()
    today_kst = kst_now.date()
    usd_krw = float(close_df['KRW=X'].dropna().iloc[-1]) if 'KRW=X' in close_df.columns else 1350.0

    for name in target_names:
        ticker = TICKERS.get(name) or custom_mapping.get(name)
        if not ticker or ticker not in close_df.columns: continue
        series = close_df[ticker].dropna()
        if series.empty: continue
        
        if name in ['Samsung', 'SK Hynix', 'KOSPI'] or '.KS' in ticker or '.KQ' in ticker: cat = 'K-Market'
        elif name in ['BTC', 'ETH'] or '-USD' in ticker: cat = 'Crypto'
        elif name in ['Gold', 'Silver', 'Copper', 'Dollar Index', 'USD/KRW', 'USO', 'BNO'] or '=F' in ticker: cat = 'Macro'
        elif name in ['TSMC']: cat = 'Others'
        elif name in ['NASDAQ', 'S&P 500'] or (ticker.isalpha() and ticker.isupper()): cat = 'US Tech'
        else: cat = 'Others'

        if status_mode == 'ATH':
            curr, ath = float(series.iloc[-1]), float(high_df[ticker].dropna().max())
            change = ((curr - ath) / ath) * 100 if ath > 0 else 0
            curr_date, base_date = series.index[-1].date(), series.index[-1].date()
            
        elif status_mode == 'Completed' and period == 'Daily':
            if cat == 'Crypto':
                offset = 2 if kst_now.hour < 9 else 1
                t_date = today_kst - timedelta(days=offset)
            elif cat in ['US Tech', 'Macro', 'Others']:
                offset = 2 if kst_now.hour < 6 else 1
                t_date = today_kst - timedelta(days=offset)
                while t_date.weekday() > 4: t_date -= timedelta(days=1)
            else:
                offset = 1 if (kst_now.hour < 15 or (kst_now.hour == 15 and kst_now.minute < 30)) else 0
                t_date = today_kst - timedelta(days=offset)
                while t_date.weekday() > 4: t_date -= timedelta(days=1)
                
            curr_s = series[series.index.date <= t_date]
            if curr_s.empty: continue
            curr = float(curr_s.iloc[-1])
            curr_date = curr_s.index[-1].date()
            
            base_s = series[series.index.date < curr_date]
            base = float(base_s.iloc[-1]) if not base_s.empty else curr
            change = ((curr - base) / base) * 100 if base > 0 else 0
            base_date = base_s.index[-1].date() if not base_s.empty else curr_date
            
        else:
            v_series = series[series.index.date < today_kst] if status_mode == 'Completed' else series 
            if v_series.empty: continue
            curr, curr_date = float(v_series.iloc[-1]), v_series.index[-1].date()
            
            if status_mode == 'Cycle':
                t_base = curr_date - timedelta(days={'Daily':1, 'Weekly':7, 'Monthly':30, 'Yearly':365}.get(period, 0))
                b_series = series[series.index.date <= t_base]
            else:
                if period == 'Daily': b_series = series[series.index.date < curr_date]
                elif period == 'Weekly': b_series = series[series.index.date < (datetime.combine(curr_date, datetime.min.time()) - timedelta(days=curr_date.weekday())).date()]
                elif period == 'Monthly': b_series = series[series.index.date < curr_date.replace(day=1)]
                elif period == 'Yearly': b_series = series[series.index.date < curr_date.replace(month=1, day=1)]
                else: b_series = series.iloc[0:1]
                
            base = float(b_series.iloc[-1]) if not b_series.empty else curr
            change = ((curr - base) / base) * 100 if base > 0 else 0
            base_date = b_series.index[-1].date() if not b_series.empty else curr_date
        
        mcap = ((curr * SHARES_B[name]) / (usd_krw if cat == 'K-Market' else 1)) / 1000 if name in SHARES_B else 0
        res.append({'name': name, 'price': curr, 'change': change, 'category': cat, 'curr_date': curr_date, 'base_date': base_date, 'mcap': mcap})
    return pd.DataFrame(res)

def format_top13_df(df, t_name):
    df = df.sort_values('mcap', ascending=False).reset_index(drop=True)
    s_idx_list = df.index[df['name'] == 'Samsung Elec'].tolist() + df.index[df['name'] == 'Samsung'].tolist()
    if s_idx_list:
        s_idx = s_idx_list[0]
        if s_idx <= 11:
            df = df.head(12).copy()
            df['display_rank'] = [f"{i+1:02d}" for i in range(len(df))]
            t_name_display = "Global Top 12"
        else:
            s_row = df.iloc[s_idx:s_idx+1]
            df = df.drop(s_idx)
            df = pd.concat([df.head(12), s_row]).reset_index(drop=True) 
            ranks = [f"{i+1:02d}" for i in range(12)] + ["00"] 
            df['display_rank'] = ranks
            t_name_display = "Global Top 12+1"
    else:
        df['display_rank'] = [f"{i+1:02d}" for i in range(len(df))]
        t_name_display = "Global Top"
    return df, t_name_display

def sort_by_category(df):
    cat_order = {'US Tech': 1, 'K-Market': 2, 'Macro': 3, 'Crypto': 4, 'Others': 5}
    name_order = {'Gold': 1, 'Silver': 2, 'Copper': 3}
    df['cat_rank'] = df['category'].map(cat_order).fillna(99)
    df['name_rank'] = df['name'].map(name_order).fillna(99)
    return df.sort_values(['cat_rank', 'name_rank', 'name']).drop(['cat_rank', 'name_rank'], axis=1).reset_index(drop=True)

# ==========================================
# 3. Chart Drawing 
# ==========================================
def get_pct_str(val, max_abs=1.0):
    if abs(val) < 0.005: return "0%"
    if abs(val) >= 100: dec = 0
    elif max_abs < 0.2: dec = 2
    else: dec = 1
    sign = '▲' if val > 0 else '▼'
    return f"{sign}{abs(val):.{dec}f}%"

def format_pct_text(val, max_abs=1.0):
    if abs(val) < 0.005: return "0%"
    if abs(val) >= 100: dec = 0
    elif max_abs < 0.2: dec = 2
    else: dec = 1
    sign = '+' if val > 0 else '-'
    return f"{sign}{abs(val):.{dec}f}%"

def style_axes(ax):
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color('#CCCCCC')
        spine.set_linewidth(1.5)
    ax.tick_params(axis='x', labelsize=8, rotation=0) 
    ax.tick_params(axis='y', labelsize=8)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(nbins=4, prune='both'))

def draw_top13_chart(df, main_title, sub_title, is_ath=False):
    if df.empty: return
    if is_ath:
        draw_normal_chart(df, main_title, sub_title)
        return

    df['plot_name'] = df['name'].str.replace(' ', '\n', n=1)
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10, 4.5), gridspec_kw={'height_ratios': [1, 3]})
    fig.subplots_adjust(hspace=0.05)
    fig.patch.set_facecolor('white')

    colors = [CATEGORY_COLORS.get(c, '#777777') for c in df['category']]
    ax1.bar(df['plot_name'], df['mcap'], color=colors, width=0.6)
    ax2.bar(df['plot_name'], df['mcap'], color=colors, width=0.6)
    
    ax1_upper = int(np.ceil((df[df['mcap'] > 10]['mcap'].max() if not df[df['mcap'] > 10].empty else 34) + 4.0))
    ax1.set_ylim(30, ax1_upper)
    ax2.set_ylim(int(np.floor((df[df['mcap'] < 20]['mcap'].min() if not df[df['mcap'] < 20].empty else 0))), (df[df['mcap'] < 20]['mcap'].max() if not df[df['mcap'] < 20].empty else 5.5) + 1.5)
    
    style_axes(ax1)
    style_axes(ax2)
    ax1.spines['bottom'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax1.xaxis.set_visible(False)

    wave_x = np.linspace(0, 1, 100)
    ax1.plot(wave_x, np.sin(20 * np.pi * wave_x) * 0.008, transform=ax1.transAxes, color='#CCCCCC', lw=1.5, clip_on=False)
    ax2.plot(wave_x, 1 + np.sin(20 * np.pi * wave_x) * 0.008, transform=ax2.transAxes, color='#CCCCCC', lw=1.5, clip_on=False)

    max_abs_change = df['change'].abs().max() if not df.empty else 1.0
    max_date = df['curr_date'].max() if not df.empty else None

    for i, r in df.iterrows():
        txt_col = get_text_color(r['change'])
        pct_str = get_pct_str(r['change'], max_abs_change)
        
        # [수정] 월/일(3/2) 형식으로 예외 날짜 표기
        date_str = ""
        if max_date and r['curr_date'] < max_date:
            date_str = f"\n({r['curr_date'].month}/{r['curr_date'].day})"
            
        lbl = f"{format_value_auto(r['mcap'])}T\n{pct_str}{date_str}"
        (ax1 if r['mcap'] > 10 else ax2).text(i, r['mcap'] + (0.8 if r['mcap'] > 10 else 0.3), lbl, ha='center', va='bottom', fontsize=8, fontweight='bold', color=txt_col)

    title_y = 1.05
    ax1.text(0.48, title_y, main_title, transform=ax1.transAxes, ha='right', va='bottom', fontsize=15, fontweight='bold', color='black')
    ax1.text(0.50, title_y, f"({sub_title})", transform=ax1.transAxes, ha='left', va='bottom', fontsize=11, color='gray')
    
    lp = [mpatches.Patch(color=v, label=k) for k, v in CATEGORY_COLORS.items() if k in df['category'].values]
    ax1.legend(handles=lp, loc='upper right', frameon=True, fontsize=8, facecolor='white', edgecolor='#CCCCCC', ncol=len(lp))
        
    plt.tight_layout()
    st.pyplot(fig)

def draw_normal_chart(df, main_title, sub_title):
    if df.empty: return
    fig, ax = plt.subplots(figsize=(10, 4.0))
    fig.patch.set_facecolor('white')
    df['plot_name'] = df['name'].str.replace(' ', '\n', n=1)
    
    colors = [CATEGORY_COLORS.get(c, '#777777') for c in df['category']]
    bars = ax.bar(df['plot_name'], df['change'], color=colors, width=0.6)
    ax.axhline(0, color='black', linewidth=1.0)
    
    style_axes(ax)
    
    max_abs_change = df['change'].abs().max() if not df.empty else 1.0
    max_date = df['curr_date'].max() if not df.empty else None
    
    for i, bar in enumerate(bars):
        r = df.iloc[i]
        h = bar.get_height()
        va, offset = ('bottom', 3) if h >= 0 else ('top', -3)
        txt_col = get_text_color(h)
        pct_str = get_pct_str(h, max_abs_change)

        # [수정] 월/일(3/2) 형식으로 예외 날짜 표기
        date_str = ""
        if max_date and r['curr_date'] < max_date:
            date_str = f"\n({r['curr_date'].month}/{r['curr_date'].day})"
            
        final_text = f"{pct_str}{date_str}"
        ax.annotate(final_text, xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, offset), textcoords="offset points", ha='center', va=va, fontweight='bold', fontsize=8, color=txt_col)

    title_y = 1.05
    ax.text(0.48, title_y, main_title, transform=ax.transAxes, ha='right', va='bottom', fontsize=15, fontweight='bold', color='black')
    ax.text(0.50, title_y, f"({sub_title})", transform=ax.transAxes, ha='left', va='bottom', fontsize=11, color='gray')
    
    lp = [mpatches.Patch(color=v, label=k) for k, v in CATEGORY_COLORS.items() if k in df['category'].values]
    ax.legend(handles=lp, loc='upper right', frameon=True, fontsize=8, facecolor='white', edgecolor='#CCCCCC', ncol=len(lp))
        
    if max_abs_change < 0.2: dec_y = 2
    elif max_abs_change < 2.0: dec_y = 1
    else: dec_y = 0
    
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100, decimals=dec_y, symbol='%'))
    margin = max(abs(df['change'].min()), abs(df['change'].max())) * 0.3 or 1
    ax.set_ylim(df['change'].min() - margin, df['change'].max() + margin) 
    
    plt.tight_layout()
    st.pyplot(fig)

def generate_twitter_text(df, title, date_str, is_top=False):
    txt = f"[{title}]\n({date_str})\n\n"
    max_abs = df['change'].abs().max() if not df.empty else 1.0
    max_date = df['curr_date'].max() if not df.empty else None
    
    if is_top and 'display_rank' in df.columns:
        for _, r in df.iterrows():
            mcap_str = f"{format_value_auto(r['mcap'])}T"
            price_str = format_price(r['price'], r['name'], r['category'])
            change_str = format_pct_text(r['change'], max_abs)
            
            # [수정] 텍스트 복사 시 월/일(3/2) 표기
            date_flag = f" [{r['curr_date'].month}/{r['curr_date'].day}]" if max_date and r['curr_date'] < max_date else ""
            txt += f"{r['display_rank']}. {r['name']} {mcap_str} ({price_str}, {change_str}){date_flag}\n"
        txt += "\n#Investing #MarketUpdate #GlobalTop"
        return txt
        
    for i, (_, r) in enumerate(df.iterrows(), 1):
        price_str = format_price(r['price'], r['name'], r['category'])
        change_str = format_pct_text(r['change'], max_abs)
        
        # [수정] 텍스트 복사 시 월/일(3/2) 표기
        date_flag = f" [{r['curr_date'].month}/{r['curr_date'].day}]" if max_date and r['curr_date'] < max_date else ""
        txt += f"{i}. {r['name']} {price_str} ({change_str}){date_flag}\n"
    txt += "\n#Investing #MarketUpdate #Portfolio"
    return txt

def draw_deep_dive_chart(ticker_symbol, raw_df, ticker_name, plot_days):
    try:
        df = raw_df.xs(ticker_symbol, axis=1, level=1).copy() if isinstance(raw_df.columns, pd.MultiIndex) and ticker_symbol in raw_df.columns.get_level_values(1) else \
             raw_df.xs(ticker_symbol, axis=1, level=0).copy() if isinstance(raw_df.columns, pd.MultiIndex) else raw_df.copy()
        
        df = df.dropna(subset=['Close'])
        if df.empty: return st.warning("No data found.")
        df.index = pd.to_datetime(df.index).tz_localize(None)

        df['SMA50'] = df['Close'].rolling(50).mean()
        df['SMA120'] = df['Close'].rolling(120).mean()
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        df['RSI14'] = 100 - (100 / (1 + (delta.where(delta > 0, 0).rolling(14).mean() / -delta.where(delta < 0, 0).rolling(14).mean())))

        plot_df = df.tail(plot_days)
        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.6, 0.2, 0.2], 
                            subplot_titles=("", "<b>Volume</b>", "<b>RSI (14)</b>"))

        fig.add_trace(go.Candlestick(x=plot_df.index, open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SMA50'], line=dict(color='blue', width=1.5), name='50 SMA'), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SMA120'], line=dict(color='orange', width=2), name='120 SMA'), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SMA200'], line=dict(color='red', width=1.5), name='200 SMA'), row=1, col=1)
        
        fig.add_trace(go.Bar(x=plot_df.index, y=plot_df['Volume'], marker_color=['red' if r['Close']<r['Open'] else 'green' for _,r in plot_df.iterrows()], name='Volume'), row=2, col=1)
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['RSI14'], line=dict(color='purple', width=1.5), name='RSI'), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

        fig.update_yaxes(fixedrange=True)
        fig.update_xaxes(
            rangeslider_visible=True,
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(step="all", label="All")
                ])
            )
        )

        fig.update_layout(
            title=dict(
                text=f"<b>{ticker_name} Technical Analysis</b>",
                x=0.5, xanchor='center', y=0.95, font=dict(size=24, family="sans-serif")
            ),
            height=750, margin=dict(l=10, r=10, t=100, b=10), 
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
        st.download_button(f"📥 Download {ticker_name} Raw Data (CSV)", data=df.to_csv().encode('utf-8'), file_name=f"{ticker_name}_data.csv", mime='text/csv', use_container_width=True)
    except Exception as e: st.error(f"Error: {e}")

# ==========================================
# 4. Main App & Subtitle Helper
# ==========================================
def get_subtitle(status, df):
    if status == 'ATH': return "All-Time High"
    kst = get_korea_time()
    c_date = df['curr_date'].max()
    b_date = df['base_date'].max()
    # [수정] 메인 타이틀 부제목도 월/일(3/2) 형식으로 통합
    curr_str = f"{kst.month}/{kst.day} {kst.strftime('%H:%M')} KST" if status != 'Completed' else f"{c_date.month}/{c_date.day}"
    return f"{curr_str} vs {b_date.month}/{b_date.day}"

def main():
    st.set_page_config(page_title="HanMARI V5.2", layout="wide")
    ports = load_portfolios()

    with st.sidebar:
        if st.button("🔄 Refresh Data", type="primary"): st.cache_data.clear(); st.rerun()
        mode = st.radio("View Mode", ["Market Overview", "Deep Dive (Interactive)"])
        st.markdown("---")
        
        if mode == "Market Overview":
            status = st.radio("Status", ('Live', 'Completed', 'Cycle', 'ATH'))
            period = 'All' if status == 'ATH' else st.selectbox("Period", ('Daily', 'Weekly', 'Monthly', 'Yearly'))
            
            st.markdown("#### 📋 Display Targets")
            show_global = st.checkbox("Global Top 12+1", value=True)
            show_key = st.checkbox("Key Indicators", value=False)
            
            st.markdown("#### 📂 Custom Portfolios")
            active_slots = {}
            for k in ports.keys():
                if st.checkbox(f"Show: {ports[k]['name']}", value=False, key=f"chk_{k}"):
                    active_slots[k] = ports[k]
                    
            with st.expander("⚙️ Manage Portfolios (Edit/Save)"):
                for k in ports.keys():
                    st.markdown(f"**{k}**")
                    ports[k]['name'] = st.text_input("Name", value=ports[k]['name'], key=f"n_{k}")
                    ports[k]['tickers'] = st.text_area("Tickers", value=ports[k]['tickers'], key=f"t_{k}")
                if st.button("💾 Save Changes", use_container_width=True):
                    save_portfolios(ports)
                    st.success("Saved Successfully!")
                    st.rerun()
        else:
            st.markdown("#### 🔍 Deep Dive Target")
            all_deep_dive_map = {}
            for k, v in TICKERS.items(): all_deep_dive_map[k] = v
            all_tickers_raw = ",".join([p['tickers'] for p in ports.values() if p['tickers']])
            for item in all_tickers_raw.split(','):
                item = item.strip()
                if not item: continue
                if '=' in item:
                    t, n = item.split('=', 1)
                    all_deep_dive_map[n.strip()] = t.strip()
                else: all_deep_dive_map[item] = item
                
            deep_dive_target = st.selectbox("Select Asset to Analyze", options=list(all_deep_dive_map.keys()))
            
            st.markdown("#### ⏳ X-Axis Timeframe")
            dd_period_label = st.selectbox("Select Timeframe", ["3 Months", "6 Months", "1 Year", "3 Years", "Max (10Y)"], index=2)
            days_map = {"3 Months": 63, "6 Months": 126, "1 Year": 252, "3 Years": 756, "Max (10Y)": 2520}
            plot_days = days_map[dd_period_label]

    st.markdown("<h3 style='font-size: 26px; font-weight: bold; font-family: sans-serif;'>📊 HanMARI V5.2 : Financial Secretary</h3>", unsafe_allow_html=True)

    custom_mapping = {}
    if mode == "Market Overview":
        for p in active_slots.values():
            for item in p['tickers'].split(','):
                item = item.strip()
                if not item: continue
                if '=' in item:
                    t, n = item.split('=', 1)
                    custom_mapping[n.strip()] = t.strip()
                else: custom_mapping[item] = item
    else:
        custom_mapping = all_deep_dive_map

    if st.button('🚀 Run Analysis', use_container_width=True):
        with st.spinner('Downloading market data...'):
            close_df, high_df, raw_df = download_all_data()
            extra_tickers = tuple(set(custom_mapping.values()) - set(TICKERS.values()))
            extra_close, extra_high, extra_raw = download_extra_data(extra_tickers)
            
            if not extra_close.empty:
                close_df = pd.concat([close_df, extra_close], axis=1)
                high_df = pd.concat([high_df, extra_high], axis=1)
                raw_df = pd.concat([raw_df, extra_raw], axis=1)

        if close_df.empty: return st.error("Failed to fetch data.")

        if mode == "Deep Dive (Interactive)":
            if deep_dive_target:
                draw_deep_dive_chart(custom_mapping[deep_dive_target], raw_df, deep_dive_target, plot_days)
        else:
            if show_global:
                df_g = process_data(['Gold','NVDA','Silver','AAPL','MSFT','AMZN','GOOG','TSMC','AVGO','TSLA','META','BTC','Samsung'], period, status, close_df, high_df)
                if not df_g.empty:
                    df_g, t_name_display = format_top13_df(df_g, "Global Top 12+1")
                    sub_t = get_subtitle(status, df_g)
                    main_t = f"{t_name_display} {'ATH' if status == 'ATH' else period}"
                    draw_top13_chart(df_g, main_t, sub_t, is_ath=(status=='ATH'))
                    st.code(generate_twitter_text(df_g, main_t, sub_t, is_top=True), language="text")
            
            if show_key:
                df_k = process_data(['Gold','Silver','Copper','BTC','ETH','KOSPI','NASDAQ','S&P 500','Dollar Index','USD/KRW'], period, status, close_df, high_df)
                if not df_k.empty:
                    df_k = sort_by_category(df_k)
                    sub_t = get_subtitle(status, df_k)
                    main_t = f"Key Indicators {'ATH' if status == 'ATH' else period}"
                    draw_normal_chart(df_k, main_t, sub_t)
                    st.code(generate_twitter_text(df_k, main_t, sub_t), language="text")
            
            for k, p_data in active_slots.items():
                st.markdown("---")
                names = [n.split('=')[1].strip() if '=' in n else n.strip() for n in p_data['tickers'].split(',') if n.strip()]
                df_c = process_data(names, period, status, close_df, high_df, custom_mapping)
                if not df_c.empty:
                    df_c = sort_by_category(df_c)
                    sub_t = get_subtitle(status, df_c)
                    main_t = f"{p_data['name']} {'ATH' if status == 'ATH' else period}"
                    draw_normal_chart(df_c, main_t, sub_t)
                    st.code(generate_twitter_text(df_c, main_t, sub_t), language="text")

if __name__ == '__main__':
    main()