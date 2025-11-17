import os
import pandas as pd
import json
import re
import requests 
from datetime import datetime, timedelta
from collections import Counter 
import gc 
import matplotlib.pyplot as plt 
import matplotlib
import requests.utils

# ⚠️ [추가] Flask 연동 및 데이터 처리를 위해 필수적인 라이브러리 추가
import io 
import numpy as np 

# 태그 클라우드 라이브러리
from wordcloud import WordCloud 


# 시각화 라이브러리
import seaborn as sns

from matplotlib import font_manager, rc 


def save_and_get_url(plot_func, filename, static_folder):
    """ Matplotlib 그래프를 파일로 저장하고 URL을 반환합니다. """
    if not static_folder:
        return None

    try:
        # --- ⚠️ [수정] ---
        # 1. 'static' 폴더 안에 'img' 폴더 경로를 만듭니다.
        img_save_path = os.path.join(static_folder, 'img')

        # 2. 'static/img' 폴더가 없으면 새로 생성합니다.
        if not os.path.exists(img_save_path):
            os.makedirs(img_save_path)
        # ---------------------

        plot_object = plot_func()

        if plot_object is None:
             return None

        # 3. 파일 저장 경로를 'static/img/파일이름'으로 변경합니다.
        filepath = os.path.join(img_save_path, filename) # 👈 static/img/파일이름

        if os.path.exists(filepath):
            os.remove(filepath)

        plot_object.savefig(filepath, dpi=100)
        plt.close('all')        # 4. 브라우저가 이미지를 요청할 URL도 '/static/img/파일이름'으로 변경합니다.
        return f"/static/img/{filename}" # 👈 /static/img/파일이름

    except Exception as e:
        print(f"-> ❌ 시각화 저장 및 URL 생성 중 오류 발생 ({filename}): {e}")
        plt.close('all')
        return None

# ----------------------------------------------------
# --- ⚠️설정 (Configuration) ---
NAVER_CLIENT_ID = "keeE_3_zOuG8ndn5AdQd" 
NAVER_CLIENT_SECRET = "FVUwmNaHst" 
# ----------------------------------------------------

# 🚨🚨 데이터 수집 갯수 설정 부분 🚨🚨
MAX_RESULTS_PER_API = 1000 


# --- 순수 Python 감성 사전 정의 (Lexicon) ---
POSITIVE_WORDS = [
    '좋아요', '최고', '만족', '추천', '강력추천', '대박', '예쁘', '편안', '행복', '감사', 
    '기쁨', '훌륭', '사랑', '재미', '즐거움', '성공', '합격', '선물', '따뜻', '밝은', 
    '완벽', '인생템', '가성비', '착한', '놀랍', '기대', '보람', '깨끗', '싱그러', '프리미엄'
]

NEGATIVE_WORDS = [
    '별로', '실망', '아쉬움', '나쁘', '불만', '불편', '최악', '힘들', '걱정', '문제', 
    '어려움', '부족', '실패', '낭비', '쓰레기', '비싸', '떨어짐', '실망스럽', '지루', '후회',
    '이상', '오류', '짜증', '고통', '논란', '부정적', '약점', '결함', '복잡', '불필요'
]

# --- 폰트 설정 (통합 로직) ---
# 1. 시스템에 설치된 한글 폰트 찾기
def get_korean_font():
    """시스템에서 사용 가능한 한글 폰트(Malgun Gothic, AppleGothic, NanumGothic 등)를 찾습니다."""
    font_names = ['Malgun Gothic', 'AppleGothic', 'NanumGothic', 'Noto Sans CJK JP']
    for font_name in font_names:
        font_path = font_manager.findfont(font_name)
        if font_path:
            return font_name, font_path
    return None, None

korean_font_name, korean_font_path = get_korean_font()

if korean_font_name:
    # 2. 폰트 캐시 초기화 (필요시)
    try:
        # 이 부분은 환경에 따라 캐시가 존재하지 않을 수 있습니다.
        pass
    except Exception:
        pass
    
    # 3. Matplotlib에 폰트 설정 적용
    # ⚠️ [유지] font_manager.fontManager.addfont 호출은 환경에 따라 에러를 일으킬 수 있지만, 
    # 안정적인 사용자 환경을 가정하고 유지합니다.
    # font_manager.fontManager.addfont(korean_font_path)
    rc('font', family=korean_font_name)
    print(f"-> ✅ 한글 폰트 '{korean_font_name}' 설정 완료.")
    FONT_PATH = korean_font_path # 워드클라우드용 경로 설정
else:
    print("-> ⚠️ 한글 폰트를 찾을 수 없습니다. 기본 폰트로 실행합니다.")
    FONT_PATH = None
    
plt.rcParams['axes.unicode_minus'] = False # 마이너스 기호 깨짐 방지
# ----------------------------------------------------

# ----------------------------------------------------
# --- 검색어 유효성 및 브랜드명 검증 함수 ---
# ----------------------------------------------------

def is_valid_query(query):
    """ 무의미한 반복 문자열, 너무 짧은 문자열 등을 걸러내 분석을 위한 검색어인지 확인합니다. """
    if len(query.replace(' ', '')) < 2:
        print("-> ❌ 검색어 길이가 너무 짧습니다. (공백 제외 2자 미만)")
        return False
    # ⚠️ [수정] 정규식 패턴이 일부 환경에서 오류를 일으킬 수 있어, Raw String으로 명시합니다.
    repeated_pattern = re.compile(r'([가-힣a-zA-Z0-9])\1{3,}')
    if repeated_pattern.search(query):
        print("-> ❌ 동일한 문자가 4회 이상 반복되는 패턴을 포함하고 있습니다. (무의미한 검색어로 판단)")
        return False
    return True

def is_brand_name(query, client_id, client_secret, confidence_threshold=0.6):
    """ 네이버 쇼핑 API를 이용해 검색어가 브랜드명인지 교차 검증합니다. """
    print(f"\n--- 0단계: '{query}'가 브랜드명인지 검증 시작 ---")
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {"query": query, "display": 20} 

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])

        if not items:
            print("-> 쇼핑 검색 결과가 없어 브랜드명으로 판단할 수 없습니다.")
            return False

        brands = [item.get("brand") for item in items if item.get("brand")]
        if not brands:
            print("-> 검색 결과에서 브랜드명을 찾을 수 없습니다.")
            return False

        brands = [b.strip() for b in brands] # ⚠️ [추가] 브랜드명 앞뒤 공백 제거
        
        brand_counts = Counter(brands)
        most_common_brand, count = brand_counts.most_common(1)[0]
        dominance_ratio = count / len(brands)
        
        is_dominant = dominance_ratio >= confidence_threshold
        # ⚠️ [수정] 검색어와 브랜드명을 비교할 때, 소문자화하여 정확한 비교를 수행합니다.
        is_query_matched = most_common_brand.lower() == query.lower() 

        print(f"-> 가장 많이 노출된 브랜드: '{most_common_brand}' (비중: {dominance_ratio:.2%})")

        if is_dominant and is_query_matched:
            print(f"-> ✅ 브랜드명 일치 및 비중({dominance_ratio:.2%}) 통과.")
            return True
        else:
            reason = []
            if not is_dominant:
                reason.append(f"브랜드 비중({dominance_ratio:.2%})이 기준치({confidence_threshold:.0%}) 미만")
            if not is_query_matched:
                reason.append(f"가장 지배적인 브랜드('{most_common_brand}')가 검색어와 불일치")
            
            print(f"-> ❌ 브랜드명으로 판단하기 어려움 ({', '.join(reason)}).")
            return False

    except requests.exceptions.RequestException as e:
        # ⚠️ [수정] 오류 발생 시 500 에러를 반환해야 하므로, 함수를 종료합니다.
        print(f"쇼핑 API 호출 중 오류 발생: {e}")
        return False

# ----------------------------------------------------
# --- 데이터 수집 및 전처리 함수 ---
# ----------------------------------------------------

def fetch_naver_search_results(query, api_type, client_id, client_secret, total_results):
    """ Blog 또는 News 데이터를 수집합니다. """
    print(f"\n--- 1단계: '{api_type.capitalize()}' 데이터 수집 시작 (최대 {total_results}건) ---")

    if api_type == 'blog':
        url_template = "https://openapi.naver.com/v1/search/blog.json"
    elif api_type == 'news':
        url_template = "https://openapi.naver.com/v1/search/news.json"
    else:
        return pd.DataFrame() 

    # ⚠️ [수정] 최종 DF는 일관된 컬럼명을 가져야 합니다.
    df_columns = ['title', 'link', 'description', 'channel_name', 'postdate', 'channel_type'] 
    df = pd.DataFrame(columns=df_columns)
    display = 100
    remove_tag = re.compile('<.*?>')

    for start in range(1, min(total_results, 1001) + 1, display): 
        # ⚠️ [수정] query를 URL 인코딩하지 않아도 requests 라이브러리에서 자동으로 처리해줍니다.
        url = url_template
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret
        }
        params = {
            "query": query,
            "display": display,
            "start": start
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                break

            processed_items = []
            for item in items:
                clean_item = {}
                clean_item['title'] = re.sub(remove_tag, '', item.get('title', ''))
                clean_item['description'] = re.sub(remove_tag, '', item.get('description', ''))
                clean_item['link'] = item.get('link', '') 
                
                # ⚠️ [수정] 채널명 및 날짜 처리 로직 통일
                if api_type == 'blog':
                    clean_item['channel_name'] = re.sub(remove_tag, '', item.get('bloggername', ''))
                    raw_date = item.get('postdate', '')
                    clean_item['postdate'] = pd.to_datetime(raw_date, format='%Y%m%d', errors='coerce').normalize() # YYYYMMDD 형식
                elif api_type == 'news':
                    clean_item['channel_name'] = item.get('publisher', '') 
                    raw_date = item.get('pubDate', '')
                    # RFC 822 형식 처리 (예: Wed, 25 Oct 2023 00:00:00 +0900)
                    clean_item['postdate'] = pd.to_datetime(raw_date, format='%a, %d %b %Y %H:%M:%S +0900', errors='coerce').normalize()
                    
                clean_item['channel_type'] = api_type # 채널 타입 추가

                processed_items.append(clean_item)

            temp_df = pd.DataFrame(processed_items)
            df = pd.concat([df, temp_df], ignore_index=True)

        except requests.exceptions.RequestException as e:
            print(f"{api_type.capitalize()} API 호출 중 오류 발생 (start={start}): {e}")
            break 

    df = df.dropna(subset=['postdate']).drop_duplicates()
    df = df[df['postdate'] <= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)]
    print(f"-> 총 {len(df)}건의 '{api_type.capitalize()}' 데이터를 수집했습니다.")
    return df


def get_search_trend(query, client_id, client_secret):
    """ 네이버 데이터랩 API를 이용해 최근 1년간의 월간 검색량 추이를 가져옵니다. """
    # ⚠️ [수정] 주간(90일) 대신 월간(365일) 트렌드를 가져오도록 수정했습니다.
    print(f"\n--- 2단계: '{query}' 월간 검색량 추이 데이터 수집 시작 (최근 1년) ---")

    url = "https://openapi.naver.com/v1/datalab/search"
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d') # 최근 1년

    body = json.dumps({
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": "month",  # ⚠️ [수정] 월간 단위 요청
        "keywordGroups": [{"groupName": query, "keywords": [query]}]
    })
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, data=body)
        response.raise_for_status()
        data = response.json()

        if not data.get('results') or not data['results'][0].get('data'):
             print("-> ❌ 데이터랩 API 응답에 유효한 데이터가 없습니다.")
             return pd.DataFrame(columns=['date', 'ratio']) # ⚠️ [수정] 반환 컬럼명 통일

        trend_df = pd.DataFrame(data['results'][0]['data'])
        # ⚠️ [수정] 컬럼명을 'date', 'ratio'로 통일하여 교차 분석 함수에서 사용하기 쉽게 합니다.
        trend_df = trend_df.rename(columns={'period': 'date', 'ratio': 'ratio'}) 
        
        trend_df['date'] = pd.to_datetime(trend_df['date']) 
        
        print(f"-> 최근 1년간의 월간 검색량 데이터를 수집했습니다. (총 {len(trend_df)}건)")
        return trend_df[['date', 'ratio']]

    except requests.exceptions.RequestException as e:
        print(f"데이터랩 API 호출 중 오류 발생: {e}")
        return pd.DataFrame(columns=['date', 'ratio'])
    except Exception as e:
        print(f"데이터랩 처리 중 예상치 못한 오류 발생: {e}")
        return pd.DataFrame(columns=['date', 'ratio'])
    
# ----------------------------------------------------
# --- 시각화 함수 (플롯 객체 생성) ---
# ----------------------------------------------------

def visualize_post_frequency(df, frequency_type='monthly'): 
    """ 단일 통합 데이터프레임을 받아 월별 또는 주별 언급량 추이를 시각화하고 플롯 객체를 반환합니다. """
    time_unit = "월별" if frequency_type == 'monthly' else "주별"
    time_span = "12개월" if frequency_type == 'monthly' else "6개월"
    color = 'darkorange' if frequency_type == 'monthly' else 'purple'
    
    print(f"\n--- 3단계 분석: {time_unit} 언급량 시각화 ({time_span}) (현재 기간 제외) ---")
    
    temp_df = df.copy()
    
    try:
        temp_df['postdate'] = pd.to_datetime(temp_df['postdate'], errors='coerce').dt.normalize()
    except Exception:
        print(f"경고: 날짜 변환 중 오류 발생. 분석을 건너뜕니다.")
        return None  # None 반환으로 통일
    
    temp_df.dropna(subset=['postdate'], inplace=True)
    if temp_df.empty:
        print("경고: 유효한 날짜를 가진 게시물 데이터가 없어 분석을 건너뜕니다.")
        return None
        
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 🌟 이전에 생략 주석이 있던 부분 (이제 로직이 모두 포함되어 깔끔해졌습니다) 🌟
    if frequency_type == 'monthly':
        current_month_start = now.replace(day=1)
        # 현재 월보다 이전 데이터만 사용
        df_filtered = temp_df[temp_df['postdate'] < current_month_start].copy()
        start_date_offset = pd.DateOffset(months=12)
        freq_label = 'post_month'
        freq_unit = 'MS'
        
        if not df_filtered.empty:
            # 최근 12개월 데이터만 필터링 (최신 날짜 기준으로 12개월)
            latest_date = df_filtered['postdate'].max()
            df_filtered = df_filtered[df_filtered['postdate'] >= (latest_date - start_date_offset)].copy()
            df_filtered[freq_label] = df_filtered['postdate'].dt.strftime('%Y-%m')
            counts_raw = df_filtered[freq_label].value_counts().sort_index()
            
            # 빈 월을 채우기 위한 전체 레이블 생성
            start_month = counts_raw.index.min() if not counts_raw.empty else (now - start_date_offset).strftime('%Y-%m')
            end_month = counts_raw.index.max() if not counts_raw.empty else (now - pd.DateOffset(months=1)).strftime('%Y-%m')
            
            full_index_range = pd.date_range(start=start_month, end=end_month, freq=freq_unit)
            full_labels = full_index_range.strftime('%Y-%m')
            rotation_angle = 45
        else:
            print(f"경고: 필터링 결과 최근 {time_span} 이내의 유효한 게시물이 없어 {time_unit} 분석을 건너뜕니다.")
            return None # None 반환으로 통일

    elif frequency_type == 'weekly':
        # 현재 주차의 시작일 (월요일 시작으로 가정)
        # 현재 주차 시작일 (월요일)
        current_week_start = (now - timedelta(days=now.weekday()))
        
        # 현재 주보다 이전 데이터만 사용
        df_filtered = temp_df[temp_df['postdate'] < current_week_start].copy()
        start_date_offset = pd.DateOffset(months=6) # 주별은 최근 6개월 기준

        if not df_filtered.empty:
            # 최근 6개월 데이터만 필터링
            latest_date = df_filtered['postdate'].max()
            df_filtered = df_filtered[df_filtered['postdate'] >= (latest_date - start_date_offset)].copy()
            
            # ** 🎯 핵심 수정: resample을 사용하여 주차별 카운트 및 빈 주차 채우기 **
            
            # postdate를 인덱스로 설정
            df_resample = df_filtered.set_index('postdate')
            
            # 'W'를 사용하여 주별로 재표본 추출 (기본적으로 일요일에 끝나는 주차로 카운트)
            counts_resampled = df_resample.resample('W').size() # count.value_counts() 대신 size() 사용
            
            full_counts = counts_resampled
            
            # resample 결과 인덱스 (날짜 객체)를 'YYYY-MM-DD' 형식의 문자열 레이블로 변환
            full_counts.index = full_counts.index.strftime('%Y-%m-%d')
            full_labels = full_counts.index.tolist() # 재색인 불필요
            rotation_angle = 90
        else:
            print(f"경고: 필터링 결과 최근 {time_span} 이내의 유효한 게시물이 없어 {time_unit} 분석을 건너뜕니다.")
            return None # None 반환으로 통일
    
    else:
        return None

    if 'full_counts' not in locals() or full_counts.empty: # full_counts 변수 생성 확인 및 비어있는지 확인
        print(f"경고: 필터링 결과 최근 {time_span} 이내의 유효한 게시물이 없어 {time_unit} 분석을 건너뜕니다.")
        return None

    # 월별 로직을 따르기 위해 full_counts를 counts_raw와 full_labels로 분리 (주별 로직은 이미 full_counts에 통합됨)
    if frequency_type == 'monthly':
        counts_series = counts_raw.rename('count')
        full_counts = counts_series.reindex(full_labels, fill_value=0)
    
    # 시각화 실행
    plt.figure(figsize=(15 if frequency_type == 'weekly' else 12, 6))
    sns.lineplot(
        x=full_counts.index, y=full_counts.values, marker='o', color=color
    )

    plt.title(f'최근 {time_span} 언급량 추이 (현재 {time_unit[:-1]} 제외)', fontsize=16) 
    
    # 주별/월별에 따라 x축 레이블 설정
    if frequency_type == 'weekly':
        plt.xlabel(f'언급 {time_unit} (주차 종료일)', fontsize=12) # 레이블 수정
    else:
        plt.xlabel(f'언급 {time_unit}', fontsize=12) 
        
    plt.ylabel('총 언급량', fontsize=12)

    plt.xticks(full_counts.index, rotation=rotation_angle) 
    plt.grid(axis='y', linestyle='--')
    plt.tight_layout()
    
    print(f"-> 통합 데이터 {time_unit} 언급량 시각화 플롯 객체 생성 완료.")
    return plt

def visualize_combined_trend(total_df, trend_df):
    """ 검색량(월간)과 언급량(월간)을 하나의 그래프에 시각화하고 플롯 객체를 반환합니다. """
    print("\n--- 4단계 분석: 언급량 vs 검색량 통합 시각화 (최근 1년 월간 단위) ---")
    
    if trend_df.empty or 'date' not in trend_df.columns:
        print("경고: 검색량(데이터랩) 데이터가 없거나 형식이 잘못되어 통합 분석을 건너뜁니다.")
        return
        
    temp_df = total_df.copy()
    
    try:
        temp_df['postdate'] = pd.to_datetime(temp_df['postdate'], errors='coerce').dt.normalize()
        temp_df.dropna(subset=['postdate'], inplace=True)
    except Exception:
        return

    temp_df['month_start_date'] = temp_df['postdate'].dt.to_period('M').apply(lambda x: x.start_time).dt.normalize() 
    mention_counts = temp_df['month_start_date'].value_counts().reset_index()
    mention_counts.columns = ['date', 'mention_count']
    
    trend_df['date'] = trend_df['date'].dt.to_period('M').apply(lambda x: x.start_time).dt.normalize()
    
    start_date = trend_df['date'].min()
    end_date = trend_df['date'].max()
    mention_counts = mention_counts[
        (mention_counts['date'] >= start_date) & (mention_counts['date'] <= end_date)
    ]
    
    combined_df = pd.merge(trend_df, mention_counts, on='date', how='left').fillna(0)
    
    max_mention = combined_df['mention_count'].max()
    combined_df['mention_ratio'] = (combined_df['mention_count'] / max_mention) * 100 if max_mention > 0 else 0.0
    
    # 시각화 (Dual Axis)
    fig, ax1 = plt.subplots(figsize=(12, 6))
    x_labels = combined_df['date'].dt.strftime('%Y-%m')

    color = 'tab:red'
    ax1.set_xlabel('월간 (시작일 기준)', fontsize=12)
    ax1.set_ylabel('검색량 비율 (0-100) - Datalab 기준', color=color, fontsize=12)
    sns.lineplot(x=combined_df.index, y='ratio', data=combined_df, marker='o', color=color, ax=ax1, label='검색량')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_ylim(0, 100)
    ax1.set_xticks(combined_df.index)
    ax1.set_xticklabels(x_labels, rotation=45, ha='right')
    ax1.legend(loc='upper left')

    ax2 = ax1.twinx() 
    color = 'tab:blue'
    ax2.set_ylabel('언급량 비율 (0-100) - 자체 최대 언급량 기준', color=color, fontsize=12) 
    sns.lineplot(x=combined_df.index, y='mention_ratio', data=combined_df, marker='s', color=color, ax=ax2, label='언급량')
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.set_ylim(0, 100)
    ax2.legend(loc='upper right')
    
    plt.title('최근 1년 월간 검색량 및 언급량 추이 비교 (0-100 비율)', fontsize=16)
    fig.tight_layout()
    print("-> 검색량 및 언급량 통합 시각화 플롯 객체 생성 완료.")
    return plt

def visualize_sentiment_word_clouds(df, positive_words, negative_words):
    """ 감성 사전 기반 긍정/부정 워드 클라우드 플롯 객체와 상위 7개 키워드 DF를 반환합니다. """
    print("\n--- 5단계 분석: 감성 사전 기반 긍정/부정 및 통합 키워드 분석 시작 ---")
    
    if df.empty or 'description' not in df.columns:
        return (None, None, None, pd.DataFrame())

    text = ' '.join(df['description'].astype(str).tolist())
    cleaned_text = re.sub('[^가-힣\s]', '', text).lower()
    
    def get_word_counts(word_list, text_corpus, max_words=20):
        counts = {}
        for word in word_list:
            count = len(re.findall(r'\b' + re.escape(word) + r'\b', text_corpus)) 
            if count > 0:
                counts[word] = count
        return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True)[:max_words])
    
    def create_wordcloud_plot(counts, title, colormap):
        if not counts:
            return None

        wc = WordCloud(
            font_path=FONT_PATH, width=800, height=400, background_color='white',
            max_words=20, colormap=colormap, prefer_horizontal=0.9, collocations=False 
        )
        wordcloud = wc.generate_from_frequencies(counts)
        
        fig = plt.figure(figsize=(12, 7)) 
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off') 
        plt.title(title, fontsize=16)
        plt.tight_layout(pad=3.0) 
        
        return fig

    pos_counts = get_word_counts(positive_words, cleaned_text, max_words=20)
    pos_plot = create_wordcloud_plot(pos_counts, '긍정 감성 키워드 태그 클라우드 (Top 20)', 'YlGn')
    
    neg_counts = get_word_counts(negative_words, cleaned_text, max_words=20)
    neg_plot = create_wordcloud_plot(neg_counts, '부정 감성 키워드 태그 클라우드 (Top 20)', 'Reds_r')

    ALL_SENTIMENT_WORDS = positive_words + negative_words
    all_counts_top20 = get_word_counts(ALL_SENTIMENT_WORDS, cleaned_text, max_words=20)
    all_plot = create_wordcloud_plot(all_counts_top20, '긍정+부정 통합 키워드 태그 클라우드 (Top 20)', 'plasma')
    
    all_counts_top7 = {k: all_counts_top20[k] for k in list(all_counts_top20.keys())[:min(7, len(all_counts_top20))]}
    all_df = pd.DataFrame(all_counts_top7.items(), columns=['키워드', '언급 횟수'])
    
    print("-> 감성 사전 기반 워드클라우드 플롯 객체 생성 및 상위 키워드 분석 완료.")
    return pos_plot, neg_plot, all_plot, all_df

def visualize_competitor_mention_comparison(own_query, own_df, competitor_query, competitor_df):
    """ 자사/경쟁사 월별 언급량을 비교하여 시각화하고 플롯 객체를 반환합니다. """
    print(f"\n--- 9단계 분석: 자사({own_query}) vs 경쟁사({competitor_query}) 월별 언급량 비교 시각화 시작 ---")

    if own_df.empty and competitor_df.empty:
        print("경고: 자사와 경쟁사 모두 유효한 데이터가 없어 비교 분석을 건너뜁니다.")
        return None

    def prepare_monthly_counts(df, label):
        temp_df = df.copy()
        if temp_df.empty: return pd.Series([], dtype='int64', name=label)
        try:
            temp_df['postdate'] = pd.to_datetime(temp_df['postdate'], errors='coerce').dt.normalize()
            temp_df.dropna(subset=['postdate'], inplace=True)
            
            now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            current_month_start = now.replace(day=1)
            start_date_offset = pd.DateOffset(months=12)
            
            df_filtered = temp_df[temp_df['postdate'] < current_month_start].copy()
            if df_filtered.empty: return pd.Series([], dtype='int64', name=label)
                 
            latest_date = df_filtered['postdate'].max()
            df_filtered = df_filtered[df_filtered['postdate'] >= (latest_date - start_date_offset)].copy()
            
            df_filtered['post_month'] = df_filtered['postdate'].dt.strftime('%Y-%m')
            counts = df_filtered['post_month'].value_counts().sort_index().rename(label)
            return counts
        except Exception as e:
            print(f"경고: {label} 데이터 전처리 중 오류 발생. {e}")
            return pd.Series([], dtype='int64', name=label)

    own_counts = prepare_monthly_counts(own_df, own_query)
    comp_counts = prepare_monthly_counts(competitor_df, competitor_query)
    combined_counts = pd.concat([own_counts, comp_counts], axis=1).fillna(0)
    combined_counts.index.name = 'Month'
    
    if combined_counts.shape[0] < 2:
        print("경고: 비교할 월 데이터가 부족합니다. (최소 2개월 필요)")
        return None

    plt.figure(figsize=(14, 7))
    sns.lineplot(x=combined_counts.index, y=own_query, data=combined_counts, marker='o', color='tab:blue', label=own_query)
    sns.lineplot(x=combined_counts.index, y=competitor_query, data=combined_counts, marker='s', color='tab:red', label=competitor_query)

    plt.title(f'{own_query} vs {competitor_query} 월별 언급량 추이 비교 (최근 12개월)', fontsize=16) 
    plt.xlabel('월', fontsize=12) 
    plt.ylabel('총 언급량', fontsize=12)
    plt.xticks(combined_counts.index, rotation=45) 
    plt.legend(fontsize=12)
    plt.grid(axis='y', linestyle='--')
    plt.tight_layout()
    
    print("-> 자사/경쟁사 언급량 비교 시각화 플롯 객체 생성 완료.")
    return plt


# ----------------------------------------------------
# --- 핵심 분석 함수 (지표 계산 및 감성 분석) ---
# ----------------------------------------------------

def find_outbreak_weeks(trend_df, change_threshold=0.5):
    """ 월간 검색량 비율을 기준으로 전월 대비 검색량이 급증한 월간을 찾습니다. """
    print(f"\n--- 6단계 분석: 이슈 확산 월간 추출 시작 (전월 대비 {change_threshold * 100:.0f}% 초과 증가 기준) ---")
    
    if trend_df.empty or 'date' not in trend_df.columns:
        print("-> ❌ 검색량(데이터랩) 데이터가 없어 확산 월간 분석을 건너뜁니다.")
        return []

    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).replace(day=1)
    filtered_trend_df = trend_df[trend_df['date'] < now].copy()
    filtered_trend_df = filtered_trend_df.sort_values(by='date')
    
    if filtered_trend_df.empty:
        print("-> ❌ 유효한 과거 월간 데이터가 없어 확산 월간 분석을 건너뜁니다.")
        return []

    filtered_trend_df['ratio'] = pd.to_numeric(filtered_trend_df['ratio'], errors='coerce')
    filtered_trend_df.dropna(subset=['ratio'], inplace=True)
    filtered_trend_df['prev_ratio'] = filtered_trend_df['ratio'].shift(1).fillna(0)
    
    filtered_trend_df['change_rate'] = filtered_trend_df.apply(
        lambda row: (row['ratio'] - row['prev_ratio']) / row['prev_ratio'] 
                     if row['prev_ratio'] > 0 else (100.0 if row['ratio'] > 0 else 0), 
        axis=1
    )
    
    outbreak_months_df = filtered_trend_df[
        ((filtered_trend_df['prev_ratio'] > 0) & (filtered_trend_df['change_rate'] > change_threshold)) | 
        ((filtered_trend_df['prev_ratio'] == 0) & (filtered_trend_df['ratio'] > 0))
    ].copy()
    
    outbreak_results = []
    if not outbreak_months_df.empty:
        outbreak_months_df = outbreak_months_df.sort_values(by='ratio', ascending=False)
        for _, row in outbreak_months_df.iterrows():
            month_start = row['date'].strftime('%Y-%m')
            current_ratio = row['ratio']
            prev_ratio = row['prev_ratio']
            
            rate_str = f"{row['change_rate'] * 100:.1f}% 증가" if row['prev_ratio'] > 0 else "신규 발생 (전월 0)"
            outbreak_results.append(f"{month_start} (현재 비율: {current_ratio:.1f}, 전월: {prev_ratio:.1f}, {rate_str})")
            
        print(f"-> ✅ 총 {len(outbreak_results)}개의 검색량 급증 월간을 찾았습니다.")
        
    return outbreak_results

def calculate_lexicon_score(text_corpus):
    """ 감성 사전을 기반으로 긍정성 지수를 계산합니다. """
    print("\n--- 7단계 분석: 순수 Python 감성 사전을 이용한 감성 분석 시작 ---")
    
    cleaned_text = re.sub('[^가-힣\s]', '', text_corpus).lower()
    pos_count = sum(len(re.findall(r'\b' + re.escape(word) + r'\b', cleaned_text)) for word in POSITIVE_WORDS)
    neg_count = sum(len(re.findall(r'\b' + re.escape(word) + r'\b', cleaned_text)) for word in NEGATIVE_WORDS)

    total_sentiment_count = pos_count + neg_count

    if total_sentiment_count == 0:
        print("-> 감성 단어가 텍스트에서 발견되지 않아 중립 처리됩니다.")
        return 50.0

    positive_score = (pos_count / total_sentiment_count) * 100
    
    print(f"-> 긍정 단어: {pos_count}회, 부정 단어: {neg_count}회")
    print(f"-> 계산된 긍정성 지수: {positive_score:.2f}%")
    
    return positive_score

def classify_sentiment(positive_score):
    """ 사용자 지정 규칙에 따라 최종 감성을 분류합니다. """
    if positive_score > 60:
        return f"🟢 긍정 ({positive_score:.1f}%)"
    else: 
        return f"🔴 부정 ({positive_score:.1f}%)"

def calculate_key_metrics(df):
    """ 최다 언급량 날짜와 언급량 증감률(최근 30일 vs 이전 30일)을 계산합니다. """
    default_date = 'N/A'
    default_rate = 'N/A'
    
    temp_df = df.copy()
    print("\n--- 8단계 분석: 최다 언급 날짜 및 증감률 계산 시작 ---")
    
    try:
        temp_df['postdate'] = pd.to_datetime(temp_df['postdate'], errors='coerce').dt.normalize()
        temp_df.dropna(subset=['postdate'], inplace=True)
    except Exception as e:
        print(f"-> ❌ 언급량 분석: 날짜 변환 실패. {e}")
        return default_date, default_rate

    if temp_df.empty: return default_date, default_rate

    # 1. 최다 언급량 날짜
    daily_counts = temp_df['postdate'].dt.normalize().value_counts()
    most_frequent_date = default_date
    if not daily_counts.empty:
        max_count = daily_counts.max()
        most_frequent_date = daily_counts[daily_counts == max_count].index.max().strftime('%Y-%m-%d')
        print(f"-> 최다 언급량 날짜: {most_frequent_date} ({max_count}회)")

    # 2. 언급량 증감률
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_d1, end_d1 = now - timedelta(days=30), now 
    start_d2, end_d2 = now - timedelta(days=60), now - timedelta(days=30)

    mentions_d1 = temp_df[(temp_df['postdate'].dt.normalize() >= start_d1) & (temp_df['postdate'].dt.normalize() < end_d1)].shape[0]
    mentions_d2 = temp_df[(temp_df['postdate'].dt.normalize() >= start_d2) & (temp_df['postdate'].dt.normalize() < end_d2)].shape[0]

    mention_change_rate = default_rate

    if mentions_d2 > 0:
        change_rate = ((mentions_d1 - mentions_d2) / mentions_d2) * 100
        mention_change_rate = f"{change_rate:+.1f}%" 
    elif mentions_d1 > 0:
        mention_change_rate = "+100% (신규)"
    else:
        mention_change_rate = "0.0%"

    print(f"-> 증감률 분석: 최근 30일({mentions_d1}건) vs 이전 30일({mentions_d2}건). 증감률: {mention_change_rate}")
    return most_frequent_date, mention_change_rate


# ----------------------------------------------------
# --- 메인 실행 함수 (Flask API 엔드포인트에 사용) ---
# ----------------------------------------------------

def run_full_analysis(search_query: str, competitor_query: str, client_id: str, client_secret: str, max_results: int, static_folder: str) -> dict:
    """
    브랜드 평판 분석의 전체 파이프라인을 실행하고 결과를 JSON 응답용 딕셔너리로 반환합니다.
    """
    
    analysis_results = {
        "query": search_query,
        "competitor_query": competitor_query,
        "status": "FAILURE",
        "message": "분석 실패: 알 수 없는 오류",
        "key_metrics": {},
        "sentiment_analysis": {},
        "trend_analysis": {},
        "visualization_urls": {}
    }

    # 1. 유효성 검증
    if not is_valid_query(search_query) or not is_brand_name(search_query, client_id, client_secret):
        analysis_results["message"] = "자사 검색어 유효성/브랜드명 검증에 실패하여 분석을 종료합니다."
        return analysis_results
    
    is_comp_valid = competitor_query and is_valid_query(competitor_query)
    if not is_comp_valid: competitor_query = None

    print("\n==================================================")
    print("✅ 데이터 수집 및 분석을 시작합니다.")
    print("==================================================")
    
    # 2. 자사 데이터 수집 및 통합
    blog_df = fetch_naver_search_results(search_query, 'blog', client_id, client_secret, max_results)
    news_df = fetch_naver_search_results(search_query, 'news', client_id, client_secret, max_results)
    total_df = pd.concat([blog_df, news_df], ignore_index=True)
    
    # 3. 검색량 추이 분석 (월간)
    trend_df = get_search_trend(search_query, client_id, client_secret)
    
    # 4. 경쟁사 데이터 수집
    competitor_df = pd.DataFrame()
    if is_comp_valid and competitor_query:
        comp_blog_df = fetch_naver_search_results(competitor_query, 'blog', client_id, client_secret, max_results)
        comp_news_df = fetch_naver_search_results(competitor_query, 'news', client_id, client_secret, max_results)
        competitor_df = pd.concat([comp_blog_df, comp_news_df], ignore_index=True)

    if total_df.empty:
        analysis_results["message"] = "수집된 자사 블로그/뉴스 데이터가 없어 분석을 건너뜁니다."
        analysis_results["status"] = "INSUFFICIENT_DATA"
        return analysis_results

    # 5. 분석 및 지표 계산
    total_description = ' '.join(total_df['description'].astype(str).tolist())
    positive_score = calculate_lexicon_score(total_description) 
    final_sentiment = classify_sentiment(positive_score)
    most_frequent_date_result, mention_change_rate_result = calculate_key_metrics(total_df)
    initial_outbreak_months = find_outbreak_weeks(trend_df, change_threshold=0.5) 
    
    # 6. 시각화 및 URL 저장
    gc.collect() 
    
    # ⚠️ [수정] 누락된 시각화 함수 호출 및 URL 저장 로직 추가
    urls = {}
    
    # 6-1. 감성 워드클라우드 (top7_keywords_df 변수 확보)
    pos_plot, neg_plot, all_plot, top7_keywords_df = visualize_sentiment_word_clouds(
        total_df, POSITIVE_WORDS, NEGATIVE_WORDS
    )
    
    urls["positive_wordcloud"] = save_and_get_url(
        lambda: pos_plot, "sentiment_positive_wc.png", static_folder
    )
    urls["negative_wordcloud"] = save_and_get_url(
        lambda: neg_plot, "sentiment_negative_wc.png", static_folder
    )
    urls["combined_wordcloud"] = save_and_get_url(
        lambda: all_plot, "sentiment_combined_wc.png", static_folder
    )
    
    # 6-2. 월별 언급량 추이
    urls["monthly_frequency"] = save_and_get_url(
        lambda: visualize_post_frequency(total_df, frequency_type='monthly'),
        "mention_monthly_freq.png", static_folder
    )
    
    # 6-3. 주별 언급량 추이 (최근 6개월)
    urls["weekly_frequency"] = save_and_get_url(
        lambda: visualize_post_frequency(total_df, frequency_type='weekly'),
        "mention_weekly_freq.png", static_folder
    )
    
    # 6-4. 검색량 vs 언급량 통합
    urls["combined_trend"] = save_and_get_url(
        lambda: visualize_combined_trend(total_df, trend_df),
        "mention_vs_search_trend.png", static_folder
    )
    
    # 6-5. 경쟁사 비교
    if is_comp_valid and not competitor_df.empty:
        urls["competitor_comparison"] = save_and_get_url(
            lambda: visualize_competitor_mention_comparison(search_query, total_df, competitor_query, competitor_df),
            "competitor_comparison.png", static_folder
        )
    else:
        urls["competitor_comparison"] = None
    
    # 7. 최종 결과 딕셔너리 구성 (템플릿 연동을 위해 키 구조 평탄화)
    analysis_results = {} # 분석 결과를 새로운 딕셔너리로 평탄화하여 구성

    # 기본 정보
    analysis_results["query"] = search_query
    analysis_results["competitor_query"] = competitor_query
    analysis_results["status"] = "SUCCESS"
    analysis_results["message"] = f"'{search_query}' 분석이 완료되었습니다."

    # 핵심 지표 (Key Metrics)
    analysis_results["total_mentions"] = len(total_df)
    analysis_results["most_frequent_date"] = most_frequent_date_result
    analysis_results["mention_change_rate"] = mention_change_rate_result
    analysis_results["competitor_mentions"] = len(competitor_df) if competitor_query else 0

    # 감성 분석 (Sentiment Analysis)
    # 템플릿의 'label'과 'slider'에 바로 사용하기 쉽게 변환
    analysis_results["final_sentiment_label"] = final_sentiment 
    analysis_results["positive_percentage"] = int(float(f"{positive_score:.2f}")) 
    analysis_results["top_keywords"] = top7_keywords_df.to_dict('records') if not top7_keywords_df.empty else []

    # 트렌드 분석
    analysis_results["outbreak_weeks"] = initial_outbreak_months # 이슈 확산 포인트
    analysis_results["trend_data_available"] = not trend_df.empty

    # 시각화 URL
    
    
    analysis_results["visualization_urls"] = urls


    # 🚀 [추가된 부분] 게시물 리스트 (제목, 날짜, 작성자, 링크) 추출
    # total_df에서 필요한 4개 열만 추출하여 템플릿에 전달합니다.
    analysis_results["post_list"] = total_df[[
        'title', 
        'postdate', 
        'channel_name', 
        'link'
    ]].rename(columns={
        'postdate': 'date', 
        'channel_name': 'author'
    }).to_dict('records')

    # 🚀 [추가된 부분] AI 리포트 공간 (일단 빈 문자열로 할당)
    # 추후 LLM 등을 활용하여 내용을 채울 수 있도록 키만 남깁니다.
    analysis_results["ai_report"] = "AI 리포트 내용을 준비 중입니다. 잠시 후 확인해 주세요." 


    print("\n==================================================")
    print("✅ 최종 분석 결과 JSON 생성 완료. Flask 응답 준비.")
    print("==================================================")

    return analysis_results

# ----------------------------------------------------
# --- 콘솔 테스트용 실행 블록 ---
# ----------------------------------------------------

if __name__ == "__main__":
    print("이 코드는 Flask 앱의 백엔드 모듈로 설계되었습니다.")
    print("실제 테스트를 위해서는 Flask 환경과 API 키, 폰트 경로 등이 필요합니다.")
