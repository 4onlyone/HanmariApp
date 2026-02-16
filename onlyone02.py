import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import platform
from datetime import datetime, timedelta

# ==========================================
# 1. 스타일 설정 (맑은고딕/Arial/Bold)
# ==========================================
def set_style():
    system_name = platform.system()
    try:
        if system_name == 'Windows':
            f_name = 'Malgun Gothic'
        elif system_name == 'Darwin':
            f_name = 'AppleGothic'
        else:
            f_name = 'NanumGothic'
        plt.rcParams.update({'font.family': f_name, 'axes.unicode_minus': False, 'font.weight': 'bold', 'axes.labelweight': 'bold', 'axes.titleweight': 'bold'})
    except:
        plt.rcParams['font.family'] = 'sans-serif'

# 색상 가이드 (원자재 vs 암호화폐 확실한 구분)
COLOR_MAP = {
    '원자재': '#C29200', '암호화폐': '#FF5E00', 
    '한국증시': '#228B22', '미장': '#004A99', '기타': '#777777'
}

# ==========================================
# 2. 한마리 헌법 (숫자 포맷팅)
# ==========================================
def hanmari_format(value, name):
    dollar_list = ['금', '은', '동', 'BTC', 'ETH', '엔비디아', '애플', 'MS', '아마존', '구글', '테슬라', '브로드컴', '메타', '월마트', '일라이릴리', 'JP모건', 'TSMC']
    prefix = "$" if name in dollar_list else ""
    if value >= 100: return f"{prefix}{value:,.0f}"
    if value >= 10: return f"{prefix}{value:,.1f}"
    return f"{prefix}{value:,.2f}"

# ==========================================
# 3. [핵심 엔진] 날짜 및 가격 계산 로직
# ==========================================
def get_price_at_date(df, target_date):
    """특정 날짜(또는 그 직전 거래일)의 종가를 가져오는 Look-back 함수"""
    # target_date 이전 데이터 중 가장 최신 데이터 추출
    past_data = df[df.index <= target_date]
    if past_data.empty:
        return None
    return float(past_data['Close'].iloc[-1].item())

def fetch_data(target_list, period_option, status_option):
    t_map = {
        '금': 'GC=F', '은': 'SI=F', '동': 'HG=F', 'BTC': 'BTC-USD', 'ETH': 'ETH-USD',
        '코스피': '^KS11', '나스닥': '^IXIC', 'S&P': '^GSPC', '달러': 'DX-Y.NYB', '환율': 'KRW=X',
        '엔비디아': 'NVDA', '애플': 'AAPL', 'MS': 'MSFT', '아마존': 'AMZN', '구글': 'GOOG', 
        'TSMC': 'TSM', '브로드컴': 'AVGO', '테슬라': 'TSLA', '메타': 'META', '월마트': 'WMT', 
        '일라이릴리': 'LLY', 'JP모건': 'JPM'
    }
    
    res = []
    today = datetime.now().date()
    
    # 데이터 조회 범위 설정 (연간 데이터를 위해 넉넉히 2년치)
    download_period = "2y" if '연간' in period_option else "1y"

    for name in target_list:
        ticker = t_map.get(name)
        try:
            # 1. 데이터 다운로드 (일괄)
            df = yf.download(ticker, period=download_period, progress=False)
            if df.empty: continue
            df.index = df.index.date

            # 2. 현재 시점(Current) 날짜 결정
            # Live: 오늘(또는 마지막 데이터) / Completed: 어제(또는 마지막 전 데이터)
            last_available_date = df.index[-1]
            
            if '마감' in status_option:
                # 마감 모드: 오늘 날짜 데이터가 있다면 제외하고 그 전날을 '현재'로 봄
                if last_available_date == today:
                    curr_date = df.index[-2] # 어제
                else:
                    curr_date = last_available_date # 이미 어제 데이터임
            else:
                # 실시간 모드
                curr_date = last_available_date

            # 3. 기준 시점(Base) 날짜 결정
            if '일간' in period_option:
                # 일간: Current 바로 직전 거래일
                # (Live면 어제, Completed면 그제)
                base_date = df[df.index < curr_date].index[-1]
                
            elif '주간' in period_option:
                # 주간: 지난주 마지막 거래일 (일요일 or 금요일)
                # curr_date 기준 요일을 뺌 -> 이번주 시작일 -> 하루 더 뺌
                days_sub = curr_date.weekday() + 1
                base_date = curr_date - timedelta(days=days_sub)
                
            elif '월간' in period_option:
                # 월간: 지난달 말일
                first_day = curr_date.replace(day=1)
                base_date = first_day - timedelta(days=1)
                
            else: # 연간
                # 연간: 작년 12월 31일
                base_date = curr_date.replace(year=curr_date.year - 1, month=12, day=31)

            # 4. 가격 추출 (Look-back 적용)
            curr_price = get_price_at_date(df, curr_date)
            base_price = get_price_at_date(df, base_date)
            
            # 안전장치
            if base_price is None: base_price = curr_price
            
            change = ((curr_price - base_price) / base_price) * 100
            
            # 카테고리 분류
            if name in ['금','은','동']: cat = '원자재'
            elif name in ['BTC','ETH']: cat = '암호화폐'
            elif name == '코스피': cat = '한국증시'
            elif name in ['달러', '환율']: cat = '기타'
            else: cat = '미장'
            
            res.append({'name': name, 'price': curr_price, 'change': change, 'category': cat})
            
        except: continue
        
    return pd.DataFrame(res)

# ==========================================
# 4. 차트 그리기 (가로 정렬 + 글씨 크기 축소)
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

    # 수치 라벨 (Arial Bold, 막대 밖)
    for bar in bars:
        h = bar.get_height()
        va, offset = ('bottom', 5) if h >= 0 else ('top', -8)
        ax.annotate(f'{h:.1f}%', xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, offset), textcoords="offset points", ha='center', va=va, fontname='Arial', fontweight='bold', fontsize=9)

    ax.set_title(title, fontsize=14, fontweight='bold', pad=30)

    # 범례 설정 (논리적 구분)
    lp = [mpatches.Patch(color=COLOR_MAP['원자재'], label='원자재'), mpatches.Patch(color=COLOR_MAP['암호화폐'], label='암호화폐'), mpatches.Patch(color=COLOR_MAP['한국증시'], label='한국증시'), mpatches.Patch(color=COLOR_MAP['미장'], label='미장')]
    if is_global: lp.pop(2) # 글로벌 15에선 국장 제외
    ax.legend(handles=lp, loc='upper right', frameon=True, fontsize=8)
    
    # [수정] X축 라벨 가로 정렬 (겹침 방지 위해 폰트 8pt로 축소)
    plt.xticks(rotation=0, ha='center', fontsize=8, fontweight='bold')
    
    margin = max(abs(df['change'].max()), abs(df['change'].min())) * 0.5
    ax.set_ylim(df['change'].min() - margin, df['change'].max() + margin)
    for l in ax.get_yticklabels(): l.set_fontname('Arial')
    plt.tight_layout()
    st.pyplot(fig)

# ==========================================
# 5. 메인 실행부 (완벽한 통합)
# ==========================================
def main():
    st.set_page_config(page_title="한마리 비서", layout="wide")
    set_style()
    st.sidebar.header("🛠️ 분석 설정")
    
    status = st.sidebar.radio("1. 기준", ('실시간(Live)', '마감(Completed)'))
    period_raw = st.sidebar.selectbox("2. 기간", ('일간(Daily)', '주간(Weekly)', '월간(Monthly)', '연간(Yearly)'))
    
    show_g, show_m = st.sidebar.checkbox("글로벌 Top 15", value=True), st.sidebar.checkbox("주요 시세 10", value=True)
    
    # 괄호 가독성 최적화
    period_clean = period_raw.split('(')[0]
    header_info = f"{status} / {period_clean}"

    if st.button('🚀 분석 시작', use_container_width=True):
        with st.spinner('데이터 수집 중...'):
            curr_t = pd.Timestamp.now().strftime('%m/%d %H:%M')
            
            if show_g:
                st.subheader(f"🌍 글로벌 Top 15 | {header_info}")
                df_g = fetch_data(['금','엔비디아','은','애플','MS','아마존','구글','TSMC','브로드컴','테슬라','메타','BTC','월마트','일라이릴리','JP모건'], period_raw, status)
                
                txt = f"[{curr_t} {header_info}]\n"
                for i, r in df_g.iterrows():
                    txt += f"{i+1}.{r['name']}{hanmari_format(r['price'], r['name'])}({'▲' if r['change']>=0 else '▼'}{abs(r['change']):.1f}%)\n"
                st.code(txt, language="text")
                draw_chart(df_g, f"그래프 | 글로벌 Top 15 ({period_clean})", True)
            
            if show_m:
                st.subheader(f"📉 주요 시세 10 | {header_info}")
                df_m = fetch_data(['금','은','동','BTC','ETH','코스피','나스닥','S&P','달러','환율'], period_raw, status)
                
                txt = f"[{curr_t} {header_info}]\n"
                for i, r in df_m.iterrows():
                    txt += f"{i+1}.{r['name']}{hanmari_format(r['price'], r['name'])}({'▲' if r['change']>=0 else '▼'}{abs(r['change']):.1f}%)\n"
                st.code(txt, language="text")
                draw_chart(df_m, f"그래프 | 주요 시세 10 ({period_clean})", False)

if __name__ == '__main__':
    main()