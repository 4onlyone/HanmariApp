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

# [수정] 삼성전자 우선주 합산(6.791) 및 예비 종목 추가 완료
SHARES_B = {
    'Gold': 6.83, 'Silver': 56.0, 'AAPL': 15.4, 'NVDA': 24.5, 
    'MSFT': 7.43, 'AMZN': 10.39, 'GOOG': 12.43, 'TSMC': 5.18, 
    'AVGO': 4.63, 'TSLA': 3.18, 'META': 2.54, 'BTC': 0.01999,
    'Samsung': 6.791, 'PLTR': 2.3, 'ETH': 0.12, 'SK Hynix': 0.728
}

def get_text_color(change_val):
    if abs(change_val) < 0.05: return 'black'
    return 'blue' if change_val > 0 else 'red'

def format_value_auto(value):
    if value >= 100: return f"{value:,.0f}"
    if value >= 10: return f"{value:,.1f}"
    return f"{value:,.2f}"

def format_price(value, name, category='Others'):
    krw_assets = ['Samsung', 'SK Hynix', 'TIGER']
    no_sym_assets = ['KOSPI', 'USD/KRW', 'DXY']
    
    if any(x in name for x in no_sym_assets): prefix = ""
    elif any(x in name for x in krw_assets) or category == 'K-Market': prefix = "₩"
    else: prefix = "$"
    
    return f"{prefix}{format_value_auto(value)}"

def get_korea_time():
    utc_now = datetime.now(pytz.utc)
    return utc_now.astimezone(pytz.timezone('Asia/Seoul'))

# ==========================================
# 2. Data Engine & Dynamic Mcap Calculator
# ==========================================
@st.cache_data(ttl=300) 
def download_all_data():
    tickers_list = list(TICKERS.values())
    df = yf.download(tickers_list, period="10y", interval="1d", progress=False)
    return parse_downloaded_data(df)

@st.cache_data(ttl=300)
def download_extra_data(tickers_tuple):
    if not tickers_tuple: return pd.DataFrame(), pd.DataFrame()
    df = yf.download(list(tickers_tuple), period="10y", interval="1d", progress=False)
    return parse_downloaded_data(df)

def parse_downloaded_data(df):
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

def process_data(target_names, period, status_mode, close_df, high_df, custom_mapping=None):
    if custom_mapping is None: custom_mapping = {}
    res = []
    kst_now = get_korea_time()
    today_kst = kst_now.date()
    
    usd_krw_series = close_df['KRW=X'].dropna() if 'KRW=X' in close_df.columns else pd.Series(dtype=float)
    usd_krw_current = float(usd_krw_series.iloc[-1]) if not usd_krw_series.empty else 1350.0

    for name in target_names:
        ticker = TICKERS.get(name) or custom_mapping.get(name)
        if not ticker or ticker not in close_df.columns: 
            if name in custom_mapping:
                st.warning(f"⚠️ Cannot fetch data for '{ticker}'. Please check the ticker symbol.")
            continue
        
        series = close_df[ticker].dropna()
        if series.empty: continue
        
        cat = 'Others'
        if name in TICKERS:
            if name in ['Gold', 'Silver', 'Copper', 'DXY', 'USD/KRW', 'TIGER Gold']: cat = 'Macro'
            elif name in ['BTC', 'ETH']: cat = 'Crypto'
            elif name in ['Samsung', 'SK Hynix', 'KOSPI', 'TIGER 200', 'TIGER Heavy']: cat = 'K-Market'
            elif name in ['NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOG', 'AVGO', 'TSLA', 'META', 'NASDAQ', 'S&P 500', 'QQQ', 'MSTR', 'TIGER Nasdaq', 'TIGER US Tech']: cat = 'US Tech'
            elif name in ['TSMC']: cat = 'Others'
        else:
            if ticker.endswith('.KS') or ticker.endswith('.KQ'): cat = 'K-Market'
            elif '-USD' in ticker: cat = 'Crypto'
            elif ticker.isalpha() and ticker.isupper(): cat = 'US Tech'
            else: cat = 'Others'

        if status_mode == 'ATH':
            curr = float(series.iloc[-1])
            ath = float(high_df[ticker].dropna().max())
            curr_date = series.index[-1].date()
            change = ((curr - ath) / ath) * 100 if ath > 0 else 0
            base_date = curr_date

        # [수정] 시장별 마감 시간 독립화 로직 (Daily 한정)
        elif status_mode == 'Completed' and period == 'Daily':
            if cat in ['US Tech', 'Macro', 'Others']:
                target_date = today_kst - timedelta(days=2) if kst_now.hour < 6 else today_kst - timedelta(days=1)
            elif cat == 'Crypto':
                target_date = today_kst - timedelta(days=2) if kst_now.hour < 9 else today_kst - timedelta(days=1)
            else: # K-Market
                if kst_now.hour < 15 or (kst_now.hour == 15 and kst_now.minute < 30):
                    target_date = today_kst - timedelta(days=1)
                else:
                    target_date = today_kst
            
            curr_subset = series[series.index.date <= target_date]
            if curr_subset.empty: continue
            curr = float(curr_subset.iloc[-1])
            
            base_target_date = target_date - timedelta(days=1)
            base_subset = series[series.index.date <= base_target_date]
            base = float(base_subset.iloc[-1]) if not base_subset.empty else curr
            
            change = ((curr - base) / base) * 100 if base > 0 else 0
            curr_date = target_date
            base_date = base_target_date

        else:
            # Live, Cycle, 및 Completed(Weekly/Monthly/Yearly) 로직
            if status_mode == 'Completed': 
                valid_series = series[series.index.date < today_kst]
            else: 
                valid_series = series 
                
            if valid_series.empty: continue
                
            curr = float(valid_series.iloc[-1])
            curr_date = valid_series.index[-1].date()
            
            if status_mode == 'Cycle':
                if period == 'Daily': target_base = curr_date - timedelta(days=1)
                elif period == 'Weekly': target_base = curr_date - timedelta(days=7)
                elif period == 'Monthly': target_base = curr_date - timedelta(days=30)
                elif period == 'Yearly': target_base = curr_date - timedelta(days=365)
                else: target_base = curr_date
                base_series = series[series.index.date <= target_base]
            else:
                if period == 'Daily': base_series = series[series.index.date < curr_date]
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
                elif period == 'All': base_series = series.iloc[0:1] 
                else: base_series = series
                
            base = float(base_series.iloc[-1]) if not base_series.empty else curr
            change = ((curr - base) / base) * 100 if base > 0 else 0
            base_date = base_series.index[-1].date() if not base_series.empty else curr_date
        
        # [수정] 환율 변환 로직 범용화
        mcap = 0
        if name in SHARES_B:
            if cat == 'K-Market' or name in ['Samsung', 'SK Hynix']: 
                mcap = (curr * SHARES_B[name]) / usd_krw_current / 1000
            else: 
                mcap = (curr * SHARES_B[name]) / 1000
                
        res.append({'name': name, 'price': curr, 'change': change, 'category': cat, 'curr_date': curr_date, 'base_date': base_date, 'mcap': mcap})
        
    return pd.DataFrame(res)

# ==========================================
# 3. Dynamic Sorting Rule & Formatting
# ==========================================
def format_top13_df(df, t_name):
    df = df.sort_values('mcap', ascending=False).reset_index(drop=True)
    s_idx_list = df.index[df['name'] == 'Samsung'].tolist()
    
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
    df['cat_rank'] = df['category'].map(cat_order).fillna(99)
    return df.sort_values(['cat_rank', 'name']).drop('cat_rank', axis=1).reset_index(drop=True)

# ==========================================
# 4. Chart Drawing
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

    df['plot_name'] = df['name'].str.replace(' ', '\n', n=1)

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10, 4.5) if not is_mini else (6, 3.5), gridspec_kw={'height_ratios': [1, 3]})
    fig.subplots_adjust(hspace=0.05)
    fig.patch.set_facecolor('white')

    colors = [CATEGORY_COLORS.get(c, '#777777') for c in df['category']]
    ax1.bar(df['plot_name'], df['mcap'], color=colors, width=0.6)
    
    ax1_mcaps = df[df['mcap'] > 10]['mcap'] 
    ax1_max = ax1_mcaps.max() if not ax1_mcaps.empty else 34.0
    ax1_upper_bound = int(np.ceil(ax1_max + 4.0)) 
    ax1.set_ylim(30, ax1_upper_bound)
    
    ax2.bar(df['plot_name'], df['mcap'], color=colors, width=0.6)
    ax2_mcaps = df[df['mcap'] < 20]['mcap'] 
    ax2_min = ax2_mcaps.min() if not ax2_mcaps.empty else 0
    ax2_max = ax2_mcaps.max() if not ax2_mcaps.empty else 5.5
    
    ax2_lower_bound = int(np.floor(ax2_min)) 
    ax2_upper_bound = ax2_max + 1.5          
    ax2.set_ylim(ax2_lower_bound, ax2_upper_bound) 
    
    style_axes(ax1)
    style_axes(ax2)
    
    ax1.set_yticks([30, ax1_upper_bound])
    ax1.spines['bottom'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax1.xaxis.set_visible(False)

    wave_x = np.linspace(0, 1, 100)
    ax1.plot(wave_x, np.sin(20 * np.pi * wave_x) * 0.008, transform=ax1.transAxes, color='#CCCCCC', lw=1.5, clip_on=False)
    ax2.plot(wave_x, 1 + np.sin(20 * np.pi * wave_x) * 0.008, transform=ax2.transAxes, color='#CCCCCC', lw=1.5, clip_on=False)

    for i, r in df.iterrows():
        txt_col = get_text_color(r['change'])
        sign = '▲' if r['change'] > 0 else ('▼' if r['change'] < 0 else '-')
        mcap_formatted = format_value_auto(r['mcap'])
        label = f"{mcap_formatted}T\n{sign}{abs(r['change']):.1f}%"
        
        if r['mcap'] > 10: ax1.text(i, r['mcap'] + 0.8, label, ha='center', va='bottom', fontsize=8 if is_mini else 9, fontweight='bold', color=txt_col)
        else: ax2.text(i, r['mcap'] + 0.3, label, ha='center', va='bottom', fontsize=8 if is_mini else 9, fontweight='bold', color=txt_col)

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
# 5. Data Export Generator (Ranking Mode)
# ==========================================
def generate_twitter_text(df, title, date_str, is_top=False):
    txt = f"[{title}]\n({date_str})\n\n"
    
    if is_top and 'display_rank' in df.columns:
        for _, r in df.iterrows():
            mcap_str = f"{format_value_auto(r['mcap'])}T"
            price_str = format_price(r['price'], r['name'], r['category'])
            change_str = f"+{r['change']:.1f}%" if r['change'] > 0 else f"{r['change']:.1f}%"
            txt += f"{r['display_rank']}. {r['name']} {mcap_str} ({price_str}, {change_str})\n"
        txt += "\n#Investing #MarketUpdate #GlobalTop"
        return txt
        
    for i, (_, r) in enumerate(df.iterrows(), 1):
        price_str = format_price(r['price'], r['name'], r['category'])
        change_str = f"+{r['change']:.1f}%" if r['change'] > 0 else f"{r['change']:.1f}%"
        txt += f"{i}. {r['name']} {price_str} ({change_str})\n"
        
    txt += "\n#Investing #MarketUpdate #Crypto #Stocks"
    return txt

# ==========================================
# 6. Main App
# ==========================================
def main():
    st.set_page_config(page_title="Hanmari Financial Secretary", layout="wide")
    
    if st.sidebar.button("🔄 Refresh Data (Clear Cache)", type="primary"):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.header("🛠️ Settings")
    mode = st.sidebar.radio("View Mode", ["General Analysis", "Comprehensive Report"])
    
    st.sidebar.markdown("#### 📋 Targets")
    show_global = st.sidebar.checkbox("Global Top 12+1", value=True)
    show_key = st.sidebar.checkbox("Key Indicators", value=False)
    
    show_custom = st.sidebar.checkbox("Custom Portfolio", value=False)
    
    selected_custom_port = []
    custom_mapping = {}
    
    if show_custom:
        default_port = ['TIGER 200', 'TIGER Heavy', 'Samsung', 'SK Hynix', 'TIGER Nasdaq', 'TIGER US Tech', 'QQQ', 'TSLA', 'MSTR', 'TIGER Gold', 'BTC', 'ETH']
        selected_custom_port = st.sidebar.multiselect("Select Existing Tickers", options=list(TICKERS.keys()), default=default_port)
        
        # [수정] 16개 종목 자동 삽입
        default_tickers = "PLTR=Palantir, TSLA=Tesla, NVDA=NVIDIA, 005930.KS=Samsung Elec, 000660.KS=SK Hynix, 102110.KS=Tiger 200, 139260.KS=Tiger Heavy, 411060.KS=Tiger Gold, BTC-USD=BTC, 005380.KS=Hyundai Motors, 035420.KS=NAVER, 466920.KS=K-Ship, 241180.KS=Tiger Nikkei, 192090.KS=Tiger China, 453850.KS=Tiger India, 204320.KS=HL Mando"
        custom_input = st.sidebar.text_input("Add Tickers (Separate with commas ',')", value=default_tickers)
        
        if custom_input.strip():
            items = custom_input.split(',')
            for item in items:
                item = item.strip()
                if not item: continue
                if '=' in item:
                    ticker, name = item.split('=', 1)
                    custom_mapping[name.strip()] = ticker.strip()
                else:
                    custom_mapping[item] = item

    st.sidebar.markdown("---")
    status = st.sidebar.radio("Status", ('Live', 'Completed', 'Cycle', 'ATH'))
    period = 'All' if (mode == "Comprehensive Report" or status == 'ATH') else st.sidebar.selectbox("Period", ('Daily', 'Weekly', 'Monthly', 'Yearly'))

    st.markdown("<h3 style='font-size: 24px; font-weight: bold;'>📊 Hanmari Financial Secretary v2.0</h3>", unsafe_allow_html=True)

    if st.button('🚀 Run Analysis', use_container_width=True):
        
        with st.spinner('Downloading market data...'):
            close_df, high_df = download_all_data()
            
            extra_tickers = tuple(set(custom_mapping.values()) - set(TICKERS.values()))
            extra_close, extra_high = download_extra_data(extra_tickers)
            
            if not extra_close.empty:
                close_df = pd.concat([close_df, extra_close], axis=1)
                high_df = pd.concat([high_df, extra_high], axis=1)

        if close_df.empty:
            st.error("Failed to fetch market data. Please try again later.")
            return

        targets = []
        if show_global: 
            targets.append(("Global Top", ['Gold','NVDA','Silver','AAPL','MSFT','AMZN','GOOG','TSMC','AVGO','TSLA','META','BTC','Samsung'], draw_top13_chart))
        if show_key: 
            targets.append(("Key Indicators", ['Gold','Silver','Copper','BTC','ETH','KOSPI','NASDAQ','S&P 500','DXY','USD/KRW'], draw_normal_chart))
        if show_custom: 
            final_custom_list = selected_custom_port + list(custom_mapping.keys())
            if final_custom_list:
                targets.append(("Custom Portfolio", final_custom_list, draw_normal_chart))

        if mode == "General Analysis":
            for t_name, t_list, t_func in targets:
                df = process_data(t_list, period, status, close_df, high_df, custom_mapping)
                if not df.empty:
                    is_top = "Global Top" in t_name
                    if is_top:
                        df, t_name_display = format_top13_df(df, t_name)
                    else:
                        df = sort_by_category(df)
                        t_name_display = t_name
                    
                    kst_now = get_korea_time()
                    if status in ['Live', 'ATH', 'Cycle']: target_str = kst_now.strftime('%b %d %H:%M KST Live')
                    else: target_str = f"{df['curr_date'].max().strftime('%b %d')} Close"
                        
                    if status == 'ATH': base_str = "All-Time High"
                    else: base_str = df['base_date'].max().strftime('%b %d')
                        
                    sub_t = f"({target_str} vs {base_str})"
                    main_t = f"{t_name_display} {period if status != 'ATH' else 'ATH'}"
                    
                    t_func(df, main_t, sub_t, is_mini=False, is_ath=(status=='ATH') if is_top else False)
                    
                    st.markdown("#### 📋 Data Export")
                    st.code(generate_twitter_text(df, main_t, sub_t.strip("()"), is_top=is_top), language="text")

        else: # Comprehensive Report
            for t_name, t_list, t_func in targets:
                st.markdown(f"<hr><h4 style='font-weight: bold;'>📑 {t_name} Comprehensive</h4>", unsafe_allow_html=True)
                is_top = "Global Top" in t_name
                
                if status == 'ATH':
                    st.warning("ATH Mode is a single timeframe view.")
                    df = process_data(t_list, 'All', 'ATH', close_df, high_df, custom_mapping)
                    if not df.empty:
                        if is_top:
                            df, t_name_display = format_top13_df(df, t_name)
                        else:
                            df = sort_by_category(df)
                            t_name_display = t_name
                            
                        kst_now = get_korea_time()
                        target_str = kst_now.strftime('%b %d %H:%M KST Live')
                        sub_t = f"({target_str} vs All-Time High)"
                        
                        t_func(df, f"{t_name_display} ATH", sub_t, is_mini=False, is_ath=True if is_top else False)
                else:
                    periods = ['Daily', 'Weekly', 'Monthly', 'Yearly']
                    cols = st.columns(2) + st.columns(2)
                    
                    for i, p in enumerate(periods):
                        with cols[i]:
                            df = process_data(t_list, p, status, close_df, high_df, custom_mapping)
                            if not df.empty:
                                if is_top:
                                    df, t_name_display = format_top13_df(df, t_name)
                                else:
                                    df = sort_by_category(df)
                                    t_name_display = t_name
                                    
                                kst_now = get_korea_time()
                                if status in ['Live', 'Cycle']: target_str = kst_now.strftime('%b %d %H:%M KST Live')
                                else: target_str = f"{df['curr_date'].max().strftime('%b %d')} Close"
                                    
                                base_str = df['base_date'].max().strftime('%b %d')
                                sub_t = f"({target_str} vs {base_str})"
                                
                                t_func(df, f"{p}", sub_t, is_mini=True, is_ath=False)

if __name__ == '__main__':
    main()
