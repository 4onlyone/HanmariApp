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
# 1. 디자인 및 헌법 (색상, 포맷 - 불변)
# ==========================================
BAR_COLOR_MAP = {
    '원자재': '#C29200', '암호화폐': '#FF5E00', '한국증시': '#228B22', '미장': '#004A99', '기타': '#777777'
}

def get_text_color(change_value):
    if abs(change_value) < 0.05: return 'black'
    return '#0000FF' if change_value > 0 else '#FF0000'

def hanmari_format(value, name):
    dollar_list = ['금', '은', '동', 'BTC', 'ETH', '엔비디아', '애플', 'MS', '아마존', '구글', '테슬라', '브로드컴', '메타', '월마트', '일라이릴리', 'JP모건', 'TSMC', 'QQQ', 'MSTR']
    prefix = "$" if name in dollar_list else ""
    if value >= 100: return f"{prefix}{value:,.0f}"
    if value >= 10: return f"{prefix}{value:,.1f}"
    return f"{prefix}{value:,.2f}"

def get_korea_time():
    utc_now = datetime.now(pytz.utc)
    korea_timezone = pytz.timezone('Asia/Seoul')
    return utc_now.astimezone(korea_timezone)

# ==========================================
# 2. 데이터 엔진 (통합 티커 맵핑)
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
    # [통합] 모든 종목 티커 맵핑
    t_map = {
        # 글로벌 12 & 주요 시세 10
        '금': 'GC=F', '은': 'SI=F', '동': 'HG=F', 
        'BTC': 'BTC-USD', 'ETH': 'ETH-USD', 
        '코스피': '^KS11', '나스닥': '^IXIC', 'S&P': '^GSPC', 
        '달러': 'DX-Y.NYB', '환율': 'KRW=X', 
        '엔비디아': 'NVDA', '애플': 'AAPL', 'MS': 'MSFT', '아마존': 'AMZN', 
        '구글': 'GOOG', 'TSMC': 'TSM', '브로드컴': 'AVGO', '테슬라': 'TSLA', 
        '메타': 'META', '월마트': 'WMT', '일라이릴리': 'LLY', 'JP모건': 'JPM',
        # 내 투자일보 추가분
        'TIGER 200': '102110.KS', 'TIGER 200 중공업': '139260.KS',
        '삼성전자': '005930.KS', 'SK하이닉스': '000660.KS',
        'TIGER 미국나스닥100': '133690.KS', 'TIGER 미국테크TOP10': '381170.KS',
        'QQQ': 'QQQ', 'MSTR': 'MSTR', 'TIGER 금현물': '411060.KS'
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
            
            # 통합 카테고리 로직
            if name in ['금','은','동','TIGER 금현물']: cat = '원자재'
            elif name in ['BTC','ETH']: cat = '암호화폐'
            elif name in ['코스피', 'TIGER 200', 'TIGER 200 중공업', '삼성전자', 'SK하이닉스']: cat = '한국증시'
            elif name in ['달러', '환율', 'TSMC']: cat = '기타'
            else: cat = '미장'
            
            res.append({'name': name, 'price': curr, 'change': change, 'category': cat, 'base_date': display_base_date})
        except: continue
    return pd.DataFrame(res)

# ==========================================
# 3. 차트 그리기 함수들
# ==========================================

# [3-1] 글로벌 12 전용 (물결, Y축 135)
def draw_global_12_chart(df, main_title, sub_title, is_mini=False):
    if df.empty: return
    base_caps = {'금': 33.9, '엔비디아': 4.51, '은': 4.32, '애플': 4.08, 'MS': 2.98, '아마존': 2.26, '구글': 1.88, 'TSMC': 1.81, '브로드컴': 1.58, '테슬라': 1.54, '메타': 1.45, 'BTC': 1.37}
    df['market_cap'] = df['name'].map(base_caps).fillna(0)
    figsize = (5, 3.2) if is_mini else (8.5, 3.8) 
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=figsize, gridspec_kw={'height_ratios': [1, 3]})
    fig.subplots_adjust(hspace=0.03)

    colors = [BAR_COLOR_MAP.get(c, '#777777') for c in df['category']]
    
    ax1.bar(df['name'], df['market_cap'], color=colors, width=0.6)
    ax1.set_ylim(30, 38)
    ax1.set_yticks([30, 34, 38])
    for spine in ax1.spines.values(): spine.set_visible(True); spine.set_linewidth(0.8); spine.set_color('#CCCCCC')
    ax1.spines['bottom'].set_visible(False); ax1.xaxis.set_visible(False)
    
    ax2.bar(df['name'], df['market_cap'], color=colors, width=0.6)
    ax2.set_ylim(1, 5.5) 
    ax2.set_yticks([1, 3, 5])
    for spine in ax2.spines.values(): spine.set_visible(True); spine.set_linewidth(0.8); spine.set_color('#CCCCCC')
    ax2.spines['top'].set_visible(False)
    
    wave_x = np.linspace(0, 1, 100)
    ax1.plot(wave_x, np.sin(20 * np.pi * wave_x) * 0.008, transform=ax1.transAxes, color='#CCCCCC', lw=0.8, clip_on=False)
    ax2.plot(wave_x, 1 + np.sin(20 * np.pi * wave_x) * 0.008, transform=ax2.transAxes, color='#CCCCCC', lw=0.8, clip_on=False)

    ax1.tick_params(axis='y', labelsize=8 if not is_mini else 6)
    ax2.tick_params(axis='y', labelsize=8 if not is_mini else 6)

    for i, r in df.iterrows():
        if r['market_cap'] > 10:
            is_zero = abs(r['change']) < 0.05
            txt_col = 'black' if is_zero else get_text_color(r['change'])
            font_w = 'normal' if is_zero else 'bold'
            ax1.text(i, 35.5, f"{r['market_cap']}T", ha='center', va='bottom', fontsize=7 if is_mini else 9, fontweight='bold', color='black') 
            ax1.text(i, 35.2, f"({'+' if r['change']>0 else ''}{r['change']:.1f}%)", ha='center', va='top', fontsize=6 if is_mini else 8, fontweight=font_w, color=txt_col)
    for i, bar in enumerate(ax2.patches):
        if df.iloc[i]['market_cap'] <= 10:
            h = bar.get_height()
            c_val = df.iloc[i]['change']
            is_zero = abs(c_val) < 0.05
            txt_col = 'black' if is_zero else get_text_color(c_val)
            font_w = 'normal' if is_zero else 'bold'
            ax2.text(bar.get_x() + bar.get_width()/2, h + 0.5, f"{h}T", ha='center', va='bottom', fontsize=7 if is_mini else 9, fontweight='bold', color='black')
            ax2.text(bar.get_x() + bar.get_width()/2, h + 0.1, f"({'+' if c_val>0 else ''}{c_val:.1f}%)", ha='center', va='bottom', fontsize=6 if is_mini else 8, fontweight=font_w, color=txt_col)

    title_y = 1.15 if is_mini else 1.10
    main_fs = 10 if is_mini else 16
    sub_fs = 8 if is_mini else 12
    ax1.text(0.49, title_y, main_title, transform=ax1.transAxes, ha='right', va='bottom', fontsize=main_fs, fontweight='bold', color='black')
    ax1.text(0.51, title_y, sub_title, transform=ax1.transAxes, ha='left', va='bottom', fontsize=sub_fs, fontweight='normal', color='#555555')
    if not is_mini:
        lp = [mpatches.Patch(color=BAR_COLOR_MAP[k], label=k) for k in ['원자재','암호화폐','미장','기타']]
        ax1.legend(handles=lp, loc='upper right', frameon=True, fontsize=8)
    plt.xticks(rotation=0, ha='center', fontsize=6 if is_mini else 8)
    plt.tight_layout()
    st.pyplot(fig)

# [3-2] 주요 시세 10 전용
def draw_major_10_chart(df, main_title, sub_title, is_mini=False):
    if df.empty: return
    fig, ax = plt.subplots(figsize=(5, 3) if is_mini else (8.5, 4.5)) 
    colors = [BAR_COLOR_MAP.get(c, '#777777') for c in df['category']]
    bars = ax.bar(df['name'], df['change'], color=colors)
    ax.axhline(0, color='black', linewidth=1.0)
    for spine in ax.spines.values(): spine.set_visible(True); spine.set_linewidth(0.8); spine.set_color('#CCCCCC')
    for bar in bars:
        h = bar.get_height()
        va, offset = ('bottom', 5) if h >= 0 else ('top', -8)
        is_zero = abs(h) < 0.05
        text_color = 'black' if is_zero else get_text_color(h)
        font_w = 'normal' if is_zero else 'bold'
        ax.annotate(f'{h:.1f}%', xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, offset), textcoords="offset points", ha='center', va=va, fontname='Arial', fontweight=font_w, fontsize=7 if is_mini else 9, color=text_color)

    title_y = 1.12 if is_mini else 1.08
    main_fs = 10 if is_mini else 16
    sub_fs = 8 if is_mini else 12
    ax.text(0.49, title_y, main_title, transform=ax.transAxes, ha='right', va='bottom', fontsize=main_fs, fontweight='bold', color='black')
    ax.text(0.51, title_y, sub_title, transform=ax.transAxes, ha='left', va='bottom', fontsize=sub_fs, fontweight='normal', color='#555555')
    if not is_mini:
        lp = [mpatches.Patch(color=BAR_COLOR_MAP[k], label=k) for k in ['원자재','암호화폐','한국증시','미장','기타']]
        ax.legend(handles=lp, loc='upper right', frameon=True, fontsize=8)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100, decimals=0, symbol='%'))
    ax.tick_params(axis='y', labelsize=8 if not is_mini else 6)
    plt.xticks(rotation=0, ha='center', fontsize=6 if is_mini else 8)
    if not df.empty:
        y_min, y_max = df['change'].min(), df['change'].max()
        margin = max(abs(y_min), abs(y_max)) * 0.3 
        if margin < 1: margin = 1
        ax.set_ylim(y_min - margin, y_max + margin * 1.5) 
    plt.tight_layout()
    st.pyplot(fig)

# [3-3] 내 투자일보 전용 (하단 여백 확보)
def draw_my_portfolio_chart(df, main_title, sub_title, is_mini=False):
    if df.empty: return
    fig, ax = plt.subplots(figsize=(5, 3.2) if is_mini else (8.5, 4.0)) 
    colors = [BAR_COLOR_MAP.get(c, '#777777') for c in df['category']]
    bars = ax.bar(df['name'], df['change'], color=colors)
    ax.axhline(0, color='black', linewidth=1.0)
    for spine in ax.spines.values(): spine.set_visible(True); spine.set_linewidth(0.8); spine.set_color('#CCCCCC')
    for bar in bars:
        h = bar.get_height()
        va, offset = ('bottom', 5) if h >= 0 else ('top', -8)
        is_zero = abs(h) < 0.05
        text_color = 'black' if is_zero else get_text_color(h)
        font_w = 'normal' if is_zero else 'bold'
        ax.annotate(f'{h:.1f}%', xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, offset), textcoords="offset points", ha='center', va=va, fontname='Arial', fontweight=font_w, fontsize=7 if is_mini else 9, color=text_color)

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
    ax.yaxis.set_major_locator(mticker.MaxNLocator(nbins=4))
    plt.xticks(rotation=45 if not is_mini else 90, ha='right', fontsize=6 if is_mini else 8)
    if not df.empty:
        y_min, y_max = df['change'].min(), df['change'].max()
        margin = max(abs(y_min), abs(y_max)) * 0.3 
        if margin < 1: margin = 1
        ax.set_ylim(y_min - margin * 1.5, y_max + margin * 1.2) 
    plt.tight_layout()
    st.pyplot(fig)

# ==========================================
# 4. 메인 로직 (통합 메뉴)
# ==========================================
def main():
    st.set_page_config(page_title="한마리 금융 비서", layout="wide")
    st.sidebar.header("🛠️ 메뉴")
    
    # [통합] 메뉴 선택
    menu = st.sidebar.radio("모드 선택", ["일반 분석", "종합 리포트", "내 투자일보"])
    
    st.markdown("<h3 style='font-size: 22px; margin-bottom: 20px;'>📊 한마리 금융 비서</h3>", unsafe_allow_html=True)
    now = get_korea_time()
    curr_date_str = now.strftime('%y.%m.%d')
    curr_full_str = now.strftime('%y.%m.%d %H:%M')

    # [1] 일반 분석
    if menu == "일반 분석":
        st.sidebar.markdown("---")
        target_groups = st.sidebar.multiselect("대상 (다중 선택)", ["글로벌 Top 12", "주요 시세 10"], default=["글로벌 Top 12"])
        status = st.sidebar.radio("기준", ('Live', '마감', '주기'))
        period = st.sidebar.selectbox("기간", ('일간', '주간', '월간', '연간'))
        engine_status = 'Cycle' if status == '주기' else ('Completed' if status == '마감' else 'Live')
        if st.button('🚀 분석 시작', use_container_width=True):
            with st.spinner('데이터 분석 중...'):
                prefix = f"[{curr_full_str}]" if period == '일간' else f"[{curr_date_str}]"
                for target_group in target_groups:
                    st.markdown(f"#### {target_group}")
                    if target_group == "글로벌 Top 12":
                        target_list = ['금','엔비디아','은','애플','MS','아마존','구글','TSMC','브로드컴','테슬라','메타','BTC']
                        draw_func = draw_global_12_chart
                    else:
                        target_list = ['금','은','동','BTC','ETH','코스피','나스닥','S&P','달러','환율']
                        draw_func = draw_major_10_chart
                    df = fetch_data(target_list, period, engine_status)
                    if not df.empty:
                        base_d = df['base_date'].iloc[0].strftime('%y.%m.%d')
                        main_t = f"{prefix} {target_group}"
                        sub_t = f"({base_d} 기준)"
                        txt = f"{main_t} {sub_t}\n"
                        for i, r in df.iterrows():
                            arrow = '▲' if r['change']>0 else ('▼' if r['change']<0 else '-')
                            txt += f"{i+1}.{r['name']}{hanmari_format(r['price'], r['name'])}({arrow}{abs(r['change']):.1f}%)\n"
                        st.code(txt, language="text")
                        draw_func(df, main_t, sub_t)

    # [2] 종합 리포트
    elif menu == "종합 리포트":
        st.sidebar.markdown("---")
        report_targets = st.sidebar.multiselect("리포트 대상 (다중 선택)", ["글로벌 Top 12", "주요 시세 10"], default=["글로벌 Top 12"])
        report_status = st.sidebar.radio("리포트 기준", ["Live", "마감", "주기"])
        engine_status = 'Cycle' if report_status == '주기' else ('Completed' if report_status == '마감' else 'Live')
        if st.button('🚀 리포트 생성', use_container_width=True):
            st.write(f"조회 시점: {now.strftime('%y.%m.%d %H:%M')}")
            for target in report_targets:
                st.markdown(f"<h4 style='font-size: 18px; margin-top:20px;'>📑 {target} 종합 리포트 ({report_status})</h4>", unsafe_allow_html=True)
                periods = ['일간', '주간', '월간', '연간']
                col1, col2 = st.columns(2)
                col3, col4 = st.columns(2)
                cols_map = [col1, col2, col3, col4]
                if target == "글로벌 Top 12":
                    t_list = ['금','엔비디아','은','애플','MS','아마존','구글','TSMC','브로드컴','테슬라','메타','BTC']
                    draw_func = draw_global_12_chart
                else:
                    t_list = ['금','은','동','BTC','ETH','코스피','나스닥','S&P','달러','환율']
                    draw_func = draw_major_10_chart
                for i, p in enumerate(periods):
                    with cols_map[i]: 
                        with st.spinner(f'{p}...'):
                            df = fetch_data(t_list, p, engine_status)
                            if not df.empty:
                                base_d = df['base_date'].iloc[0].strftime('%y.%m.%d')
                                prefix = f"[{curr_full_str}]" if p == '일간' else f"[{curr_date_str}]"
                                draw_func(df, f"{prefix} {p}", f"({base_d} 기준)", is_mini=True)

    # [3] 내 투자일보 (신규)
    elif menu == "내 투자일보":
        st.sidebar.markdown("---")
        status = st.sidebar.radio("기준", ('Live', '마감', '주기'))
        engine_status = 'Cycle' if status == '주기' else ('Completed' if status == '마감' else 'Live')
        if st.button('🚀 리포트 생성', use_container_width=True):
            st.write(f"조회 시점: {now.strftime('%y.%m.%d %H:%M')}")
            st.markdown(f"<h4 style='font-size: 18px; margin-top:20px;'>📑 내 투자일보 종합 리포트 ({status})</h4>", unsafe_allow_html=True)
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