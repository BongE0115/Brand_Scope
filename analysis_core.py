import os
import pandas as pd
import json
import re
import requests 
from datetime import datetime, timedelta
from collections import Counter 
import gc 
import matplotlib.pyplot as plt 
from matplotlib import font_manager, rc
import matplotlib
import requests.utils
import threading
import time
import markdown
import uuid  # 👈 [핵심] 사용자 간 파일 덮어쓰기 방지
from dotenv import load_dotenv
load_dotenv()

# Flask 연동 및 데이터 처리를 위해 필수적인 라이브러리
import io 
import numpy as np 
import shutil # 👈 캐시 삭제용

# 태그 클라우드 & 시각화 라이브러리
from wordcloud import WordCloud 
import seaborn as sns

# ==================================================================
# [1] 폰트 캐시 삭제 및 강제 설정
# ==================================================================
def set_custom_font():
    try:
        cache_dir = matplotlib.get_cachedir()
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
    except Exception:
        pass

    current_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(current_dir, 'static', 'NanumGothic.ttf')
    global FONT_PATH 

    if os.path.exists(font_path):
        try:
            font_manager.fontManager.addfont(font_path)
            font_prop = font_manager.FontProperties(fname=font_path)
            font_name = font_prop.get_name()
            plt.rcParams['font.family'] = font_name
            rc('font', family=font_name)
            FONT_PATH = font_path
        except Exception as e:
            print(f"-> [에러] 폰트 설정 실패: {e}")
            FONT_PATH = None
    else:
        FONT_PATH = None

set_custom_font()
plt.rcParams['axes.unicode_minus'] = False

# ==================================================================
# [2] 시각화 저장 함수 (파일명 중복 방지 & 캐시 방지)
# ==================================================================
def save_and_get_url(plot_func, filename, static_folder, unique_id): # 👈 unique_id 추가
    """ Matplotlib 그래프를 파일로 저장하고 URL을 반환합니다. """
    if not static_folder:
        return None

    try:
        img_save_path = os.path.join(static_folder, 'img')
        if not os.path.exists(img_save_path):
            os.makedirs(img_save_path)

        plot_object = plot_func()
        if plot_object is None: return None

        # 파일명 앞에 고유 ID를 붙여서 겹치지 않게 함
        final_filename = f"{unique_id}_{filename}"
        filepath = os.path.join(img_save_path, final_filename)

        if os.path.exists(filepath):
            os.remove(filepath)

        plot_object.savefig(filepath, dpi=100)
        plt.close('all')
        
        # URL 뒤에 타임스탬프를 붙여 브라우저 캐시 방지
        timestamp = int(time.time())
        return f"/static/img/{final_filename}?v={timestamp}"

    except Exception as e:
        print(f"-> ❌ 시각화 저장 오류 ({filename}): {e}")
        plt.close('all')
        return None

# ----------------------------------------------------
# --- 설정 (Configuration) ---
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
MAX_RESULTS_PER_API = 1000 

# --- 감성 사전 (기존 유지) ---
POSITIVE_WORDS = [
    '좋아요', '최고', '만족', '추천', '강력추천', '대박', '예쁘', '예쁘다', '편안', '편안함',
    '행복', '감사', '기쁨', '훌륭', '사랑', '재미', '즐거움', '성공', '합격', '선물',
    '따뜻', '밝은', '완벽', '인생템', '가성비', '착한', '놀랍', '기대', '보람', '깨끗',
    '싱그럽', '프리미엄', '친절', '신뢰', '편리', '안정성', '풍부', '효율적', '세련', '프렌들리',
    '믿음', '가치', '만족감', '추천합니다', '짱', '최고예요', '좋네요', '감동', '재구매', '재구매의사',
    '만족스러움', '고급', '퀄리티', '뛰어남', '만족스럽다', '훌륭해요', '믿을만', '편안해요', '사랑스러', '사랑스러움',
    '편리함', '안정적', '풍성', '만족도', '효율성', '인기', '유용', '실용적', '강추', '강추합니다',
    '추천해요', '감사해요', '기뻐요', '만족했다', '좋습니다', '최고임', '편안함이', '친절해요', '가성비좋', '경제적',
    '만족도가', '만족했던', '깔끔', '깔끔함', '신속', '신속함', '정확', '정확함', '편안한', '포근',
    '달콤', '시원', '풍미', '활력', '안정감', '만족스러운', '놀랍다', '기대이상', '추천받음', '기대만큼'
]

NEGATIVE_WORDS = [
    '별로', '실망', '아쉬움', '나쁘', '불만', '불편', '최악', '힘들', '걱정', '문제',
    '어려움', '부족', '실패', '낭비', '쓰레기', '비싸', '떨어짐', '실망스럽', '지루', '후회',
    '이상', '오류', '짜증', '고통', '논란', '부정적', '약점', '결함', '복잡', '불필요',
    '무성의', '불친절', '지저분', '과대광고', '오래걸림', '허접', '번거로움', '부정확', '비추천', '불신',
    '불만족', '불만족스러움', '불쾌', '불만족하다', '불만족스럽다', '불안정', '질낮', '저급', '형편없', '엉망',
    '망함', '실패작', '불편함', '성가심', '번거로워요', '못함', '부실', '불량', '손해', '불친절함',
    '비추', '비추합니다', '무책임', '취약', '반품', '환불', '불만족했다', '부작용', '문제있', '불편했다',
    '짜증나요', '사용불가', '먹먹', '불편한', '못쓰겠다', '고장', '터무니없', '불만족감', '불편함이', '불쾌감',
    '불합리', '악화', '악성', '부정', '부적절', '실망스러웠다', '실망했다', '후회한다', '실망해요', '최악이다',
    '최악이에요', '형편없다', '엉망진창', '엉성', '값비싼', '불친절했어요', '불편했습니다', '부정확함', '부주의', '문제가있다'
]

# --- 유틸리티 함수들 (검증, 수집, 분석) ---
def is_valid_query(query):
    """ 
    검색어 유효성 검사:
    1. 공백 제외 2글자 미만 차단
    2. 의미 없는 자음/모음만 있는 경우 차단 (예: ㅇㅇ, ㅋㅋ)
    3. 동일 문자 무한 반복 차단
    """
    clean_query = query.replace(' ', '')
    
    # 1. 길이 체크
    if len(clean_query) < 2:
        print(f"-> ❌ 검색어 '{query}' 차단: 길이가 너무 짧습니다.")
        return False

    # 2. [추가된 로직] 자음/모음만으로 구성된 경우 차단 (ㄱ-ㅎ, ㅏ-ㅣ)
    # 정규식: 한글 자음/모음 범위에만 해당하는지 체크
    if re.fullmatch(r'[ㄱ-ㅎㅏ-ㅣ]+', clean_query):
        print(f"-> ❌ 검색어 '{query}' 차단: 자음/모음만으로 구성되었습니다.")
        return False
        
    # 3. 동일 문자 3회 이상 반복 체크 (aaa, 111 등)
    # (단, 브랜드명일 수도 있으므로 한글은 제외하거나 기준을 완화할 수 있음)
    repeated_pattern = re.compile(r'([^가-힣])\1{2,}') 
    if repeated_pattern.search(clean_query):
        print(f"-> ❌ 검색어 '{query}' 차단: 무의미한 문자 반복.")
        return False
        
    return True

def load_brand_whitelist():
    """ static/brands.txt 파일에서 브랜드 목록을 읽어옵니다. """
    whitelist = set() # 검색 속도가 빠른 set 자료구조 사용
    
    # 1. 파일 경로 찾기
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'static', 'brands.txt')
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    brand = line.strip()
                    if brand:
                        # 소문자로 변환하고 공백 제거해서 저장 (비교 용이성)
                        whitelist.add(brand.replace(" ", "").lower())
            print(f"-> [화이트리스트] {len(whitelist)}개의 브랜드를 로드했습니다.")
        except Exception as e:
            print(f"-> [경고] 브랜드 파일 로드 실패: {e}")
    else:
        print("-> [경고] brands.txt 파일이 없습니다. 화이트리스트 기능이 제한됩니다.")
        # 비상용 기본 리스트
        basic_brands = ['삼성', '애플', '나이키', '다이소', '쿠팡', '카카오', '네이버']
        for b in basic_brands:
            whitelist.add(b)
            
    return whitelist

BRAND_WHITELIST = load_brand_whitelist()

def is_brand_name(query, client_id, client_secret, confidence_threshold=0.15):
    """ 
    네이버 쇼핑 API를 통해 검색어가 브랜드명인지 검증 
    """
    query_norm = query.replace(" ", "").lower()

    # 1. 화이트리스트 체크
    if query_norm in BRAND_WHITELIST:
        print(f"-> [Pass] '{query}'는 화이트리스트 브랜드입니다.")
        return True

    # 2. API 검증
    print(f"\n--- 0단계: '{query}' 브랜드 검증 (API) ---")
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    # 정확도순(sim)으로 검색해서 연관성을 높임
    params = {"query": query, "display": 40, "sort": "sim"}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        items = response.json().get("items", [])

        if not items:
            print("-> ❌ 쇼핑 검색 결과가 없습니다.")
            return False

        brand_list = []
        match_count = 0

        for item in items:
            brand = item.get("brand", "").strip()
            # 브랜드 정보가 없으면 무시
            if not brand: continue
            
            brand_list.append(brand)
            brand_norm = brand.replace(" ", "").lower()

            # 포함 관계 확인
            if query_norm in brand_norm or brand_norm in query_norm:
                match_count += 1

        total_brands_found = len(brand_list)
        
        #  검색 결과는 있는데 '브랜드' 필드가 있는 상품이 하나도 없는 경우 (예: 중고장터 글 등)
        if total_brands_found == 0:
            print(f"-> ❌ 검색 결과는 있으나 등록된 브랜드 정보가 없습니다. (일반 명사일 가능성 높음)")
            return False

        ratio = match_count / total_brands_found
        print(f"-> 검증 결과: 유효 상품 {total_brands_found}개 중 {match_count}개 일치 ({ratio:.1%})")

        if ratio >= confidence_threshold:
            return True
        else:
            # 최빈값 구제 로직
            if brand_list:
                most_common = Counter(brand_list).most_common(1)[0][0]
                if query_norm in most_common.replace(" ", "").lower():
                    print(f"-> ⚠️ 비율 미달이나 최빈 브랜드('{most_common}')와 일치하여 통과.")
                    return True
            
            print(f"-> ❌ 브랜드 검증 실패 (기준 미달)")
            return False

    except Exception as e:
        print(f"브랜드 검증 API 오류: {e}")
        # API 오류 시에는 억울하게 막히는 걸 방지하기 위해 일단 통과시키거나, 
        # 엄격하게 하려면 False를 리턴합니다. (여기선 안전하게 True 유지)
        return True

def fetch_naver_search_results(query, api_type, client_id, client_secret, total_results):
    if api_type == 'blog': url = "https://openapi.naver.com/v1/search/blog.json"
    elif api_type == 'news': url = "https://openapi.naver.com/v1/search/news.json"
    else: return pd.DataFrame()

    df = pd.DataFrame(columns=['title', 'link', 'description', 'channel_name', 'postdate', 'channel_type'])
    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    remove_tag = re.compile('<.*?>')
    
    for start in range(1, min(total_results, 1001) + 1, 100):
        try:
            res = requests.get(url, headers=headers, params={"query": query, "display": 100, "start": start})
            res.raise_for_status()
            items = res.json().get("items", [])
            if not items: break
            
            processed = []
            for item in items:
                clean = {
                    'title': re.sub(remove_tag, '', item.get('title', '')),
                    'description': re.sub(remove_tag, '', item.get('description', '')),
                    'link': item.get('link', ''),
                    'channel_type': api_type
                }
                if api_type == 'blog':
                    clean['channel_name'] = re.sub(remove_tag, '', item.get('bloggername', ''))
                    clean['postdate'] = pd.to_datetime(item.get('postdate', ''), format='%Y%m%d', errors='coerce')
                else:
                    clean['channel_name'] = item.get('publisher', '')
                    clean['postdate'] = pd.to_datetime(item.get('pubDate', ''), format='%a, %d %b %Y %H:%M:%S +0900', errors='coerce')
                processed.append(clean)
            
            df = pd.concat([df, pd.DataFrame(processed)], ignore_index=True)
        except: break
        
    df['postdate'] = df['postdate'].dt.normalize()
    return df.dropna(subset=['postdate']).drop_duplicates()

def get_search_trend(query, client_id, client_secret):
    url = "https://openapi.naver.com/v1/datalab/search"
    headers = {
        "X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json"
    }
    body = json.dumps({
        "startDate": (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
        "endDate": datetime.now().strftime('%Y-%m-%d'),
        "timeUnit": "month",
        "keywordGroups": [{"groupName": query, "keywords": [query]}]
    })
    try:
        res = requests.post(url, headers=headers, data=body)
        res.raise_for_status()
        data = res.json()
        if not data.get('results'): return pd.DataFrame(columns=['date', 'ratio'])
        df = pd.DataFrame(data['results'][0]['data']).rename(columns={'period': 'date'})
        df['date'] = pd.to_datetime(df['date'])
        return df
    except: return pd.DataFrame(columns=['date', 'ratio'])

# --- 시각화 함수들 ---
def visualize_post_frequency(df, frequency_type='monthly'):
    """ 
    최대 기간(12개월/6개월)으로 그래프 X축을 고정하고, 
    데이터가 없는 기간은 0으로 채워서 보여줍니다.
    """
    time_unit = "월별" if frequency_type == 'monthly' else "주별"
    color = 'darkorange' if frequency_type == 'monthly' else 'purple'
    
    print(f"\n--- 3단계 분석: {time_unit} 언급량 시각화 (기간 고정) ---")
    
    temp_df = df.copy()
    try:
        temp_df['postdate'] = pd.to_datetime(temp_df['postdate'], errors='coerce').dt.normalize()
        temp_df.dropna(subset=['postdate'], inplace=True)
    except Exception:
        return None 
    
    if temp_df.empty: return None

    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 1. [기간 설정] 데이터 유무와 상관없이 12개월/6개월 전부터 시작
    if frequency_type == 'monthly':
        start_date = now - pd.DateOffset(months=12)
        freq_code = 'MS'
    else:
        start_date = now - pd.DateOffset(months=6)
        freq_code = 'W'

    # 2. [필터링] 해당 기간 내 데이터만 추출
    df_filtered = temp_df[(temp_df['postdate'] >= start_date) & (temp_df['postdate'] <= now)].copy()
    
    # 3. [전체 범위 생성] 빈 기간을 채우기 위한 날짜 인덱스
    full_date_range = pd.date_range(start=start_date, end=now, freq=freq_code)
    
    if frequency_type == 'monthly':
        # 월별 집계
        df_filtered['period_dt'] = df_filtered['postdate'].dt.to_period('M').dt.to_timestamp()
        counts_raw = df_filtered['period_dt'].value_counts().sort_index()
        
        # 빈 곳 0으로 채우기
        full_counts = counts_raw.reindex(full_date_range, fill_value=0)
        
        # 라벨: YYYY-MM
        full_counts.index = full_counts.index.strftime('%Y-%m')
        rotation_angle = 45

    elif frequency_type == 'weekly':
        # 주별 집계
        df_resample = df_filtered.set_index('postdate')
        counts_resampled = df_resample.resample('W').size()
        
        # 빈 곳 0으로 채우기
        full_counts = counts_resampled.reindex(full_date_range, fill_value=0)
        
        # 라벨: 0000년 0월 0주차
        new_labels = []
        for date in full_counts.index:
            first_day = date.replace(day=1)
            dom = date.day
            adjusted_dom = dom + first_day.weekday()
            w = int(np.ceil(adjusted_dom/7.0))
            if w > 5: w = 5
            new_labels.append(f"{date.year}년 {date.month}월 {w}주차")
            
        full_counts.index = new_labels
        rotation_angle = 45
        
    else:
        return None

    if full_counts.empty: return None

    # 그래프 그리기
    fig = plt.figure(figsize=(15 if frequency_type == 'weekly' else 12, 6))
    sns.lineplot(x=full_counts.index, y=full_counts.values, marker='o', color=color)
    
    # 제목 설정
    period_msg = "최근 12개월" if frequency_type == 'monthly' else "최근 6개월"
    plt.title(f'{period_msg} 언급량 추이 ({time_unit})', fontsize=16)
    
    if frequency_type == 'weekly':
        plt.xlabel(f'언급 {time_unit} (주차)', fontsize=12) 
    else:
        plt.xlabel(f'언급 {time_unit}', fontsize=12) 
        
    plt.ylabel('총 언급량', fontsize=12)

    plt.xticks(full_counts.index, rotation=rotation_angle) 
    plt.grid(axis='y', linestyle='--')
    plt.tight_layout()
    
    print(f"-> 통합 데이터 {time_unit} 언급량 시각화 플롯 객체 생성 완료.")
    return fig

def visualize_combined_trend(total_df, trend_df):
    if trend_df.empty: return None
    temp = total_df.copy()
    temp['month'] = temp['postdate'].dt.to_period('M').dt.to_timestamp()
    mention_counts = temp['month'].value_counts().reset_index()
    mention_counts.columns = ['date', 'mention_count']
    
    trend_df['date'] = trend_df['date'].dt.to_period('M').dt.to_timestamp()
    combined = pd.merge(trend_df, mention_counts, on='date', how='left').fillna(0)
    if combined.empty: return None
    combined['mention_ratio'] = (combined['mention_count'] / combined['mention_count'].max() * 100) if combined['mention_count'].max() > 0 else 0

    fig, ax1 = plt.subplots(figsize=(12, 6))
    sns.lineplot(x=combined.index, y=combined['ratio'], ax=ax1, color='tab:red', marker='o', label='검색량')
    ax2 = ax1.twinx()
    sns.lineplot(x=combined.index, y=combined['mention_ratio'], ax=ax2, color='tab:blue', marker='s', label='언급량')
    plt.title('검색량 vs 언급량 교차 분석', fontsize=16)
    ax1.set_xticks(range(len(combined)))
    ax1.set_xticklabels(combined['date'].dt.strftime('%Y-%m'), rotation=45)
    fig.tight_layout()
    return fig

def visualize_sentiment_word_clouds(df, pos_words, neg_words):
    if df.empty: return None, None, None, pd.DataFrame()
    text = ' '.join(df['description'].astype(str).tolist())
    cleaned = re.sub('[^가-힣\s]', '', text).lower()
    
    def make_wc(words, title, cmap):
        counts = {w: len(re.findall(rf'\b{w}\b', cleaned)) for w in words}
        counts = {k: v for k, v in counts.items() if v > 0}
        if not counts: return None
        wc = WordCloud(font_path=FONT_PATH, width=800, height=400, background_color='white', colormap=cmap)
        wc.generate_from_frequencies(counts)
        fig = plt.figure(figsize=(12, 7))
        plt.imshow(wc, interpolation='bilinear')
        plt.axis('off')
        plt.title(title, fontsize=16)
        plt.tight_layout()
        return fig

    pos_fig = make_wc(pos_words, '긍정 키워드', 'YlGn')
    neg_fig = make_wc(neg_words, '부정 키워드', 'Reds_r')
    
    # 통합 키워드 및 상위 리스트
    all_counts = {w: len(re.findall(rf'\b{w}\b', cleaned)) for w in pos_words + neg_words}
    all_counts = dict(sorted(all_counts.items(), key=lambda x: x[1], reverse=True)[:20])
    all_fig = make_wc(list(all_counts.keys()), '통합 키워드', 'plasma')
    
    top_k = pd.DataFrame(all_counts.items(), columns=['키워드', '언급 횟수']) if all_counts else pd.DataFrame()
    return pos_fig, neg_fig, all_fig, top_k

def visualize_competitor_mention_comparison(own_query, own_df, competitor_query, competitor_df):
    """ 
    자사 vs 경쟁사 월별 언급량을 비교합니다.
    (최근 12개월 고정, 빈 달은 0으로 채움, 날짜 오름차순 정렬 보장)
    """
    print(f"\n--- 9단계 분석: 자사({own_query}) vs 경쟁사({competitor_query}) 월별 언급량 비교 ---")

    # 둘 다 데이터가 없으면 그릴 수 없음
    if own_df.empty and competitor_df.empty:
        print("경고: 비교할 데이터가 없어 건너뜁니다.")
        return None

    # 1. 기준 기간 설정 (최근 12개월)
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = now - pd.DateOffset(months=12)
    
    # 2. 완전한 날짜 인덱스 생성 (이게 있어야 순서가 안 섞이고 0으로 채워짐)
    full_date_range = pd.date_range(start=start_date, end=now, freq='MS')

    # 내부 집계 함수
    def get_monthly_counts(df):
        temp_df = df.copy()
        if temp_df.empty: 
            return pd.Series(0, index=full_date_range) # 데이터 없으면 0으로 꽉 채운 시리즈 반환
        
        try:
            temp_df['postdate'] = pd.to_datetime(temp_df['postdate'], errors='coerce').dt.normalize()
            temp_df.dropna(subset=['postdate'], inplace=True)
            
            # 기간 내 데이터 필터링
            mask = (temp_df['postdate'] >= start_date) & (temp_df['postdate'] <= now)
            filtered = temp_df[mask]
            
            # 월별 리샘플링 (MS: Month Start)
            # set_index -> resample -> size 과정을 거치면 날짜순으로 자동 정렬됨
            counts = filtered.set_index('postdate').resample('MS').size()
            
            # 빈 달을 0으로 채우기 (Reindex)
            return counts.reindex(full_date_range, fill_value=0)
            
        except Exception as e:
            print(f"데이터 집계 중 오류: {e}")
            return pd.Series(0, index=full_date_range)

    # 3. 자사/경쟁사 데이터 집계
    own_counts = get_monthly_counts(own_df)
    comp_counts = get_monthly_counts(competitor_df)
    
    # 4. 데이터프레임 통합
    combined = pd.DataFrame({
        own_query: own_counts,
        competitor_query: comp_counts
    })
    
    # 5. 그래프 그리기 (Figure 객체 생성)
    fig = plt.figure(figsize=(10, 5))
    
    # X축 라벨을 보기 좋게 변환 (YYYY-MM)
    x_labels = combined.index.strftime('%Y-%m')

    # 라인 그래프 그리기
    sns.lineplot(data=combined, markers=True, dashes=False)

    plt.title(f'{own_query} vs {competitor_query} 월별 언급량 비교 (최근 12개월)', fontsize=14) 
    plt.xlabel('월', fontsize=11) 
    plt.ylabel('총 언급량', fontsize=11)
    
    # X축 설정 (정렬된 날짜 인덱스 사용)
    plt.xticks(ticks=combined.index, labels=x_labels, rotation=45) 
    
    plt.legend(fontsize=11)
    plt.grid(axis='y', linestyle='--')
    plt.tight_layout()
    
    print("-> 자사/경쟁사 언급량 비교 시각화 플롯 객체 생성 완료.")
    return fig

# --- AI 리포트 생성 ---
def generate_smart_report(query, total, sent_label, pos_score, keywords, outbreak, trend_ok, freq_date, change_rate, api_key):
    key_str = ", ".join([k['키워드'] for k in keywords[:5]]) if keywords else "없음"
    outbreak_text = f"{outbreak[0]}" if outbreak else "없음"
    
    prompt = f"""
        당신은 '검색량(관심도)'과 '언급량(버즈량)'의 상관관계를 분석하는 브랜드 평판 전문가입니다.
        제공된 데이터를 바탕으로 '{query}' 브랜드의 현황을 진단하고, 논리적인 마케팅 솔루션을 제시하세요.

        📊 [데이터 개요]
        - 총 언급량(Buzz): {total}건 (시장의 반응 크기)
        - 언급량 증감률: {change_rate} (최근 추세)
        - 최다 언급일: {freq_date}
        - 이슈 확산 포인트: {outbreak_text} (검색량 급증 시점)
        - 여론 감성: {sent_label} (긍정 {pos_score}%)
        - 핵심 키워드: {key_str}

        📝 [작성 가이드 (500자 내외, 개조식)]
        아래 4가지 목차에 맞춰 분석하되, 단순 수치 나열이 아닌 '인사이트' 위주로 작성하세요.

        1. 🔍 [관심도-확산성 교차 분석]
        - '이슈 확산(검색량 급증)'과 '총 언급량'의 관계를 분석하여 현재 단계를 정의하세요.
        - (예: 검색량이 선행하고 언급량이 따라오는 '상승기'인지, 검색 없이 언급만 많은 '바이럴 단계'인지 진단)

        2. 🗣️ [여론의 질적 진단]
        - 긍정 여론({pos_score}%)의 구체적인 성격을 키워드와 연관 지어 해석하세요.
        - 단순한 호감인지, 구매로 이어지는 신뢰인지, 혹은 부정적 이슈 방어인지 분석하세요.

        3. 🔑 [트렌드 맥락(Context)]
        - 도출된 키워드({key_str})들이 왜 이 시점에 등장했는지, 소비자의 어떤 니즈(Needs)를 반영하는지 설명하세요.

        4. 💡 [Actionable Strategy]
        - 위 분석을 종합하여 구체적인 행동 전략을 한 문장으로 제안하세요.
        - (High Search/Low Mention일 경우 -> "정보성 콘텐츠 보강으로 구매 전환 유도")
        - (Low Search/High Mention일 경우 -> "이벤트성 거품 주의 및 브랜드 진정성 강화")
        """
    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={api_key}"
            res = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps({"contents": [{"parts": [{"text": prompt}]}]}))
            if res.status_code == 200: return markdown.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
        except: pass
    return markdown.markdown(f"### 분석 요약\n- 총 언급량: {total}건\n- 감성: {sent_label}\n- 주요 키워드: {key_str}")

# --- 헬퍼 함수들 ---
def get_month_week(date_obj):
    """ 
    날짜(date_obj)를 받아서 해당 월의 몇 번째 주인지 계산합니다.
    (최대 5주차까지만 나오도록 보정)
    """
    # 매월 1일 찾기
    first_day = date_obj.replace(day=1)
    
    # 날짜(일) + 1일의 요일 인덱스(월=0, 일=6)를 더해서 주차 계산
    dom = date_obj.day
    adjusted_dom = dom + first_day.weekday()
    
    # 올림 처리하여 주차 계산
    week_num = int(np.ceil(adjusted_dom/7.0))
    
    # 6주차가 나오면 5주차로 강제 편입
    if week_num > 5: 
        return 5
    return week_num

def find_outbreak_weeks(trend_df, change_threshold=0.3):
    if trend_df.empty: return []
    
    filtered = trend_df.sort_values('date')
    
    # 에러 방지: 문자열을 숫자로 변환
    filtered['ratio'] = pd.to_numeric(filtered['ratio'], errors='coerce')
    
    # 변화율(pct_change) 계산
    filtered['change'] = filtered['ratio'].pct_change()
    
    # 급증한 구간(threshold 초과) 찾기
    outbreak = filtered[filtered['change'] > change_threshold]
    
    results = []
    for _, row in outbreak.iterrows():
        m = row['date'].month
        w = get_month_week(row['date']) 
        
        results.append(f"{row['date'].year}년 {m}월 {w}주차")
        
    return results

def calculate_lexicon_score(text):
    cleaned = re.sub('[^가-힣\s]', '', text).lower()
    pos = sum(len(re.findall(rf'\b{w}\b', cleaned)) for w in POSITIVE_WORDS)
    neg = sum(len(re.findall(rf'\b{w}\b', cleaned)) for w in NEGATIVE_WORDS)
    return (pos / (pos + neg) * 100) if (pos + neg) > 0 else 50.0

def classify_sentiment(score):
    return f"🟢 긍정" if score > 60 else f"🔴 부정"

def calculate_key_metrics(df):
    if df.empty: return 'N/A', 'N/A'
    most_freq = df['postdate'].mode()[0].strftime('%Y-%m-%d')
    d1 = df[(df['postdate'] >= datetime.now() - timedelta(30))].shape[0]
    d2 = df[(df['postdate'] >= datetime.now() - timedelta(60)) & (df['postdate'] < datetime.now() - timedelta(30))].shape[0]
    rate = f"{((d1-d2)/d2)*100:+.1f}%" if d2 > 0 else "0.0%"
    return most_freq, rate

# ==================================================================
# [3] 메인 실행 함수 (Flask 호출용)
# ==================================================================
def run_full_analysis(search_query, competitor_query, client_id, client_secret, max_results, static_folder):
    results = {
        "query": search_query, "competitor_query": competitor_query,
        "status": "FAILURE", "message": "오류", "visualization_urls": {}
    }

    if not is_valid_query(search_query):
        results["message"] = "검색어 오류"
        return results

    # 1. 데이터 수집
    blog = fetch_naver_search_results(search_query, 'blog', client_id, client_secret, max_results)
    news = fetch_naver_search_results(search_query, 'news', client_id, client_secret, max_results)
    total = pd.concat([blog, news], ignore_index=True)
    trend = get_search_trend(search_query, client_id, client_secret)

    if total.empty:
        results["status"] = "INSUFFICIENT_DATA"
        return results

    comp_df = pd.DataFrame()
    if competitor_query:
        cb = fetch_naver_search_results(competitor_query, 'blog', client_id, client_secret, max_results)
        cn = fetch_naver_search_results(competitor_query, 'news', client_id, client_secret, max_results)
        comp_df = pd.concat([cb, cn], ignore_index=True)

    # 2. 지표 계산
    desc = ' '.join(total['description'].astype(str).tolist())
    score = calculate_lexicon_score(desc)
    sent_label = classify_sentiment(score)
    freq_date, change_rate = calculate_key_metrics(total)
    outbreak = find_outbreak_weeks(trend)

    # 3. 시각화 생성 (⚠️ 고유 ID 사용)
    unique_id = str(uuid.uuid4())[:8]
    urls = {}
    
    pos_p, neg_p, all_p, top_k = visualize_sentiment_word_clouds(total, POSITIVE_WORDS, NEGATIVE_WORDS)
    urls["positive_wordcloud"] = save_and_get_url(lambda: pos_p, "sentiment_pos_wc.png", static_folder, unique_id)
    urls["negative_wordcloud"] = save_and_get_url(lambda: neg_p, "sentiment_neg_wc.png", static_folder, unique_id)
    urls["combined_wordcloud"] = save_and_get_url(lambda: all_p, "sentiment_wc.png", static_folder, unique_id)
    
    urls["monthly_frequency"] = save_and_get_url(lambda: visualize_post_frequency(total, 'monthly'), "freq_month.png", static_folder, unique_id)
    urls["weekly_frequency"] = save_and_get_url(lambda: visualize_post_frequency(total, 'weekly'), "freq_week.png", static_folder, unique_id)
    urls["combined_trend"] = save_and_get_url(lambda: visualize_combined_trend(total, trend), "trend_cross.png", static_folder, unique_id)

    if not comp_df.empty:
        urls["competitor_comparison"] = save_and_get_url(
            lambda: visualize_competitor_mention_comparison(search_query, total, competitor_query, comp_df),
            "comp_compare.png", static_folder, unique_id
        )

    # 4. 결과 반환
    results.update({
        "status": "SUCCESS", "message": "완료",
        "total_mentions": len(total),
        "most_frequent_date": freq_date,
        "mention_change_rate": change_rate,
        "positive_percentage": int(score),
        "final_sentiment_label": sent_label,
        "top_keywords": top_k.to_dict('records'),
        "visualization_urls": urls,
        "post_list": total[['title', 'postdate', 'channel_name', 'link']].rename(columns={'postdate': 'date', 'channel_name': 'author'}).to_dict('records'),
        "outbreak_weeks": outbreak
    })

    results["ai_report"] = generate_smart_report(
        search_query, len(total), sent_label, int(score), results["top_keywords"], 
        outbreak, not trend.empty, freq_date, change_rate, 
        os.getenv("GEMINI_API_KEY")
    )
    
    return results

if __name__ == "__main__":
    print("Flask 백엔드 모듈입니다.")