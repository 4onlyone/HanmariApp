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
# 0. [실행력] 폰트 자동 설정 (에러 원천 차단)
# ==========================================
@st.cache_resource
def font_setting():
    """
    PC(윈도우/맥)에서는 시스템 폰트를,
    리눅스(스트림릿 클라우드)에서는 나눔고딕을 다운받아 사용합니다.
    '!apt-get' 같은 에러 유발 명령어는 절대 쓰지 않습니다.
    """
    system_name = platform.system()
    
    if system_name == 'Windows':
        # 윈도우: 맑은 고딕
        plt.rc('font', family='Malgun Gothic')
    elif system_name == 'Darwin':
        # 맥: 애플고딕
        plt.rc('font', family='AppleGothic')
    else:
        # 리눅스/웹: 나눔고딕 다운로드 및 적용
        font_path = "NanumGothic.ttf"
        if not os.path.exists(font_path):
            url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
            try:
                response = requests.get(url)
                with open(font_path, "wb") as f:
                    f.write(response.content)
            except:
                pass # 다운로드 실패 시 기본 폰트 사용

        if os.path.exists(font_path):
            fm.fontManager.addfont(font_path)
            plt.rc('font', family='NanumGothic')
        else:
            plt.rc('font', family='sans-serif') # 최후의 수단

    # 공통 설정: 마이너스 기호 깨짐 방지 및 볼드체
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['font.weight'] = 'bold'
    plt.rcParams['axes.labelweight'] = 'bold'
    plt.rcParams['axes.titleweight'] = 'bold'

# 폰트 설정 즉시 실행
font_setting()

# ==========================================
# 1. 색상 및 스타일 (베스트 디자인)
# ==========================================
COLOR_MAP = {
    '원자재': '#C29200',   # 짙은 황동색
    '암호화폐': '#FF5E00', # 선명한 주황색
    '한국증시': '#228B22', # 포레스트 그린
    '미장': '#004A99',     # 다크 블루
    '기타': '#777777'      # 회색
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
# 3. 데이터 엔진 (집요한 탐색 & 마감 로직)
# ==========================================
def get_historical_price(ticker, days_ago):
    """휴장일을 피해 과거 데이터를 집요하게 찾아내는 함수"""
    target_date = (datetime.now() - timedelta(days=days_ago)).date()
    # 넉넉하게 20일 전부터 스캔
    start_date = target_date - timedelta(days=20)
    end_date = target_date + timedelta(days=1)
    
    try:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if df.empty: return None
        df.index = df.index.date
        # 목표일 이하 중 가장 최신 데이터 (Look-back)
        past_data = df[df.index <= target_date]
        return float(past_data['Close'].iloc[-1].item()) if not past_data.empty else None
    except:
        return None

def fetch_data(target_list, period_option, status_option):
    """마감(Completed)과 실시간(Live)을 구분하여 데이터를 가져오는 핵심 엔진"""
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
            # 최근 데이터 호출
            recent = yf.download(ticker, period="1mo", progress=False)
            if recent.empty: continue
            
            # [마감 로직] 오늘 날짜 데이터 배제 여부 결정
            last_date = recent.index[-1].date()
            today_date = datetime.now().date()
            
            if '마감' in status_option:
                # 마감 모드인데 마지막 데이터가 오늘 것이라면 -> 아직 마감 안 된 거니까 버리고 '어제' 거 사용
                if last_date == today_date:
                    if len(recent) < 2: continue
                    curr = float(recent['Close'].iloc[-2].item())
                    curr_date = recent.index[-2].date()
                else:
                    curr = float(recent['Close'].iloc[-1].item())
                    curr_date = last_date
            else:
                # 실시간 모드: 무조건 최신 데이터
                curr = float(recent['Close'].iloc[-1].item())
                curr_date = last_date

            # [기준가 계산]
            if '일간' in period_option:
                # 일간 변동: curr_date보다 하루 전 데이터 찾기
                past_data = recent[recent.index.date < curr_date]
                if not past_data.empty:
                    base = float(past_data['Close'].iloc[-1].item())
                else:
                    base = curr # 비교 불가 시 변동 0
            else:
                # 기간 변동: N일 전 데이터 Look-back
                # 마감 모드면 기준일도 그만큼 뒤로 밀어서 계산
                target_date_override = curr_date - timedelta(days=days)
                
                # get_historical_price 함수를 직접 쓰지 않고 여기서 로직 구현 (일관성 위해)
                # (아까 별도 함수로 뺐지만, 여기서 직접 처리하는 게 날짜 정합성에 더 유리할 수 있음)
                # 하지만 코드 재사용을 위해 get_historical_price 활용하되 날짜만 정확히 전달
                
                # 여기서는 날짜 계산이 복잡하므로, 
                # get_historical_price 함수를 'days_ago' 대신 'specific_date'를 받도록 수정하거나
                # 단순히 days를 넘기되, curr_date 기준임을 감안해야 함.
                # 편의상 기존 함수(오늘 기준 days_ago)를 사용하되, 
                # 마감 모드일 경우 days에 +1일 정도 보정을 하거나, 
                # 별도 로직을 짜는 게 맞음. 
                
                # [수정된 로직] 정확성을 위해 직접 쿼리
                search_date = curr_date - timedelta(days=days)
                # search_date 이하 중 최신값 찾기
                mask = recent.index.date <= search_date
                filtered = recent[mask]
                
                if not filtered.empty:
                    base = float(filtered['Close'].iloc[-1].item())
                else:
                    # recent에 없으면 더 과거 데이터 쿼리
                    base = get_historical_price(ticker, days + (1 if '마감' in status_option else 0))

            base = base if base else curr
            change = ((curr - base) / base) * 100
            
            # 카테고리 분류
            if name in ['금','은','동']: cat = '원자재'
            elif name in ['BTC','ETH']: cat = '암호화폐'
            elif name == '코스피': cat = '한국증시'
            elif name in ['달러', '환율']: cat = '기타'
            else: cat = '미장'
            
            res.append({'name': name, 'price': curr, 'change': change, 'category': cat})
        except: continue
    return pd.DataFrame(res)

# ==========================================
# 4. 차트 그리기 (디자인 완전 복구)
# ==========================================
def draw_chart(df, title, is_global=False):
    if df.empty: return
    # 그래프 크기 및 폰트 설정
    fig, ax = plt.subplots(figsize=(8.5, 4.5)) 
    
    colors = [COLOR_MAP.get(c, '#777777') for c in df['category']]
    bars = ax.bar(df['name'], df['change'], color=colors)
    ax.axhline(0, color='black', linewidth=1.0)

    # [디자인] 외곽 박스 (연한 회색, 세련된 두께)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.8)
        spine.set_color('#CCCCCC') 

    # [디자인] 수치 라벨 (Arial Bold)
    for bar in bars:
        h = bar.get_height()
        va, offset = ('bottom', 5) if h >= 0 else ('top', -8)
        ax.annotate(f'{h:.1f}%', xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, offset),
                    textcoords="offset points", ha='center', va=va, fontname='Arial', fontweight='bold', fontsize=9)

    # [디자인] 제목 및 간격
    ax.set_title(title, fontsize=14, fontweight='bold', pad=30)

    # [디자인] 범례 (논리적 구분)
    lp = [mpatches.Patch(color=COLOR_MAP['원자재'], label='원자재'), 
          mpatches.Patch(color=COLOR_MAP['암호화폐'], label='암호화폐'), 
          mpatches.Patch(color=COLOR_MAP['한국증시'], label='한국증시'), 
          mpatches.Patch(color=COLOR_MAP['미장'], label='미장')]
    
    if is_global: lp.pop(2) # 글로벌 15에선 한국증시 제외
    ax.legend(handles=lp, loc='upper right', frameon=True, fontsize=8)
    
    # [디자인] X축 라벨 회전 (겹침 방지)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    
    # Y축 여백
    margin = max(abs(df['change'].max()), abs(df['change'].min())) * 0.5
    ax.set_ylim(df['change'].min() - margin, df['change'].max() + margin)
    
    # Y축 폰트 (Arial)
    for l in ax.get_yticklabels(): l.set_fontname('Arial')
    
    plt.tight_layout()
    st.pyplot(fig)

# ==========================================
# 5. 메인 실행부 (모든 기능 통합)
# ==========================================
def main():
    st.set_page_config(page_title="한마리 비서", layout="wide")
    
    # 사이드바 설정
    st.sidebar.header("🛠️ 분석 설정")
    status = st.sidebar.radio("1. 기준", ('실시간(Live)', '마감(Completed)'))
    period_raw = st.sidebar.selectbox("2. 기간", ('일간(Daily)', '주간(Weekly)', '월간(Monthly)', '연간(Yearly)'))
    
    # 체크박스 (에러 없이 변수명 통일)
    show_g = st.sidebar.checkbox("글로벌 Top 15", value=True)
    show_m = st.sidebar.checkbox("주요 시세 10", value=True)
    
    # 괄호 가독성 최적화
    period_clean = period_raw.split('(')[0]
    header_info = f"{status} / {period_clean}"

    st.title("📊 한마리 주식 비서")

    if st.button('🚀 분석 시작', use_container_width=True):
        with st.spinner('데이터 수집 및 분석 중...'):
            curr_t = pd.Timestamp.now().strftime('%m/%d %H:%M')
            
            # 1. 글로벌 Top 15 분석
            if show_g:
                st.subheader(f"🌍 글로벌 Top 15 | {header_info}")
                df_g = fetch_data(['금','엔비디아','은','애플','MS','아마존','구글','TSMC','브로드컴','테슬라','메타','BTC','월마트','일라이릴리','JP모건'], period_raw, status)
                
                # 텍스트 출력 (괄호 중복 제거)
                txt = f"[{curr_t} {header_info}]\n"
                for i, r in df_g.iterrows():
                    txt += f"{i+1}.{r['name']}{hanmari_format(r['price'], r['name'])}({'▲' if r['change']>=0 else '▼'}{abs(r['change']):.1f}%)\n"
                st.code(txt, language="text")
                
                # 차트 출력
                draw_chart(df_g, f"그래프 | 글로벌 Top 15 ({period_clean})", is_global=True)
            
            # 2. 주요 시세 10 분석
            if show_m:
                st.subheader(f"📉 주요 시세 10 | {header_info}")
                df_m = fetch_data(['금','은','동','BTC','ETH','코스피','나스닥','S&P','달러','환율'], period_raw, status)
                
                # 텍스트 출력
                txt = f"[{curr_t} {header_info}]\n"
                for i, r in df_m.iterrows():
                    txt += f"{i+1}.{r['name']}{hanmari_format(r['price'], r['name'])}({'▲' if r['change']>=0 else '▼'}{abs(r['change']):.1f}%)\n"
                st.code(txt, language="text")
                
                # 차트 출력
                draw_chart(df_m, f"그래프 | 주요 시세 10 ({period_clean})", is_global=False)

if __name__ == '__main__':
    main()