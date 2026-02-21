import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import platform
from datetime import datetime, timedelta
import pytz

# ==========================================
# 0. Font Settings (Global Standard)
# ==========================================
@st.cache_resource
def font_setting():
    system_name = platform.system()
    if system_name == 'Windows':
        plt.rc('font', family='Malgun Gothic')
    elif system_name == 'Darwin':
        plt.rc('font', family='AppleGothic')
    else:
        plt.rc('font', family='sans-serif')
    plt.rcParams['axes.unicode_minus'] = False

font_setting()

# ==========================================
# 1. Design & Core Rules
# ==========================================
CATEGORY_COLORS = {
    'Macro': '#C29200',     
    'Crypto': '#FF5E00',    
    'US Tech': '#004A99',   
    'K-Market': '#228B22',  
    'Others': '#777777'
}

TICKERS = {
    'Gold': 'GC=F', 'Silver': 'SI=F', 'Copper': 'HG=F',
    'BTC': 'BTC-USD', 'ETH': 'ETH-USD',
    'KOSPI': '^KS11', 'NASDAQ': '^IXIC', 'S&P 500': '^GSPC',
    'DXY': 'DX-Y.NYB', 'USD/KRW': 'KRW=X',
    'NVDA': 'NVDA', 'AAPL': 'AAPL', 'MSFT': 'MSFT', 'AMZN': 'AMZN',
    'GOOG': 'GOOG', 'TSMC': 'TSM', 'AVGO': 'AVGO', 'TSLA': 'TSLA',
    'META': 'META', 'Samsung': '005930.KS', 'SK Hynix': '000660.KS',
    'QQQ': 'QQQ', 'MSTR': 'MSTR',
    'TIGER 200': '102110.KS', 'TIGER Heavy': '139260.KS',
    'TIGER Nasdaq': '133690.KS', 'TIGER US Tech': '381170.KS',
    'TIGER Gold': '411060.KS'
}

def get_text_color(change_val):
    if abs(change_val) < 0.05: return 'black'
    return 'blue' if change_val > 0 else 'red'

def format_price(value, name):
    krw_assets = ['Samsung', 'SK Hynix', 'TIGER']
    prefix = "₩" if any(x in name for x in krw_assets) else ""
    
    if value >= 1000: return f"{prefix}{value:,.0f}"
    if value >= 10: return f"{prefix}{value:,.1f}"
    return f"{prefix}{value:,.2f}"

def get_korea_time():
    utc_now = datetime.now(pytz.utc)
    return utc_now.astimezone(pytz.timezone('Asia/Seoul'))

# ==========================================
# 2. Data Engine (Cycle vs Calendar Logic)
# ==========================================
@st.cache_data(ttl=300) 
def download_all_data():
    tickers_list = list(TICKERS.values())
    df = yf.download(tickers_list, period="10y", interval="1d", progress=False)
    
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        if 'Close' in df.columns.get_level_values(0):
            close_df = df.xs('Close', axis=1, level=0)
            high_df = df.xs('High', axis=1, level=0)
        elif 'Close' in df.columns.get_level_values(1):
            close_df = df.xs('Close', axis=1, level=1)
            high_df = df.xs('High', axis=1, level=1)
        else:
            return pd.DataFrame(), pd.DataFrame()
    else:
        close_df = pd.DataFrame(df['Close'])
        high_df = pd.DataFrame(df['High'])
        
    close_df.index = pd.to_datetime(close_df.index).tz_localize(None)
    high_df.index = pd.to_datetime(high_df.index).tz_localize(None)
    
    return close_df, high_df

def process_data(target_names, period, status_mode, close_df, high_df):
    res = []
    today_kst = get_korea_time().date()

    for name in target_names:
        ticker = TICKERS.get(name)
        if ticker not in close_df.columns: continue
        
        series = close_df[ticker].dropna()
        if series.empty: continue
        
        cat = 'Others'
        if name in ['Gold', 'Silver', 'Copper', 'DXY', 'USD/KRW', 'TIGER Gold']: cat = 'Macro'
        elif name in ['BTC', 'ETH']: cat = 'Crypto'
        elif name in ['Samsung', 'SK Hynix', 'KOSPI', 'TIGER 200', 'TIGER Heavy']: cat = 'K-Market'
        elif name in ['NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOG', 'TSMC', 'AVGO', 'TSLA', 'META', 'NASDAQ', 'S&P 500', 'QQQ', 'MSTR', 'TIGER Nasdaq', 'TIGER US Tech']: cat = 'US Tech'

        if status_mode == 'ATH':
            curr = float(series.iloc[-1])
            ath = float(high_df[ticker].dropna().max())
            curr_date = series.index[-1].date()
            change = ((curr - ath) / ath) * 100 if ath > 0 else 0
            res.append({'name': name, 'price': curr, 'change': change, 'category': cat, 'curr_date': curr_date, 'base_date': curr_date})
            continue
        
        if status_mode == 'Completed':
            valid_series = series[series.index.date < today_kst]
        else: 
            valid_series = series 
            
        if valid_series.empty: continue
            
        curr = float(valid_series.iloc[-1])
        curr_date = valid_series.index[-1].date()
        
        # Cycle: Strict rolling days (-1, -7, -30, -365)
        if status_mode == 'Cycle':
            if period == 'Daily': target_base = curr_date - timedelta(days=1)
            elif period == 'Weekly': target_base = curr_date - timedelta(days=7)
            elif period == 'Monthly': target_base = curr_date - timedelta(days=30)
            elif period == 'Yearly': target_base = curr_date - timedelta(days=365)
            else: target_base = curr_date
            
            base_series = series[series.index.date <= target_base]
        
        # Live / Completed: Calendar logic
        else:
            if period == 'Daily':
                base_series = series[series.index.date < curr_date]
            elif period == 'Weekly':
                curr_dt = datetime.combine(curr_date, datetime.min.time())
                monday = (curr_dt - timedelta(days=curr_dt.weekday())).date()
                base_series = series[series.index.date < monday]
            elif period == 'Monthly':
                first_day = curr_date.replace(day=1)
                base_series = series[series.index.date < first_day]
            elif period == 'Yearly':
                first_day_year = curr_date.replace(month=1, day=1)
                base_series = series[series.index.date < first_day_year]
            elif period == 'All':
                base_series = series.iloc[0:1] 
            else:
                base_series = series
            
        base = float(base_series.iloc[-1]) if not base_series.empty else curr
        base_date = base_series.index[-1].date() if not base_series.empty else curr_date
        change = ((curr - base) / base) * 100 if base > 0 else 0
        
        res.append({'name': name, 'price': curr, 'change': change, 'category': cat, 'curr_date': curr_date, 'base_date': base_date})
        
    return pd.DataFrame(res)

# ==========================================
# 3. Chart Drawing (Dynamic & Wrapped)
# ==========================================
def style_axes(ax):
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color('#CCCCCC')
        spine.set_linewidth(1.5)
    ax.tick_params(axis='x', labelsize=8, rotation=0) 
    ax.tick_params(axis='y', labelsize=8)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(nbins=4)) 

def draw_top13_chart(df, main_title, sub_title, is_mini=False, is_ath=False):
    if df.empty: return
    
    if is_ath:
        draw_normal_chart(df, main_title, sub_title, is_mini)
        return

    mcap = {'Gold': 33.9, 'NVDA': 4.5, 'Silver': 4.3, 'AAPL': 4.0, 'MSFT': 3.0, 'AMZN': 2.2, 'GOOG': 1.8, 'TSMC': 1.8, 'AVGO': 1.5, 'TSLA': 1.5, 'META': 1.4, 'BTC': 1.3, 'Samsung': 0.3}
    df['mcap'] = df['name'].map(mcap).fillna(0)
    
    # Smart line break for X-axis labels to prevent overlap
    df['plot_name'] = df['name'].str.replace(' ', '\n', n=1)

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10, 4.5) if not is_mini else (6, 3.5), gridspec_kw={'height_ratios': [1, 3]})
    fig.subplots_adjust(hspace=0.05)
    fig.patch.set_facecolor('white')

    colors = [CATEGORY_COLORS.get(c, '#777777') for c in df['category']]
    
    ax1.bar(df['plot_name'], df['mcap'], color=colors, width=0.6)
    
    # Dynamic Y-axis for Gold
    gold_max = df['mcap'].max()
    upper_bound = max(38, int(gold_max + 4)) 
    
    ax1.set_ylim(30, upper_bound)
    ax2.bar(df['plot_name'], df['mcap'], color=colors, width=0.6)
    ax2.set_ylim(0, 5.5) 
    
    style_axes(ax1)
    style_axes(ax2)
    
    ax1.set_yticks([30, upper_bound])
    
    ax1.spines['bottom'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax1.xaxis.set_visible(False)

    wave_x = np.linspace(0, 1, 100)
    ax1.plot(wave_x, np.sin(20 * np.pi * wave_x) * 0.008, transform=ax1.transAxes, color='#CCCCCC', lw=1.5, clip_on=False)
    ax2.plot(wave_x, 1 + np.sin(20 * np.pi * wave_x) * 0.008, transform=ax2.transAxes, color='#CCCCCC', lw=1.5, clip_on=False)

    for i, r in df.iterrows():
        txt_col = get_text_color(r['change'])
        sign = '▲' if r['change'] > 0 else ('▼' if r['change'] < 0 else '-')
        label = f"{r['mcap']}T\n{sign}{abs(r['change']):.1f}%"
        
        if r['mcap'] > 10:
            ax1.text(i, 34.5, label, ha='center', va='bottom', fontsize=8 if is_mini else 9, fontweight='bold', color=txt_col)
        else:
            ax2.text(i, r['mcap'] + 0.2, label, ha='center', va='bottom', fontsize=8 if is_mini else 9, fontweight='bold', color=txt_col)

    title_y = 1.05
    ax1.text(0.48, title_y, main_title, transform=ax1.transAxes, ha='right', va='bottom', fontsize=13 if is_mini else 15, fontweight='bold', color='black')
    ax1.text(0.50, title_y, f" {sub_title}", transform=ax1.transAxes, ha='left', va='bottom', fontsize=9 if is_mini else 11, color='gray')
    
    if not is_mini:
        lp = [mpatches.Patch(color=v, label=k) for k, v in CATEGORY_COLORS.items() if k in df['category'].values]
        ax1.legend(handles=lp, loc='upper right', frameon=True, fontsize=8, facecolor='white', edgecolor='#CCCCCC', ncol=len(lp))
        
    plt.tight_layout()
    st.pyplot(fig)

def draw_normal_chart(df, main_title, sub_title, is_mini=False, is_ath=False):
    if df.empty: return
    fig, ax = plt.subplots(figsize=(10, 4.0) if not is_mini else (6, 3.5))
    fig.patch.set_facecolor('white')
    
    df['plot_name'] = df['name'].str.replace(' ', '\n', n=1)
    
    colors = [CATEGORY_COLORS.get(c, '#777777') for c in df['category']]
    bars = ax.bar(df['plot_name'], df['change'], color=colors, width=0.6)
    ax.axhline(0, color='black', linewidth=1.0)
    style_axes(ax)
    
    for bar in bars:
        h = bar.get_height()
        va, offset = ('bottom', 3) if h >= 0 else ('top', -3)
        txt_col = get_text_color(h)
        sign = '▲' if h > 0 else ('▼' if h < 0 else '-')
        ax.annotate(f'{sign}{abs(h):.1f}%', xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, offset), textcoords="offset points", ha='center', va=va, fontweight='bold', fontsize=8 if is_mini else 9, color=txt_col)

    title_y = 1.05
    ax.text(0.48, title_y, main_title, transform=ax.transAxes, ha='right', va='bottom', fontsize=13 if is_mini else 15, fontweight='bold', color='black')
    ax.text(0.50, title_y, f" {sub_title}", transform=ax.transAxes, ha='left', va='bottom', fontsize=9 if is_mini else 11, color='gray')
    
    if not is_mini:
        lp = [mpatches.Patch(color=v, label=k) for k, v in CATEGORY_COLORS.items() if k in df['category'].values]
        ax.legend(handles=lp, loc='upper right', frameon=True, fontsize=8, facecolor='white', edgecolor='#CCCCCC', ncol=len(lp))
        
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100, decimals=0, symbol='%'))
    
    if not df.empty:
        margin = max(abs(df['change'].min()), abs(df['change'].max())) * 0.3 or 1
        ax.set_ylim(df['change'].min() - margin, df['change'].max() + margin) 
        
    plt.tight_layout()
    st.pyplot(fig)

# ==========================================
# 4. Data Export Generator
# ==========================================
def generate_twitter_text(df, title, date_str):
    txt = f"[{title}]\n({date_str})\n\n"
    
    macro = df[df['category'] == 'Macro']
    crypto = df[df['category'] == 'Crypto']
    tech = df[df['category'] == 'US Tech']
    k_market = df[df['category'] == 'K-Market']
    
    if not macro.empty or not crypto.empty:
        txt += "🛡️ Macro & Crypto\n"
        items = [f"{r['name']} {format_price(r['price'], r['name'])}" for _, r in pd.concat([macro, crypto]).iterrows()]
        for i in range(0, len(items), 2):
            txt += " | ".join(items[i:i+2]) + "\n"
        txt += "\n"
        
    if not tech.empty or not k_market.empty:
        txt += "💻 Equities & Tech\n"
        items = [f"{r['name']} {format_price(r['price'], r['name'])}" for _, r in pd.concat([tech, k_market]).iterrows()]
        for i in range(0, len(items), 2):
            txt += " | ".join(items[i:i+2]) + "\n"
            
    txt += "\n#Investing #MarketUpdate #Crypto #Stocks"
    return txt

# ==========================================
# 5. Main App
# ==========================================
def main():
    st.set_page_config(page_title="Hanmari Financial Secretary", layout="wide")
    st.sidebar.header("🛠️ Settings")
    
    mode = st.sidebar.radio("View Mode", ["General Analysis", "Comprehensive Report"])
    
    st.sidebar.markdown("#### 📋 Targets")
    show_global = st.sidebar.checkbox("Global Top 12+1", value=True)
    show_key = st.sidebar.checkbox("Key Indicators", value=False)
    show_my = st.sidebar.checkbox("My Portfolio", value=False)
    
    st.sidebar.markdown("---")
    status = st.sidebar.radio("Status", ('Live', 'Completed', 'Cycle', 'ATH'))
    
    period = 'All' if (mode == "Comprehensive Report" or status == 'ATH') else st.sidebar.selectbox("Period", ('Daily', 'Weekly', 'Monthly', 'Yearly'))

    st.markdown("<h3 style='font-size: 24px; font-weight: bold;'>📊 Hanmari Financial Secretary v2.0</h3>", unsafe_allow_html=True)

    if st.button('🚀 Run Analysis', use_container_width=True):
        
        with st.spinner('Downloading 10-year market data for true ATH...'):
            close_df, high_df = download_all_data()

        if close_df.empty:
            st.error("Failed to fetch market data. Please try again later.")
            return

        targets = []
        if show_global: 
            targets.append(("Global Top 12+1", ['Gold','NVDA','Silver','AAPL','MSFT','AMZN','GOOG','TSMC','AVGO','TSLA','META','BTC','Samsung'], draw_top13_chart))
        if show_key: 
            targets.append(("Key Indicators", ['Gold','Silver','Copper','BTC','ETH','KOSPI','NASDAQ','S&P 500','DXY','USD/KRW'], draw_normal_chart))
        if show_my: 
            targets.append(("My Portfolio", ['TIGER 200', 'TIGER Heavy', 'Samsung', 'SK Hynix', 'TIGER Nasdaq', 'TIGER US Tech', 'QQQ', 'TSLA', 'MSTR', 'TIGER Gold', 'BTC', 'ETH'], draw_normal_chart))

        if mode == "General Analysis":
            for t_name, t_list, t_func in targets:
                df = process_data(t_list, period, status, close_df, high_df)
                if not df.empty:
                    kst_now = get_korea_time()
                    
                    if status in ['Live', 'ATH', 'Cycle']:
                        target_str = kst_now.strftime('%b %d %H:%M KST Live')
                    else:
                        real_curr_d = df['curr_date'].max()
                        target_str = f"{real_curr_d.strftime('%b %d')} Close"
                        
                    if status == 'ATH':
                        base_str = "All-Time High"
                    else:
                        real_base_d = df['base_date'].max()
                        base_str = real_base_d.strftime('%b %d')
                        
                    sub_t = f"({target_str} vs {base_str})"
                    main_t = f"{t_name} {period if status != 'ATH' else 'ATH'}"
                    
                    t_func(df, main_t, sub_t, is_mini=False, is_ath=(status=='ATH') if t_name == "Global Top 12+1" else False)
                    
                    st.markdown("#### 📋 Data Export")
                    st.code(generate_twitter_text(df, main_t, sub_t.strip("()")), language="text")

        else: # Comprehensive Report
            for t_name, t_list, t_func in targets:
                st.markdown(f"<hr><h4 style='font-weight: bold;'>📑 {t_name} Comprehensive</h4>", unsafe_allow_html=True)
                
                if status == 'ATH':
                    st.warning("ATH Mode is a single timeframe view.")
                    df = process_data(t_list, 'All', 'ATH', close_df, high_df)
                    if not df.empty:
                        kst_now = get_korea_time()
                        target_str = kst_now.strftime('%b %d %H:%M KST Live')
                        sub_t = f"({target_str} vs All-Time High)"
                        
                        t_func(df, f"{t_name} ATH", sub_t, is_mini=False, is_ath=True if t_name == "Global Top 12+1" else False)
                else:
                    periods = ['Daily', 'Weekly', 'Monthly', 'Yearly']
                    cols = st.columns(2) + st.columns(2)
                    
                    for i, p in enumerate(periods):
                        with cols[i]:
                            df = process_data(t_list, p, status, close_df, high_df)
                            if not df.empty:
                                kst_now = get_korea_time()
                                if status in ['Live', 'Cycle']:
                                    target_str = kst_now.strftime('%b %d %H:%M KST Live')
                                else:
                                    real_curr_d = df['curr_date'].max()
                                    target_str = f"{real_curr_d.strftime('%b %d')} Close"
                                    
                                real_base_d = df['base_date'].max()
                                base_str = real_base_d.strftime('%b %d')
                                
                                sub_t = f"({target_str} vs {base_str})"
                                t_func(df, f"{p}", sub_t, is_mini=True, is_ath=False)

if __name__ == '__main__':
    main()