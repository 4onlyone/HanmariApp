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
import requests
import base64
import io

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
    "Slot_A": {
        "name": "기본", 
        "tickers": "PLTR=Palantir, TSLA=Tesla, 102110.KS=Tiger 200, 139230.KS=Tiger 200 중공업, 411060.KS=Tiger 금현물, BTC, ETH, XRP-USD=XRP, SOL-USD=SOL, KAIA-USD=KAIA, 133690.KS=Tiger QQQ, 028300.KQ=HLB, 204320.KS=HL만도"
    },
    "Slot_B": {
        "name": "나의 투자", 
        "tickers": "133690.KS=Tiger QQQ, 381170.KS=Tiger 테크TOP10, 139230.KS=Tiger 200 중공업, 411060.KS=Tiger 금현물, TSLA=Tesla, 102110.KS=Tiger 200, QQQ, PLTR=Palantir, 042370.KQ=비츠로테크, BTC, ETH"
    },
    "Slot_C": {
        "name": "국가별 Tiger ETF", 
        "tickers": "133690.KS=Tiger QQQ, 360750.KS=Tiger S&P500, 241180.KS=Tiger 일본, 453950.KS=Tiger 대만, 453870.KS=Tiger 인도, 192090.KS=Tiger 중국, 195930.KS=Tiger 유럽, 102110.KS=Tiger 200"
    },
    "Slot_D": {
        "name": "Macro&Crypto", 
        "tickers": "USO=WTI Crude, BNO=Brent Crude, Gold, Silver, Copper, BTC, ETH, XRP-USD=XRP, SOL-USD=SOL, KAIA-USD=KAIA"
    }
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
    'K-Market': '#228B22', 'Real Estate': '#000000', 'Others': '#777777'
}

TICKERS = {
    'Gold': 'GC=F', 'Silver': 'SI=F', 'Copper': 'HG=F', 'BTC': 'BTC-USD', 'ETH': 'ETH-USD',
    'KOSPI': '^KS11', 'NASDAQ': '^IXIC', 'S&P 500': '^GSPC', 'Dollar Index': 'DX-Y.NYB', 'USD/KRW': 'KRW=X',
    'NVDA': 'NVDA', 'AAPL': 'AAPL', 'MSFT': 'MSFT', 'AMZN': 'AMZN', 'GOOG': 'GOOG', 
    'TSMC': 'TSM', 'AVGO': 'AVGO', 'TSLA': 'TSLA', 'META': 'META', 
    'Samsung': '005930.KS', 'SK Hynix': '000660.KS', 'QQQ': 'QQQ', 'MSTR': 'MSTR',
    'Tiger 200': '102110.KS', 'Tiger 중공업': '139230.KS', 'Tiger Nasdaq': '133690.KS', 
    'Tiger US Tech': '381170.KS', 'Tiger 금현물': '411060.KS',
    'HLB': '028300.KQ', 'HL만도': '204320.KS',
    'Seoul APT': 'REAL_ESTATE'
}

SHARES_B = {
    'Gold': 6.83, 'Silver': 56.0, 'AAPL': 15.4, 'NVDA': 24.5, 'MSFT': 7.43, 'AMZN': 10.39, 
    'GOOG': 12.43, 'TSMC': 5.18, 'AVGO': 4.63, 'TSLA': 3.18, 'META': 2.54, 'BTC': 0.01999,
    'Samsung': 6.791, 'PLTR': 2.3, 'ETH': 0.12, 'SK Hynix': 0.728
}

def get_text_color(change_val):
    if abs(change_val) < 0.005: 
        return 'black'
    return 'blue' if change_val > 0 else 'red'

def format_value_auto(value):
    if value >= 100: 
        return f"{value:,.0f}"
    if value >= 10: 
        return f"{value:,.1f}"
    return f"{value:,.2f}"

def format_price(value, name, category='Others'):
    krw_assets = ['Samsung', 'SK Hynix', 'Tiger', 'TIGER', '테크TOP10', '중공업', '비츠로테크', '금현물', 'HLB', 'HL만도']
    no_sym_assets = ['KOSPI', 'USD/KRW', 'Dollar Index', 'Seoul APT']
    
    if any(x in name for x in no_sym_assets): 
        prefix = ""
    elif any(x in name for x in krw_assets) or category == 'K-Market' or 'Tiger' in name or 'TIGER' in name or 'HANARO' in name: 
        prefix = "₩"
    else: 
        prefix = "$"
        
    return f"{prefix}{format_value_auto(value)}"

def format_pct_text(val, max_abs=1.0):
    if abs(val) < 0.005: 
        return "0.0%"
    if abs(val) >= 100: 
        dec = 0
    elif max_abs < 0.2: 
        dec = 2
    else: 
        dec = 1
        
    sign = '+' if val > 0 else '-'
    return f"{sign}{abs(val):.{dec}f}%"

def get_korea_time():
    return datetime.now(pytz.utc).astimezone(pytz.timezone('Asia/Seoul'))

def get_dynamic_hashtags(names, default_tags):
    tags = default_tags.copy()
    for name in names:
        clean_name = ''.join(e for e in name if e.isalnum())
        tag = f"#{clean_name}"
        if tag not in tags:
            tags.append(tag)
    return " ".join(tags)

# ==========================================
# 2. Data Engine & GitHub Fetcher
# ==========================================
@st.cache_data(ttl=300) 
def download_all_data():
    valid_tickers = [v for v in TICKERS.values() if v != 'REAL_ESTATE']
    df = yf.download(valid_tickers, period="10y", interval="1d", progress=False)
    close_df, high_df, open_df = parse_downloaded_data(df)
    return close_df, high_df, open_df, df

@st.cache_data(ttl=300)
def download_extra_data(tickers_tuple):
    clean_tickers = [t for t in tickers_tuple if t != 'REAL_ESTATE']
    if not clean_tickers: 
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = yf.download(clean_tickers, period="10y", interval="1d", progress=False)
    close_df, high_df, open_df = parse_downloaded_data(df)
    return close_df, high_df, open_df, df

def parse_downloaded_data(df):
    if df.empty: 
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    if isinstance(df.columns, pd.MultiIndex):
        level = 0 if 'Close' in df.columns.get_level_values(0) else 1
        close_df = df.xs('Close', axis=1, level=level)
        high_df = df.xs('High', axis=1, level=level)
        open_df = df.xs('Open', axis=1, level=level)
    else:
        close_df = pd.DataFrame(df['Close'])
        high_df = pd.DataFrame(df['High'])
        open_df = pd.DataFrame(df['Open'])
        
    close_df.index = pd.to_datetime(close_df.index).tz_localize(None)
    high_df.index = pd.to_datetime(high_df.index).tz_localize(None)
    open_df.index = pd.to_datetime(open_df.index).tz_localize(None)
    return close_df, high_df, open_df

@st.cache_data(ttl=600)
def fetch_github_real_estate(token):
    url = "https://api.github.com/repos/4onlyone/HanmariApp/contents/gangnam11_apt.csv"
    headers = {"Authorization": f"token {token}"} if token else {}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        content = base64.b64decode(data['content']).decode('utf-8')
        df = pd.read_csv(io.StringIO(content))
        df['Date'] = pd.to_datetime(df['Date']).dt.normalize()
        df = df.set_index('Date')
        df.iloc[:, 0] = pd.to_numeric(df.iloc[:, 0], errors='coerce')
        return df.dropna()
    return None

def update_github_real_estate(token, new_date, new_index):
    url = "https://api.github.com/repos/4onlyone/HanmariApp/contents/gangnam11_apt.csv"
    headers = {"Authorization": f"token {token}"} if token else {}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        sha = data['sha']
        content = base64.b64decode(data['content']).decode('utf-8')
        df = pd.read_csv(io.StringIO(content))
        
        new_date_str = pd.to_datetime(new_date).strftime('%Y-%m-%d')
        idx_col = df.columns[1] 
        
        if new_date_str in df['Date'].astype(str).values:
            df.loc[df['Date'].astype(str) == new_date_str, idx_col] = new_index
        else:
            new_row = pd.DataFrame({'Date': [new_date_str], idx_col: [new_index]})
            df = pd.concat([df, new_row], ignore_index=True)
        
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        
        new_csv = df.to_csv(index=False)
        new_content = base64.b64encode(new_csv.encode('utf-8')).decode('utf-8')
        
        put_data = {
            "message": f"Update Real Estate Data: {new_date_str}",
            "content": new_content,
            "sha": sha
        }
        put_res = requests.put(url, headers=headers, json=put_data)
        return put_res.status_code in [200, 201]
    return False

def process_data(target_names, period, status_mode, close_df, high_df, open_df, custom_mapping=None):
    if custom_mapping is None: 
        custom_mapping = {}
    res = []
    kst_now = get_korea_time()
    today_kst = kst_now.date()
    
    if 'KRW=X' in close_df.columns and not close_df['KRW=X'].dropna().empty:
        usd_krw = float(close_df['KRW=X'].dropna().iloc[-1])
    else:
        usd_krw = 1350.0

    for name in target_names:
        ticker = TICKERS.get(name) or custom_mapping.get(name)
        if not ticker or ticker not in close_df.columns: 
            continue
            
        series = close_df[ticker].dropna()
        if series.empty: 
            continue
        
        if name in ['Samsung', 'SK Hynix', 'KOSPI', 'TIGER 200', 'HLB', 'HL만도'] or '.KS' in ticker or '.KQ' in ticker or '^KS' in ticker: 
            cat = 'K-Market'
        elif name in ['BTC', 'ETH'] or '-USD' in ticker: 
            cat = 'Crypto'
        elif name in ['Gold', 'Silver', 'Copper', 'Dollar Index', 'USD/KRW', 'USO', 'BNO'] or '=F' in ticker: 
            cat = 'Macro'
        elif name in ['TSMC', '비츠로테크']: 
            cat = 'Others'
        elif name in ['NASDAQ', 'S&P 500', 'QQQ', 'NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOG', 'AVGO', 'TSLA', 'META', 'PLTR'] or '^GSPC' in ticker or '^IXIC' in ticker or (ticker.isalpha() and ticker.isupper()): 
            cat = 'US Tech'
        else: 
            cat = 'Others'

        if status_mode == 'ATH':
            curr, ath = float(series.iloc[-1]), float(high_df[ticker].dropna().max())
            change = ((curr - ath) / ath) * 100 if ath > 0 else 0
            curr_date, base_date = series.index[-1].date(), series.index[-1].date()
            
        elif status_mode == 'Completed' and period == 'Daily':
            if cat == 'Crypto':
                offset = 2 if kst_now.hour < 9 else 1
                t_date = today_kst - timedelta(days=offset)
                
                curr_s = series[series.index.date <= t_date]
                if ticker in open_df.columns:
                    o_series = open_df[ticker].dropna()
                    next_day = t_date + timedelta(days=1)
                    if (curr_s.empty or curr_s.index[-1].date() < t_date) and (not o_series[o_series.index.date == next_day].empty):
                        curr = float(o_series[o_series.index.date == next_day].iloc[-1])
                        curr_date = t_date
                    else:
                        if curr_s.empty: 
                            continue
                        curr = float(curr_s.iloc[-1])
                        curr_date = curr_s.index[-1].date()
                else:
                    if curr_s.empty: 
                        continue
                    curr = float(curr_s.iloc[-1])
                    curr_date = curr_s.index[-1].date()

                b_date = curr_date - timedelta(days=1)
                base_s = series[series.index.date <= b_date]
                if ticker in open_df.columns:
                    if (base_s.empty or base_s.index[-1].date() < b_date) and (not o_series[o_series.index.date == curr_date].empty):
                        base = float(o_series[o_series.index.date == curr_date].iloc[-1])
                        base_date = b_date
                    else:
                        base = float(base_s.iloc[-1]) if not base_s.empty else curr
                        base_date = base_s.index[-1].date() if not base_s.empty else curr_date
                else:
                    base = float(base_s.iloc[-1]) if not base_s.empty else curr
                    base_date = base_s.index[-1].date() if not base_s.empty else curr_date

                change = ((curr - base) / base) * 100 if base > 0 else 0

            elif cat in ['US Tech', 'Macro', 'Others']:
                offset = 2 if kst_now.hour < 6 else 1
                t_date = today_kst - timedelta(days=offset)
                while t_date.weekday() > 4: 
                    t_date -= timedelta(days=1)
                
                curr_s = series[series.index.date <= t_date]
                if curr_s.empty: 
                    continue
                curr = float(curr_s.iloc[-1])
                curr_date = curr_s.index[-1].date()
                
                base_s = series[series.index.date < curr_date]
                base = float(base_s.iloc[-1]) if not base_s.empty else curr
                change = ((curr - base) / base) * 100 if base > 0 else 0
                base_date = base_s.index[-1].date() if not base_s.empty else curr_date
            else:
                offset = 1 if (kst_now.hour < 15 or (kst_now.hour == 15 and kst_now.minute < 30)) else 0
                t_date = today_kst - timedelta(days=offset)
                while t_date.weekday() > 4: 
                    t_date -= timedelta(days=1)
                
                curr_s = series[series.index.date <= t_date]
                if curr_s.empty: 
                    continue
                curr = float(curr_s.iloc[-1])
                curr_date = curr_s.index[-1].date()
                
                base_s = series[series.index.date < curr_date]
                base = float(base_s.iloc[-1]) if not base_s.empty else curr
                change = ((curr - base) / base) * 100 if base > 0 else 0
                base_date = base_s.index[-1].date() if not base_s.empty else curr_date
                
        else:
            v_series = series[series.index.date < today_kst] if status_mode == 'Completed' else series 
            if v_series.empty: 
                continue
            curr, curr_date = float(v_series.iloc[-1]), v_series.index[-1].date()
            
            if status_mode == 'Cycle':
                t_base = curr_date - timedelta(days={'Daily':1, 'Weekly':7, 'Monthly':30, 'Yearly':365}.get(period, 0))
                b_series = series[series.index.date <= t_base]
            else:
                if period == 'Daily': 
                    b_series = series[series.index.date < curr_date]
                elif period == 'Weekly': 
                    b_series = series[series.index.date < (datetime.combine(curr_date, datetime.min.time()) - timedelta(days=curr_date.weekday())).date()]
                elif period == 'Monthly': 
                    b_series = series[series.index.date < curr_date.replace(day=1)]
                elif period == 'Yearly': 
                    b_series = series[series.index.date < curr_date.replace(month=1, day=1)]
                else: 
                    b_series = series.iloc[0:1]
                
            base = float(b_series.iloc[-1]) if not b_series.empty else curr
            change = ((curr - base) / base) * 100 if base > 0 else 0
            base_date = b_series.index[-1].date() if not b_series.empty else curr_date
        
        mcap = ((curr * SHARES_B[name]) / (usd_krw if cat == 'K-Market' else 1)) / 1000 if name in SHARES_B else 0
        res.append({
            'name': name, 
            'price': curr, 
            'change': change, 
            'category': cat, 
            'curr_date': curr_date, 
            'base_date': base_date, 
            'mcap': mcap
        })
        
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
    if abs(val) < 0.005: 
        return "0%"
    if abs(val) >= 100: 
        dec = 0
    elif max_abs < 0.2: 
        dec = 2
    else: 
        dec = 1
    sign = '▲' if val > 0 else '▼'
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
    if df.empty: 
        return
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
    
    max_top_mcap = df[df['mcap'] > 10]['mcap'].max() if not df[df['mcap'] > 10].empty else 34
    ax1_upper = int(np.ceil(max_top_mcap * 1.25))
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
        
        date_str = ""
        if max_date and r['curr_date'] < max_date:
            date_str = f"\n({r['curr_date'].month}/{r['curr_date'].day})"
            
        lbl = f"{format_value_auto(r['mcap'])}T\n{pct_str}{date_str}"
        (ax1 if r['mcap'] > 10 else ax2).text(i, r['mcap'] + (0.8 if r['mcap'] > 10 else 0.3), lbl, ha='center', va='bottom', fontsize=8, fontweight='bold', color=txt_col)

    fig.text(0.50, 0.98, main_title, ha='center', va='top', fontsize=16, fontweight='bold', color='black')
    fig.text(0.50, 0.92, f"({sub_title})", ha='center', va='top', fontsize=12, color='gray')
    
    lp = [mpatches.Patch(color=v, label=k) for k, v in CATEGORY_COLORS.items() if k in df['category'].values]
    ax1.legend(handles=lp, loc='upper right', frameon=True, fontsize=8, facecolor='white', edgecolor='#CCCCCC', ncol=len(lp))
        
    plt.tight_layout(rect=[0, 0, 1, 0.90])
    st.pyplot(fig)

def draw_normal_chart(df, main_title, sub_title):
    if df.empty: 
        return
    
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

        date_str = ""
        if max_date and r['curr_date'] < max_date:
            date_str = f"\n({r['curr_date'].month}/{r['curr_date'].day})"
            
        final_text = f"{pct_str}{date_str}"
        ax.annotate(final_text, xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, offset), textcoords="offset points", ha='center', va=va, fontweight='bold', fontsize=8, color=txt_col)

    fig.text(0.50, 0.98, main_title, ha='center', va='top', fontsize=16, fontweight='bold', color='black')
    fig.text(0.50, 0.90, f"({sub_title})", ha='center', va='top', fontsize=12, color='gray')
    
    lp = [mpatches.Patch(color=v, label=k) for k, v in CATEGORY_COLORS.items() if k in df['category'].values]
    ax.legend(handles=lp, loc='upper right', frameon=True, fontsize=8, facecolor='white', edgecolor='#CCCCCC', ncol=len(lp))
        
    if max_abs_change < 0.2: 
        dec_y = 2
    elif max_abs_change < 2.0: 
        dec_y = 1
    else: 
        dec_y = 0
    
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100, decimals=dec_y, symbol='%'))
    
    data_range = df['change'].max() - df['change'].min()
    if data_range == 0: 
        data_range = 1.0
    absolute_padding = data_range * (40.0 / 280.0) 
    
    ax.set_ylim(df['change'].min() - absolute_padding, df['change'].max() + absolute_padding) 
    
    plt.tight_layout(rect=[0, 0, 1, 0.88])
    st.pyplot(fig)

def generate_twitter_text(df, title, date_str, is_top=False):
    txt = f"[{title}]\n({date_str})\n\n"
    max_abs = df['change'].abs().max() if not df.empty else 1.0
    max_date = df['curr_date'].max() if not df.empty else None
    
    names = df['name'].tolist()
    default_tags = ["#Investing", "#MarketUpdate", "#Portfolio", "#HanMARI"]
    hashtags_str = get_dynamic_hashtags(names, default_tags)
    
    if is_top and 'display_rank' in df.columns:
        for _, r in df.iterrows():
            mcap_str = f"{format_value_auto(r['mcap'])}T"
            price_str = format_price(r['price'], r['name'], r['category'])
            change_str = format_pct_text(r['change'], max_abs)
            date_flag = f" [{r['curr_date'].month}/{r['curr_date'].day}]" if max_date and r['curr_date'] < max_date else ""
            txt += f"{r['display_rank']}. {r['name']} {mcap_str} ({price_str}, {change_str}){date_flag}\n"
        txt += f"\n{hashtags_str}"
        return txt
        
    for i, (_, r) in enumerate(df.iterrows(), 1):
        price_str = format_price(r['price'], r['name'], r['category'])
        change_str = format_pct_text(r['change'], max_abs)
        date_flag = f" [{r['curr_date'].month}/{r['curr_date'].day}]" if max_date and r['curr_date'] < max_date else ""
        txt += f"{i}. {r['name']} {price_str} ({change_str}){date_flag}\n"
        
    txt += f"\n{hashtags_str}"
    return txt

# ==========================================
# 4. New Trend Mode Chart
# ==========================================
def hex_to_rgba(hex_color, alpha):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f'rgba({r},{g},{b},{alpha})'
    return hex_color

def draw_trend_chart(targets, base_date, period, close_df, custom_mapping, github_token):
    if not targets:
        st.warning("비교할 항목을 하나 이상 선택해주세요.")
        return
    
    fig = go.Figure()
    base_dt = pd.to_datetime(base_date)
    category_counts = {}
    summary_data = [] 
    real_estate_last_date = None 
    
    styles = [
        {"alpha": 1.0, "dash": "solid"}, 
        {"alpha": 0.65, "dash": "solid"}, 
        {"alpha": 0.35, "dash": "solid"},
        {"alpha": 1.0, "dash": "dash"}, 
        {"alpha": 0.65, "dash": "dash"}, 
        {"alpha": 0.35, "dash": "dash"}
    ]

    end_points = []
    global_min_y = float('inf')
    global_max_y = float('-inf')
    global_max_x_date = pd.Timestamp.min

    for name in targets:
        ticker = TICKERS.get(name) or custom_mapping.get(name)
        if not ticker: 
            continue
        
        if ticker == "REAL_ESTATE":
            if not github_token:
                st.error("⚠️ 깃허브 토큰이 없습니다.")
                continue
            df_re = fetch_github_real_estate(github_token)
            if df_re is None or df_re.empty: 
                continue
                
            real_estate_last_date = df_re.index.max().date()
            start_dt = min(base_dt, df_re.index.min())
            end_dt = close_df.index.max() if not close_df.empty else pd.Timestamp.today().normalize()
            daily_idx = pd.date_range(start=start_dt, end=end_dt, freq='D')
            
            series = df_re.iloc[:, 0].reindex(daily_idx)
            series = series.interpolate(method='linear', limit_area='inside')
            series = series.ffill().bfill()
            series = series[series.index >= base_dt]
        else:
            if ticker not in close_df.columns: 
                continue
            series = close_df[ticker].dropna()
            series = series[series.index >= base_dt]
            
        if series.empty: 
            continue
            
        if period == "Weekly": 
            series = series.resample('W').last().dropna()
        elif period == "Monthly": 
            series = series.resample('ME').last().dropna()
        elif period == "Yearly": 
            series = series.resample('YE').last().dropna()
            
        if series.empty: 
            continue
        
        base_price = series.iloc[0]
        end_price = series.iloc[-1]
        pct_change = ((series - base_price) / base_price) * 100
        
        valid_change = pct_change.dropna()
        if not valid_change.empty:
            global_min_y = min(global_min_y, valid_change.min())
            global_max_y = max(global_max_y, valid_change.max())
            
            current_max_x = pct_change.index[-1]
            if current_max_x > global_max_x_date:
                global_max_x_date = current_max_x
        
        if name == 'Seoul APT': 
            cat = 'Real Estate'
        elif name in ['Samsung', 'SK Hynix', 'KOSPI', 'TIGER 200', 'HLB', 'HL만도'] or '.KS' in ticker or '.KQ' in ticker or '^KS' in ticker: 
            cat = 'K-Market'
        elif name in ['BTC', 'ETH'] or '-USD' in ticker: 
            cat = 'Crypto'
        elif name in ['Gold', 'Silver', 'Copper', 'Dollar Index', 'USD/KRW', 'USO', 'BNO'] or '=F' in ticker: 
            cat = 'Macro'
        elif name in ['TSMC', '비츠로테크']: 
            cat = 'Others'
        elif name in ['NASDAQ', 'S&P 500', 'QQQ', 'NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOG', 'AVGO', 'TSLA', 'META', 'PLTR'] or '^GSPC' in ticker or '^IXIC' in ticker or (ticker.isalpha() and ticker.isupper()): 
            cat = 'US Tech'
        else: 
            cat = 'Others'

        summary_data.append({
            'name': name, 
            'cat': cat, 
            'end_val': end_price, 
            'change_rate': ((end_price / base_price) - 1) * 100
        })
        
        base_color = CATEGORY_COLORS.get(cat, '#777777')
        
        if cat == 'Real Estate': 
            line_width = 2.0
            current_style = 'solid'
            line_color = base_color
        else:
            line_width = 1.5
            style_idx = category_counts.get(cat, 0) % len(styles)
            current_style = styles[style_idx]["dash"]
            alpha = styles[style_idx]["alpha"]
            line_color = hex_to_rgba(base_color, alpha)
            category_counts[cat] = category_counts.get(cat, 0) + 1
            
        fig.add_trace(go.Scatter(
            x=pct_change.index, 
            y=pct_change.values, 
            mode='lines', 
            name=name, 
            line=dict(width=line_width, color=line_color, dash=current_style)
        ))
        
        end_points.append({
            'name': name, 
            'x': pct_change.index[-1], 
            'y': pct_change.values[-1], 
            'color': line_color
        })

    if global_max_y == float('-inf'): 
        global_min_y, global_max_y = 0, 100
    y_range = [global_min_y, global_max_y]
    
    y_span = global_max_y - global_min_y if global_max_y != global_min_y else 10

    end_points.sort(key=lambda x: x['y'], reverse=True)
    if end_points:
        n_items = len(end_points)
        
        max_chars = max([len(ep['name']) for ep in end_points]) if end_points else 10
        required_pixels = 15 + (max_chars * 7) + 5
        
        assumed_plot_width = 800.0
        date_span_days = max(1, (global_max_x_date - pd.to_datetime(base_dt)).days)
        
        added_days = date_span_days * (required_pixels / assumed_plot_width)
        target_x_max = global_max_x_date + timedelta(days=added_days)
        
        arrow_days = date_span_days * (15.0 / assumed_plot_width) 
        
        text_x_pos = global_max_x_date + timedelta(days=arrow_days)
        
        optimal_spacing = y_span * 0.08  
        total_text_height = (n_items - 1) * optimal_spacing
        
        if total_text_height > y_span * 0.9:
            spacing = (y_span * 0.9) / (n_items - 1) if n_items > 1 else 0
            total_text_height = (n_items - 1) * spacing
        else:
            spacing = optimal_spacing
            
        center_y = (global_max_y + global_min_y) / 2
        start_y = center_y + (total_text_height / 2)
        
        for i, ep in enumerate(end_points):
            target_y = start_y - i * spacing if n_items > 1 else center_y
            
            fig.add_annotation(
                x=ep['x'], 
                y=ep['y'], 
                xref="x", 
                yref="y",
                text=f" <b>{ep['name']}</b>",
                showarrow=True, 
                arrowhead=0, 
                arrowwidth=1,  
                arrowcolor="rgba(150, 150, 150, 0.4)",
                ax=text_x_pos, 
                ay=target_y,  
                axref="x",     
                ayref="y",     
                font=dict(size=11, color=ep['color']),
                xanchor="left", 
                yanchor="middle"
            )

    fig.update_layout(
        font=dict(family="Malgun Gothic, Arial"), 
        plot_bgcolor='white', 
        paper_bgcolor='white', 
        hovermode="x unified", 
        height=450, 
        showlegend=False, 
        # [V9.6 수술] 외부 마진 최소화로 본체 풀-사이즈 100% 확장 적용
        margin=dict(l=20, r=20, t=100, b=20), 
        xaxis=dict(
            range=[base_dt, target_x_max],
            showline=True, 
            linewidth=1.5, 
            linecolor='#CCCCCC', 
            mirror=True, 
            showgrid=False, 
            ticks='outside'
        ),
        yaxis=dict(
            range=y_range, 
            showline=True, 
            linewidth=1.5, 
            linecolor='#CCCCCC', 
            mirror=True, 
            showgrid=False, 
            ticks='outside', 
            title="Cumulative Return (%)"
        )
    )

    fig.add_annotation(
        x=0.5, 
        y=1.15, 
        xref="paper", 
        yref="paper", 
        text="<b>Trend Analysis</b>", 
        showarrow=False, 
        font=dict(size=20, color="black"), 
        xanchor="center", 
        yanchor="bottom"
    )
    
    sub_title_text = f"<span style='color:gray; font-size:14px;'>({period}, Base: {base_date.strftime('%Y-%m-%d')})</span>"
    fig.add_annotation(
        x=0.5, 
        y=1.07, 
        xref="paper", 
        yref="paper", 
        text=sub_title_text, 
        showarrow=False, 
        xanchor="center", 
        yanchor="bottom"
    )

    st.plotly_chart(fig, use_container_width=True)
    
    if "Seoul APT" in targets:
        if real_estate_last_date and pd.Timestamp.today().date() > real_estate_last_date:
            st.caption(f"* Seoul APT = Gangnam 11Gu Average\n* Note: Data after {real_estate_last_date.strftime('%Y-%m-%d')} is forward-filled.")
        else:
            st.caption("* Seoul APT = Gangnam 11Gu Average")

    st.markdown("---")
    
    if summary_data:
        st.subheader("📝 Trend Summary")
        sum_lines = [f"[Trend Analysis]\n({base_dt.strftime('%Y-%m-%d')} ~ {pd.Timestamp.today().strftime('%Y-%m-%d')})\n"]
        max_abs = max([abs(d['change_rate']) for d in summary_data]) if summary_data else 100
        
        for i, d in enumerate(summary_data, 1):
            date_flag = ""
            if d['name'] == "Seoul APT" and real_estate_last_date and real_estate_last_date < pd.Timestamp.today().date():
                date_flag = f" [{real_estate_last_date.month}/{real_estate_last_date.day}]"
            
            p_str = format_price(d['end_val'], d['name'], d['cat'])
            c_str = format_pct_text(d['change_rate'], max_abs)
            sum_lines.append(f"{i}. {d['name']} {p_str} ({c_str}){date_flag}")
            
        tags = get_dynamic_hashtags([d['name'] for d in summary_data], ['#Investing', '#TrendAnalysis', '#HanMARI'])
        st.code("\n".join(sum_lines) + f"\n\n{tags}", language=None)

def draw_deep_dive_chart(ticker_symbol, raw_df, ticker_name, plot_days):
    try:
        if isinstance(raw_df.columns, pd.MultiIndex) and ticker_symbol in raw_df.columns.get_level_values(1):
            df = raw_df.xs(ticker_symbol, axis=1, level=1).copy()
        elif isinstance(raw_df.columns, pd.MultiIndex):
            df = raw_df.xs(ticker_symbol, axis=1, level=0).copy()
        else:
            df = raw_df.copy()
            
        df = df.dropna(subset=['Close'])
        if df.empty: 
            return st.warning("No data found.")
            
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df['SMA50'] = df['Close'].rolling(50).mean()
        df['SMA120'] = df['Close'].rolling(120).mean()
        df['SMA200'] = df['Close'].rolling(200).mean()
        
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        df['RSI14'] = 100 - (100 / (1 + (gain / loss)))
        
        plot_df = df.tail(plot_days)
        
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, 
            row_heights=[0.6, 0.2, 0.2], 
            subplot_titles=("", "<b>Volume</b>", "<b>RSI (14)</b>")
        )
        
        fig.add_trace(go.Candlestick(
            x=plot_df.index, open=plot_df['Open'], high=plot_df['High'], 
            low=plot_df['Low'], close=plot_df['Close'], name='Price'
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SMA50'], line=dict(color='blue', width=1.5), name='50 SMA'), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SMA120'], line=dict(color='orange', width=2), name='120 SMA'), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SMA200'], line=dict(color='red', width=1.5), name='200 SMA'), row=1, col=1)
        
        colors = ['red' if r['Close'] < r['Open'] else 'green' for _, r in plot_df.iterrows()]
        fig.add_trace(go.Bar(x=plot_df.index, y=plot_df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)
        
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['RSI14'], line=dict(color='purple', width=1.5), name='RSI'), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
        
        fig.update_xaxes(showline=False, mirror=False)
        fig.update_yaxes(showline=False, mirror=False)
        fig.add_shape(type="rect", xref="paper", yref="paper", x0=0, y0=0, x1=1, y1=1, line=dict(color="#CCCCCC", width=1.5), layer="above")

        # [V9.6 수술] 캔들 두께(0.5일) + 순수 5픽셀 여백 확보 
        assumed_plot_width = 800.0
        padding_days = 0.5 + (plot_days * 5.0 / assumed_plot_width)

        fig.update_layout(
            title=None,
            font=dict(family="Malgun Gothic, Arial"),
            height=750, 
            # [V9.6 수술] 외부 마진 최소화로 본체 풀-사이즈 100% 확장 적용
            margin=dict(l=20, r=20, t=100, b=20),
            xaxis=dict(range=[plot_df.index[0] - timedelta(days=padding_days), plot_df.index[-1] + timedelta(days=padding_days)]),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="top", y=0.99,
                xanchor="left", x=0.01,
                bgcolor="rgba(255, 255, 255, 0.85)", 
                bordercolor="#CCCCCC",
                borderwidth=1
            )
        )
        
        fig.add_annotation(
            x=0.5, y=1.08, xref="paper", yref="paper", 
            text=f"<b>{ticker_name} Technical Analysis</b>", 
            showarrow=False, font=dict(size=20, color="black"), xanchor="center", yanchor="bottom"
        )
        fig.add_annotation(
            x=0.5, y=1.03, xref="paper", yref="paper", 
            text=f"<span style='color:gray; font-size:14px;'>(Max {plot_days} Days)</span>", 
            showarrow=False, xanchor="center", yanchor="bottom"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.download_button(
            f"📥 Download {ticker_name} Raw Data", 
            data=df.to_csv().encode('utf-8'), 
            file_name=f"{ticker_name}_data.csv", 
            mime='text/csv', 
            use_container_width=True
        )
    except Exception as e: 
        st.error(f"Error: {e}")

# ==========================================
# 5. Main App & Sidebar
# ==========================================
def main():
    st.set_page_config(page_title="HanMARI V9.6", layout="wide")
    ports = load_portfolios()
    
    with st.sidebar:
        if st.button("🔄 Refresh Data", type="primary"): 
            st.cache_data.clear()
            st.rerun()
            
        mode = st.radio("View Mode", ["Market Overview", "Trend Analysis", "Deep Dive (Interactive)"])
        st.markdown("---")
        
        all_deep_dive_map = TICKERS.copy()
        for p in ports.values():
            for item in p['tickers'].split(','):
                item = item.strip()
                if not item: 
                    continue
                    
                if '=' in item:
                    t, n = [x.strip() for x in item.rsplit('=', 1)]
                    keys_to_remove = [k for k, v in all_deep_dive_map.items() if v == t]
                    for k in keys_to_remove: 
                        del all_deep_dive_map[k]
                    all_deep_dive_map[n] = t
                else:
                    if item not in all_deep_dive_map: 
                        all_deep_dive_map[item] = item
                
        if mode == "Market Overview":
            status = st.radio("Status", ('Live', 'Completed', 'Cycle', 'ATH'))
            
            if status == 'ATH':
                period = 'All'
            else:
                period = st.selectbox("Period", ('Daily', 'Weekly', 'Monthly', 'Yearly'))
                
            show_global = st.checkbox("Global Top 12+1", value=True)
            show_key = st.checkbox("Key Indicators", value=False)
            
            active_slots = {}
            for k in ports.keys():
                if st.checkbox(f"Show: {ports[k]['name']}", value=(k == "Slot_A")):
                    active_slots[k] = ports[k]
                    
        elif mode == "Trend Analysis":
            trend_base_date = st.date_input("1) 기준일", value=datetime.today() - timedelta(days=90))
            trend_period = st.selectbox("2) 주기", ["Daily", "Weekly", "Monthly", "Yearly"])
            trend_targets = []
            
            cat_groups = {
                'Real Estate': [], 'US Tech': [], 'K-Market': [], 
                'Crypto': [], 'Macro': [], 'Others': []
            }
            
            for name, ticker in all_deep_dive_map.items():
                if name == 'Seoul APT':
                    cat = 'Real Estate'
                elif name in ['Samsung', 'SK Hynix', 'KOSPI', 'TIGER 200', 'HLB', 'HL만도'] or '.KS' in ticker or '.KQ' in ticker or '^KS' in ticker:
                    cat = 'K-Market'
                elif name in ['BTC', 'ETH'] or '-USD' in ticker:
                    cat = 'Crypto'
                elif name in ['Gold', 'Silver', 'Copper', 'Dollar Index', 'USD/KRW', 'USO', 'BNO'] or '=F' in ticker:
                    cat = 'Macro'
                elif name in ['TSMC', '비츠로테크']:
                    cat = 'Others'
                elif name in ['NASDAQ', 'S&P 500', 'QQQ', 'NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOG', 'AVGO', 'TSLA', 'META', 'PLTR'] or '^GSPC' in ticker or '^IXIC' in ticker or (ticker.isalpha() and ticker.isupper()):
                    cat = 'US Tech'
                else:
                    cat = 'Others'
                cat_groups[cat].append(name)
                
            for cat, items in cat_groups.items():
                if items:
                    with st.expander(f"📁 {cat}"):
                        cols = st.columns(2)
                        for i, item in enumerate(items):
                            is_checked = item in ["BTC", "NASDAQ", "Gold", "Seoul APT"]
                            if cols[i%2].checkbox(item, value=is_checked): 
                                trend_targets.append(item)
                                
        else:
            valid_targets = {k:v for k,v in all_deep_dive_map.items() if v != 'REAL_ESTATE'}
            deep_dive_target = st.selectbox("Select Asset", options=list(valid_targets.keys()))
            
            tf_options = ["3 Months", "6 Months", "1 Year", "3 Years", "Max (10Y)"]
            tf_days = {"3 Months": 63, "6 Months": 126, "1 Year": 252, "3 Years": 756, "Max (10Y)": 2520}
            plot_days = tf_days[st.selectbox("Timeframe", tf_options, index=2)]

        # [V9.6 수술] 4개 포트폴리오 편집 슬롯 복구 
        st.markdown("---")
        with st.expander("🛠️ 포트폴리오 편집 (4개 슬롯)"):
            new_ports = {}
            for k, v in ports.items():
                st.markdown(f"**{k}**")
                new_name = st.text_input(f"이름 ({k})", value=v['name'], key=f"name_{k}")
                new_tickers = st.text_area(f"티커 ({k})", value=v['tickers'], key=f"tick_{k}", height=68)
                new_ports[k] = {"name": new_name, "tickers": new_tickers}
                
            if st.button("💾 포트폴리오 저장", use_container_width=True):
                save_portfolios(new_ports)
                st.success("저장 완료! 상단의 🔄 Refresh Data 버튼을 눌러주세요.")

        st.markdown("---")
        github_token = st.text_input("GitHub Token", type="password")
        
        if github_token:
            df_re = fetch_github_real_estate(github_token)
            if df_re is not None:
                max_date_str = df_re.index.max().strftime('%Y-%m-%d')
                st.caption(f"📌 Latest: {max_date_str} ({df_re.iloc[-1,0]})")
                
                with st.expander("✍️ Update Data"):
                    new_d = st.date_input("Date", value=df_re.index.max().date() + timedelta(days=7))
                    new_v = st.number_input("Value", value=float(df_re.iloc[-1,0]))
                    
                    if st.button("Push to GitHub"):
                        if update_github_real_estate(github_token, new_d, new_v): 
                            st.success("Updated!")
                            st.cache_data.clear()
                            st.rerun()
        else: 
            st.info("💡 토큰을 입력하면 업데이트 창이 활성화됩니다.")
            
        if st.button("⚠️ 초기화"): 
            if os.path.exists(PORTFOLIO_FILE): 
                os.remove(PORTFOLIO_FILE)
            st.cache_data.clear()
            st.rerun()

    st.markdown("<h3>📊 HanMARI V9.6</h3>", unsafe_allow_html=True)
    
    if st.button('🚀 Run Analysis', use_container_width=True):
        close_df, high_df, open_df, raw_df = download_all_data()
        
        extra_tickers = tuple(set(all_deep_dive_map.values()) - set(TICKERS.values()) - {'REAL_ESTATE'})
        e_close, e_high, e_open, e_raw = download_extra_data(extra_tickers)
        
        if not e_close.empty: 
            close_df = pd.concat([close_df, e_close], axis=1)
            high_df = pd.concat([high_df, e_high], axis=1)
            open_df = pd.concat([open_df, e_open], axis=1)
            raw_df = pd.concat([raw_df, e_raw], axis=1)
            
        if mode == "Deep Dive (Interactive)": 
            draw_deep_dive_chart(all_deep_dive_map[deep_dive_target], raw_df, deep_dive_target, plot_days)
            
        elif mode == "Trend Analysis": 
            draw_trend_chart(trend_targets, trend_base_date, trend_period, close_df, all_deep_dive_map, github_token)
            
        else:
            if show_global:
                g_targets = ['Gold','NVDA','Silver','AAPL','MSFT','AMZN','GOOG','TSMC','AVGO','TSLA','META','BTC','Samsung']
                df_g = process_data(g_targets, period, status, close_df, high_df, open_df)
                if not df_g.empty: 
                    df_g, t_name = format_top13_df(df_g, "Global Top 12+1")
                    sub_t = get_subtitle(status, df_g)
                    draw_top13_chart(df_g, f"{t_name} {period}", sub_t, is_ath=(status=='ATH'))
                    st.code(generate_twitter_text(df_g, t_name, sub_t, True), language=None)
                    
            if show_key:
                k_targets = ['Gold','Silver','Copper','BTC','ETH','KOSPI','NASDAQ','S&P 500','Dollar Index','USD/KRW']
                df_k = process_data(k_targets, period, status, close_df, high_df, open_df)
                if not df_k.empty: 
                    df_k = sort_by_category(df_k)
                    sub_t = get_subtitle(status, df_k)
                    draw_normal_chart(df_k, f"Key Indicators {period}", sub_t)
                    st.code(generate_twitter_text(df_k, "Key Indicators", sub_t), language=None)
                    
            for p_data in active_slots.values():
                names = []
                for n in p_data['tickers'].split(','):
                    if not n.strip(): continue
                    names.append(n.split('=')[1].strip() if '=' in n else n.strip())
                    
                df_c = process_data(names, period, status, close_df, high_df, open_df, all_deep_dive_map)
                if not df_c.empty: 
                    df_c = sort_by_category(df_c)
                    sub_t = get_subtitle(status, df_c)
                    draw_normal_chart(df_c, f"{p_data['name']} {period}", sub_t)
                    st.code(generate_twitter_text(df_c, p_data['name'], sub_t), language=None)

def get_subtitle(status, df):
    if status == 'ATH': 
        return "All-Time High"
    kst = get_korea_time()
    max_base = df['base_date'].max()
    return f"{kst.month}/{kst.day} {kst.strftime('%H:%M')} KST vs {max_base.month}/{max_base.day}"

if __name__ == '__main__': 
    main()