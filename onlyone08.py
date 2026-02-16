import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import os
import platform
import requests
from datetime import datetime, timedelta

# ==========================================
# 0. 폰트 설정 (유지)
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
# 1. [복구] 자산군별 절대 고정 색상 (헌법)
# ==========================================
COLOR_MAP = {
    '원자재': '#C29200',   # 짙은 황동색
    '암호화폐': '#FF5E00', # 선명한 주황색
    '한국증시': '#228B22', # 포레스트 그린
    '미장': '#004A99',     # 다크 블루
    '기타': '#777777'      # 회색
}

# ==========================================
# 2. 한마리 헌법 (숫자 포맷)
# ==========================================
def hanmari_format(value, name):
    dollar_list = ['금', '은', '동', 'BTC', 'ETH', '엔비디아', '애플', 'MS', '아마존', '구글', '테슬라', '브로드컴', '메타', '월마트', '일라이릴리', 'JP모건', 'TSMC']
    prefix = "$" if name in dollar_list else ""
    if value >= 100: return f"{prefix}{value:,.0f}"
    if value >= 10: return f"{prefix}{value:,.1f}"
    return f"{prefix}{value:,.2f}"

# ==========================================
# 3. 데이터 엔진 (유지)
# ==========================================
def get_historical_price(ticker, days_ago):
    target_date = (datetime.now() - timedelta(days=days_ago)).date()
    start_date = target_date - timedelta(days=20)
    end_date = target_date + timedelta(days=1)
    try:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if df.empty: return None
        df.index = df.index.date
        past_data = df[df.index <= target_date]
        return float(past_data['Close'].iloc[-1].item()) if not past_data.empty else None
    except: return None

def fetch_data(target_list, period_option, status_option):
    t_map = {'금': 'GC=F', '은': 'SI=F', '동': 'HG=F', 'BTC': 'BTC-USD', 'ETH': 'ETH-USD', '코스피': '^KS11', '나스닥': '^IXIC', 'S&P': '^GSPC', '달러': 'DX-Y.NYB', '환율': 'KRW=X', '엔비디아': 'NVDA', '애플': 'AAPL', 'MS': 'MSFT', '아마존': 'AMZN', '구글': 'GOOG', 'TSMC': 'TSM', '브로드컴': 'AVGO', '테슬라': 'TSLA', '메타': 'META', '월마트': 'WMT', '일라이릴리': 'LLY', 'JP모건': 'JPM'}
    
    days = 1 if '일간' in period_option else 7 if '주간' in period_option else 30 if '월간' in period_option else 365
    res = []
    
    for name in target_list:
        ticker = t_map.get(name)
        try:
            recent = yf.download(ticker, period="1mo", progress=False)
            if recent.empty: continue
            
            last_date = recent.index[-1].date()
            today_date = datetime.now().date()
            
            if '마감' in status_option:
                if last_date == today_date:
                    if len(recent) < 2: continue
                    curr = float(recent['Close'].iloc[-2].item())
                    curr_date = recent.index[-2].date()
                else:
                    curr = float(recent['Close'].iloc[-1].item())
                    curr_date = last_date
            else:
                curr = float(recent['Close'].iloc[-1].item())
                curr_date = last_date

            if '일간' in period_option:
                past_data = recent[recent.index.date < curr_date]
                base = float(past_data['Close'].iloc[-1].item()) if not past_data.empty else curr
            else:
                search_date = curr_date - timedelta(days=days)
                mask = recent.index.date <= search_date
                filtered = recent[mask]
                base = float(filtered['Close'].iloc[-1].item()) if not filtered.empty else get_historical_price(ticker, days + (1 if '마감' in status_option else 0))

            base = base if base else curr
            change = ((curr - base) / base) * 100
            
            # 카테고리 분류 (색상 매핑용)
            if name in ['금','은','동']: cat = '원자재'
            elif name in ['BTC','ETH']: cat = '암호화폐'
            elif name == '코스피': cat = '한국증시'
            elif name in ['달러', '환율']: cat = '기타'
            else: cat = '미장'
            
            res.append({'name': name, 'price': curr, 'change': change, 'category': cat})
        except: continue
    return pd.DataFrame(res)

# ==========================================
# 4. 차트 그리기 (색상 복구 & 숫자 색 변경)
# ==========================================
def draw_chart(df, title, is_global=False):
    if df.empty: return
    fig, ax = plt.subplots(figsize=(8.5, 4.5)) 
    
    # [복구] 막대 색상은 자산군별 고정 색상 사용 (절대 규칙)
    colors = [COLOR_MAP.get(c, '#777777') for c in df['category']]
    bars = ax.bar(df['name'], df['change'], color=colors)
    ax.axhline(0, color='black', linewidth=1.0)

    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.8)
        spine.set_color('#CCCCCC') 

    # [수정] 숫자(라벨) 색상 변경: 상승=파랑(#0000FF), 하락=빨강(#FF0000)
    for bar in bars:
        h = bar.get_height()
        va, offset = ('bottom', 5) if h >= 0 else ('top', -8)
        
        # 숫자 색상 결정
        text_color = '#0000FF' if h >= 0 else '#FF0000'
        
        ax.annotate(f'{h:.1f}%', 
                    xy=(bar.get_x() + bar.get_width()/2, h), 
                    xytext=(0, offset), 
                    textcoords="offset points", 
                    ha='center', va=va, 
                    fontname='Arial', fontweight='bold', fontsize=9,
                    color=text_color) # 여기에 색상 적용

    # 제목 폰트 (작고 겸손하게 유지)
    ax.set_title(title, fontsize=12, fontweight='bold', pad=15)

    # [복구] 범례: 자산군별 색상으로 복귀
    lp = [mpatches.Patch(color=COLOR_MAP['원자재'], label='원자재'), 
          mpatches.Patch(color=COLOR_MAP['암호화폐'], label='암호화폐'), 
          mpatches.Patch(color=COLOR_MAP['한국증시'], label='한국증시'), 
          mpatches.Patch(color=COLOR_MAP['미장'], label='미장')]
    
    if is_global: lp.pop(2) # 글로벌에선 한국증시 제외
    ax.legend(handles=lp, loc='upper right', frameon=True, fontsize=8)
    
    # X축: 회전 없음(0), 폰트 작게(8) (유지)
    plt.xticks(rotation=0, ha='center', fontsize=8)
    
    margin = max(abs(df['change'].max()), abs(df['change'].min())) * 0.5
    ax.set_ylim(df['change'].min() - margin, df['change'].max() + margin)
    for l in ax.get_yticklabels(): l.set_fontname('Arial')
    plt.tight_layout()
    st.pyplot(fig)

# ==========================================
# 5. 메인 실행부 (유지)
# ==========================================
def main():
    st.set_page_config(page_title="한마리 비서", layout="wide")
    
    st.sidebar.header("🛠️ 설정")
    status = st.sidebar.radio("1. 기준", ('실시간(Live)', '마감(Completed)'))
    period_raw = st.sidebar.selectbox("2. 기간", ('일간(Daily)', '주간(Weekly)', '월간(Monthly)', '연간(Yearly)'))
    show_g, show_m = st.sidebar.checkbox("글로벌 Top 15", value=True), st.sidebar.checkbox("주요 시세 10", value=True)
    
    period_clean = period_raw.split('(')[0]
    header_info = f"{status} / {period_clean}"

    # 제목 작게 유지
    st.markdown("<h3 style='font-size: 22px; margin-bottom: 20px;'>📊 한마리 주식 비서</h3>", unsafe_allow_html=True)

    if st.button('🚀 분석 시작', use_container_width=True):
        with st.spinner('데이터 수집 중...'):
            curr_t = pd.Timestamp.now().strftime('%m/%d %H:%M')
            if show_g:
                st.markdown(f"<div style='font-size: 16px; font-weight: bold; margin-top: 20px; margin-bottom: 10px;'>🌍 글로벌 Top 15 | {header_info}</div>", unsafe_allow_html=True)
                df_g = fetch_data(['금','엔비디아','은','애플','MS','아마존','구글','TSMC','브로드컴','테슬라','메타','BTC','월마트','일라이릴리','JP모건'], period_raw, status)
                txt = f"[{curr_t} {header_info}]\n"
                for i, r in df_g.iterrows():
                    txt += f"{i+1}.{r['name']}{hanmari_format(r['price'], r['name'])}({'▲' if r['change']>=0 else '▼'}{abs(r['change']):.1f}%)\n"
                st.code(txt, language="text")
                draw_chart(df_g, f"글로벌 Top 15 ({period_clean})", is_global=True)
            
            if show_m:
                st.markdown(f"<div style='font-size: 16px; font-weight: bold; margin-top: 20px; margin-bottom: 10px;'>📉 주요 시세 10 | {header_info}</div>", unsafe_allow_html=True)
                df_m = fetch_data(['금','은','동','BTC','ETH','코스피','나스닥','S&P','달러','환율'], period_raw, status)
                txt = f"[{curr_t} {header_info}]\n"
                for i, r in df_m.iterrows():
                    txt += f"{i+1}.{r['name']}{hanmari_format(r['price'], r['name'])}({'▲' if r['change']>=0 else '▼'}{abs(r['change']):.1f}%)\n"
                st.code(txt, language="text")
                draw_chart(df_m, f"주요 시세 10 ({period_clean})", is_global=False)

if __name__ == '__main__':
    main()