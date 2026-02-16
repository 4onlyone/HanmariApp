import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import platform
from datetime import datetime, timedelta

# ==========================================
# 1. 스타일 설정 (Bold 및 폰트)
# ==========================================
def set_style():
    system_name = platform.system()
    try:
        f_name = 'Malgun Gothic' if system_name == 'Windows' else 'AppleGothic' if system_name == 'Darwin' else 'NanumGothic'
        plt.rcParams.update({'font.family': f_name, 'axes.unicode_minus': False, 'font.weight': 'bold', 'axes.labelweight': 'bold', 'axes.titleweight': 'bold'})
    except:
        plt.rcParams['font.family'] = 'sans-serif'

# 자산군별 색상 (원자재 vs 암호화폐 대비 강화)
COLOR_MAP = {
    '원자재': '#C29200',   # 짙은 황동 (원숙함)
    '암호화폐': '#FF5E00', # 선명한 주황 (역동성)
    '한국증시': '#228B22', # 포레스트 그린
    '미장': '#004A99',     # 다크 블루
    '기타': '#777777'      # 회색
}

# ==========================================
# 2. 한마리 헌법 (숫자 포맷팅)
# ==========================================
def hanmari_format(value, name):
    dollar_assets = ['금', '은', '동', 'BTC', 'ETH', '엔비디아', '애플', 'MS', '아마존', '구글', '테슬라', '브로드컴', '메타', '월마트', '일라이릴리', 'JP모건', 'TSMC']
    prefix = "$" if name in dollar_assets else ""
    if value >= 100: return f"{prefix}{value:,.0f}"
    if value >= 10: return f"{prefix}{value:,.1f}"
    return f"{prefix}{value:,.2f}"

# ==========================================
# 3. 데이터 엔진 (집요한 탐색)
# ==========================================
def get_historical_price(ticker, days_ago):
    target_date = (datetime.now() - timedelta(days=days_ago)).date()
    start_date = target_date - timedelta(days=15)
    end_date = target_date + timedelta(days=1)
    try:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if df.empty: return None
        df.index = df.index.date
        past_data = df[df.index <= target_date]
        return float(past_data['Close'].iloc[-1].item()) if not past_data.empty else None
    except:
        return None

def fetch_data(target_list, period_option):
    t_map = {
        '금': 'GC=F', '은': 'SI=F', '동': 'HG=F', 'BTC': 'BTC-USD', 'ETH': 'ETH-USD',
        '코스피': '^KS11', '나스닥': '^IXIC', 'S&P': '^GSPC', '달러': 'DX-Y.NYB', '환율': 'KRW=X',
        '엔비디아': 'NVDA', '애플': 'AAPL', 'MS': 'MSFT', '아마존': 'AMZN', '구글': 'GOOG', 
        'TSMC': 'TSM', '브로드컴': 'AVGO', '테슬라': 'TSLA', '메타': 'META', '월마트': 'WMT', 
        '일라이릴리': 'LLY', 'JP모건': 'JPM'
    }
    days = 1 if '일간' in period_option else 7 if '주간' in period_option else 30 if '월간' in period_option else 365
    res = []
    for name in target_list:
        ticker = t_map.get(name)
        try:
            recent = yf.download(ticker, period="5d", progress=False)
            curr = float(recent['Close'].iloc[-1].item())
            if '일간' in period_option and len(recent) >= 2:
                base = float(recent['Close'].iloc[-2].item())
            else:
                base = get_historical_price(ticker, days)
            base = base if base else curr
            change = ((curr - base) / base) * 100
            
            if name in ['금','은','동']: cat = '원자재'
            elif name in ['BTC','ETH']: cat = '암호화폐'
            elif name == '코스피': cat = '한국증시'
            elif name in ['달러', '환율']: cat = '기타'
            else: cat = '미장'
            
            res.append({'name': name, 'price': curr, 'change': change, 'category': cat})
        except: continue
    return pd.DataFrame(res)

# ==========================================
# 4. 차트 그리기
# ==========================================
def draw_chart(df, title, is_global=False):
    if df.empty: return
    fig, ax = plt.subplots(figsize=(9, 4.5)) 
    
    colors = [COLOR_MAP.get(c, '#777777') for c in df['category']]
    bars = ax.bar(df['name'], df['change'], color=colors)
    ax.axhline(0, color='black', linewidth=1.0)

    # 외곽 박스 (연한 회색)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.8)
        spine.set_color('#CCCCCC') 

    # 수치 라벨 (Arial Bold)
    for bar in bars:
        h = bar.get_height()
        va, offset = ('bottom', 5) if h >= 0 else ('top', -8)
        ax.annotate(f'{h:.1f}%', xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, offset),
                    textcoords="offset points", ha='center', va=va, fontname='Arial', fontweight='bold', fontsize=9)

    ax.set_title(title, fontsize=14, fontweight='bold', pad=30)

    # 범례 구성
    if is_global:
        lp = [mpatches.Patch(color=COLOR_MAP['원자재'], label='원자재'),
              mpatches.Patch(color=COLOR_MAP['암호화폐'], label='암호화폐'),
              mpatches.Patch(color=COLOR_MAP['미장'], label='미장'),
              mpatches.Patch(color=COLOR_MAP['기타'], label='기타')]
    else:
        lp = [mpatches.Patch(color=COLOR_MAP['원자재'], label='원자재'),
              mpatches.Patch(color=COLOR_MAP['암호화폐'], label='암호화폐'),
              mpatches.Patch(color=COLOR_MAP['한국증시'], label='한국증시'),
              mpatches.Patch(color=COLOR_MAP['미장'], label='미장')]
    
    ax.legend(handles=lp, loc='upper right', frameon=True, fontsize=8)
    
    plt.xticks(rotation=45, ha='right', fontsize=10)

    margin = max(abs(df['change'].max()), abs(df['change'].min())) * 0.5
    ax.set_ylim(df['change'].min() - margin, df['change'].max() + margin)
    for l in ax.get_yticklabels(): l.set_fontname('Arial')
    
    plt.tight_layout()
    st.pyplot(fig)

# ==========================================
# 5. 메인 실행부
# ==========================================
def main():
    st.set_page_config(page_title="한마리 주식 비서", layout="wide")
    set_style()
    st.sidebar.header("🛠️ 분석 설정")
    status = st.sidebar.radio("1. 기준", ('실시간(Live)', '마감(Completed)'))
    period_raw = st.sidebar.selectbox("2. 기간", ('일간(Daily)', '주간(Weekly)', '월간(Monthly)', '연간(Yearly)'))
    
    show_global = st.sidebar.checkbox("글로벌 Top 15", value=True)
    show_major = st.sidebar.checkbox("주요 시세 10", value=True)
    
    st.title("📊 한마리 주식 비서")
    
    # [수정] 괄호 중복 제거 로직
    period_clean = period_raw.split('(')[0] # '일간'만 추출
    header_info = f"{status} / {period_clean}"

    if st.button('🚀 분석 시작', use_container_width=True):
        with st.spinner('데이터 수집 중... 충성!'):
            curr_t = pd.Timestamp.now().strftime('%m/%d %H:%M')
            
            if show_global:
                st.subheader(f"🌍 글로벌 Top 15 | {header_info}")
                df_g = fetch_data(['금','엔비디아','은','애플','MS','아마존','구글','TSMC','브로드컴','테슬라','메타','BTC','월마트','일라이릴리','JP모건'], period_raw)
                
                # 텍스트 출력 [가독성 최적화 버전]
                txt = f"[{curr_t} {header_info}]\n"
                for i, r in df_g.iterrows():
                    txt += f"{i+1}.{r['name']}{hanmari_format(r['price'], r['name'])}({'▲' if r['change'] >= 0 else '▼'}{abs(r['change']):.1f}%)\n"
                st.code(txt, language="text")
                draw_chart(df_g, f"그래프 | 글로벌 Top 15 ({period_clean})", is_global=True)
            
            if show_major:
                st.subheader(f"📉 주요 시세 10 | {header_info}")
                df_m = fetch_data(['금','은','동','BTC','ETH','코스피','나스닥','S&P','달러','환율'], period_raw)
                
                # 텍스트 출력 [가독성 최적화 버전]
                txt = f"[{curr_t} {header_info}]\n"
                for i, r in df_m.iterrows():
                    txt += f"{i+1}.{r['name']}{hanmari_format(r['price'], r['name'])}({'▲' if r['change'] >= 0 else '▼'}{abs(r['change']):.1f}%)\n"
                st.code(txt, language="text")
                draw_chart(df_m, f"그래프 | 주요 시세 10 ({period_clean})", is_global=False)

if __name__ == '__main__':
    main()