import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import matplotlib.ticker as mticker
import os
import platform
import requests
from datetime import datetime, timedelta
import pytz
import numpy as np

# ==========================================
# 0. 폰트 설정 (불변)
# ==========================================
@st.cache_resource
def font_setting():
    system_name = platform.system()
    if system_name == 'Windows':
        plt.rc('font', family='Malgun Gothic')
    elif system_name == 'Darwin':
        plt.rc('font', family='AppleGothic')
    else:
        font_path = "NanumGothic.ttf"
        if not os.path.exists(font_path):
            url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
            try:
                response = requests.get(url)
                with open(font_path, "wb") as f:
                    f.write(response.content)
            except: pass
        if os.path.exists(font_path):
            fm.fontManager.addfont(font_path)
            plt.rc('font', family='NanumGothic')
        else:
            plt.rc('font', family='sans-serif')

    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['font.weight'] = 'bold'

font_setting()

# ==========================================
# 1. 디자인 및 헌법 (불변)
# ==========================================
BAR_COLOR_MAP = {
    '원자재': '#C29200', '암호화폐': '#FF5E00', '한국증시': '#228B22', '미장': '#004A99', '기타': '#777777'
}

def get_text_color(change_value):
    if abs(change_value) < 0.05: return 'black'
    return '#0000FF' if change_value > 0 else '#FF0000'

def hanmari_format(value, name):
    dollar_list = ['테슬라', 'QQQ', 'MSTR', 'BTC', 'ETH']
    prefix = "$" if name in dollar_list else ""
    if name not in dollar_list:
        return f"{value:,.0f}"
    
    if value >= 100: return f"{prefix}{value:,.0f}"
    if value >= 10: return f"{prefix}{value:,.1f}"
    return f"{prefix}{value:,.2f}"

def get_korea_time():
    utc_now = datetime.now(pytz.utc)
    korea_timezone = pytz.timezone('Asia/Seoul')
    return utc_now.astimezone(korea_timezone)

# ==========================================
# 2. 데이터 엔진 (BTC/ETH 추가)
# ==========================================
def get_base_date(period_type, mode):
    today = get_korea_time().date()
    if mode == 'CYCLE': 
        if '연간' in period_type: return today - timedelta(days=365)
        if '월간' in period_type: return today - timedelta(days=30)
        if '주간' in period_type: return today - timedelta(days=7)
        if '일간' in period_type: return today - timedelta(days=1)
    else: 
        if '연간' in period_type: return datetime(today.year - 1, 12, 31).date()
        if '월간' in period_type: return (today.replace(day=1) - timedelta(days=1))
        if '주간' in period_type:
            days_sub = today.weekday() + 1
            return today - timedelta(days=days_sub)
        if '일간' in period_type:
            return today - timedelta(days=1)
    return None

def get_price_at_date(ticker, target_date):
    start_date = target_date - timedelta(days=7)
    end_date = target_date + timedelta(days=2)
    try:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if df.empty: return None
        df.index = df.index.date
        past_data = df[df.index <= target_date]
        return float(past_data['Close'].iloc[-1].item()) if not past_data.empty else None
    except: return None

def fetch_data(target_list, period_type, status_mode):
    # [수정] BTC/ETH 추가된 맵핑
    t_map = {
        'TIGER 200': '102110.KS',
        'TIGER 200 중공업': '139260.KS',
        '삼성전자': '005930.KS',
        'SK하이닉스': '000660.KS',
        'TIGER 미국나스닥100': '133690.KS',
        'TIGER 미국테크TOP10': '381170.KS',
        'QQQ': 'QQQ',
        '테슬라': 'TSLA',
        'MSTR': 'MSTR',
        'TIGER 금현물': '411060.KS',
        'BTC': 'BTC-USD',
        'ETH': 'ETH-USD'
    }
    
    res = []
    calc_mode = 'CYCLE' if status_mode == 'Cycle' else 'FM'
    display_base_date = get_base_date(period_type, calc_mode)
    today = get_korea_time().date()

    for name in target_list:
        ticker = t_map.get(name)
        try:
            recent = yf.download(ticker, period="1mo", progress=False)
            if recent.empty: continue
            last_idx_date = recent.index[-1].date()
            if status_mode == 'Completed':
                if last_idx_date == today:
                    if len(recent) < 2: continue
                    curr = float(recent['Close'].iloc[-2].item())
                else:
                    curr = float(recent['Close'].iloc[-1].item())
            else:
                curr = float(recent['Close'].iloc[-1].item())

            if '일간' in period_type and status_mode != 'Cycle':
                if status_mode == 'Completed':
                     display_base_date = today - timedelta(days=2)
                else:
                     display_base_date = today - timedelta(days=1)
                base = get_price_at_date(ticker, display_base_date)
            else:
                base = get_price_at_date(ticker, display_base_date)
            
            base = base if base else curr
            change = ((curr - base) / base) * 100
            
            # 카테고리 분류 (BTC/ETH는 암호화폐)
            if name == 'TIGER 금현물': cat = '원자재'
            elif name in ['TIGER 200', 'TIGER 200 중공업', '삼성전자', 'SK하이닉스']: cat = '한국증시'
            elif name in ['BTC', 'ETH']: cat = '암호화폐'
            else: cat = '미장'
            
            res.append({'name': name, 'price': curr, 'change': change, 'category': cat, 'base_date': display_base_date})
        except: continue
    return pd.DataFrame(res)

# ==========================================
# 3. 차트 그리기
# ==========================================

# [내 투자일보 전용]
def draw_my_portfolio_chart(df, main_title, sub_title, is_mini=False):
    if df.empty: return
    # 12개 항목이므로 가독성을 위해 살짝 더 넓게 잡을 수도 있지만, 컴팩트함 유지
    fig, ax = plt.subplots(figsize=(5, 3.2) if is_mini else (8.5, 4.0)) 
    
    colors = [BAR_COLOR_MAP.get(c, '#777777') for c in df['category']]
    bars = ax.bar(df['name'], df['change'], color=colors)
    ax.axhline(0, color='black', linewidth=1.0)

    for spine in ax.spines.values():
        spine.set_visible(True); spine.set_linewidth(0.8); spine.set_color('#CCCCCC')

    for bar in bars:
        h = bar.get_height()
        va, offset = ('bottom', 5) if h >= 0 else ('top', -8)
        is_zero = abs(h) < 0.05
        text_color = 'black' if is_zero else get_text_color(h)
        font_w = 'normal' if is_zero else 'bold'
        ax.annotate(f'{h:.1f}%', xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, offset), textcoords="offset points", ha='center', va=va, fontname='Arial', fontweight=font_w, fontsize=7 if is_mini else 9, color=text_color)

    # 제목 (한 줄)
    title_y = 1.12 if is_mini else 1.08
    main_fs = 10 if is_mini else 16
    sub_fs = 8 if is_mini else 12
    ax.text(0.49, title_y, main_title, transform=ax.transAxes, ha='right', va='bottom', fontsize=main_fs, fontweight='bold', color='black')
    ax.text(0.51, title_y, sub_title, transform=ax.transAxes, ha='left', va='bottom', fontsize=sub_fs, fontweight='normal', color='#555555')
    
    if not is_mini:
        lp = [mpatches.Patch(color=BAR_COLOR_MAP[k], label=k) for k in ['한국증시','미장','암호화폐','원자재']]
        ax.legend(handles=lp, loc='upper right', frameon=True, fontsize=8)
    
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100, decimals=0, symbol='%'))
    ax.tick_params(axis='y', labelsize=8 if not is_mini else 6)
    
    # Y축 눈금 넓게 (최대 4~5개)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(nbins=4))

    plt.xticks(rotation=45 if not is_mini else 90, ha='right', fontsize=6 if is_mini else 8)
    
    # [수정] 마이너스 여백 확보 (하단 마진 대폭 증가)
    if not df.empty:
        y_min, y_max = df['change'].min(), df['change'].max()
        margin = max(abs(y_min), abs(y_max)) * 0.3 
        if margin < 1: margin = 1
        
        # 하단(y_min) 쪽 여백을 1.5배 더 줘서 글자가 잘리지 않게 함
        ax.set_ylim(y_min - margin * 1.5, y_max + margin * 1.2) 

    plt.tight_layout()
    st.pyplot(fig)

# ==========================================
# 4. 메인 로직
# ==========================================
def main():
    st.set_page_config(page_title="한마리 금융 비서", layout="wide")
    st.sidebar.header("🛠️ 메뉴")
    
    mode_select = st.sidebar.radio("모드 선택", ["내 투자일보"]) 
    
    st.markdown("<h3 style='font-size: 22px; margin-bottom: 20px;'>📊 한마리 금융 비서 - 내 투자일보</h3>", unsafe_allow_html=True)
    now = get_korea_time()
    curr_date_str = now.strftime('%y.%m.%d')
    curr_full_str = now.strftime('%y.%m.%d %H:%M')

    st.sidebar.markdown("---")
    
    status = st.sidebar.radio("기준", ('Live', '마감', '주기'))
    engine_status = 'Cycle' if status == '주기' else ('Completed' if status == '마감' else 'Live')

    if st.button('🚀 리포트 생성', use_container_width=True):
        st.write(f"조회 시점: {now.strftime('%y.%m.%d %H:%M')}")
        
        st.markdown(f"<h4 style='font-size: 18px; margin-top:20px;'>📑 내 투자일보 종합 리포트 ({status})</h4>", unsafe_allow_html=True)
        
        # [수정] BTC, ETH 포함 총 12개 리스트
        my_list = ['TIGER 200', 'TIGER 200 중공업', '삼성전자', 'SK하이닉스', 'TIGER 미국나스닥100', 'TIGER 미국테크TOP10', 'QQQ', '테슬라', 'MSTR', 'TIGER 금현물', 'BTC', 'ETH']
        
        periods = ['일간', '주간', '월간', '연간']
        col1, col2 = st.columns(2)
        col3, col4 = st.columns(2)
        cols_map = [col1, col2, col3, col4]

        for i, p in enumerate(periods):
            with cols_map[i]: 
                with st.spinner(f'{p}...'):
                    df = fetch_data(my_list, p, engine_status)
                    if not df.empty:
                        base_d = df['base_date'].iloc[0].strftime('%y.%m.%d')
                        prefix = f"[{curr_full_str}]" if p == '일간' else f"[{curr_date_str}]"
                        draw_my_portfolio_chart(df, f"{prefix} {p}", f"({base_d} 기준)", is_mini=True)
                        
        st.markdown("---")
        st.markdown("#### 📋 상세 시세표 (일간 기준)")
        df_daily = fetch_data(my_list, '일간', engine_status)
        if not df_daily.empty:
            txt = ""
            for i, r in df_daily.iterrows():
                arrow = '▲' if r['change']>0 else ('▼' if r['change']<0 else '-')
                txt += f"{i+1}.{r['name']} {hanmari_format(r['price'], r['name'])} ({arrow}{abs(r['change']):.1f}%)\n"
            st.code(txt, language="text")

if __name__ == '__main__':
    main()