# app.py (Flask 서버)
from flask import Flask, request, jsonify, render_template, redirect, url_for
import os
from analysis_core import run_full_analysis
app = Flask(__name__, static_url_path='/static', static_folder='static',template_folder='templates')

# ⚠️ [필수 수정] 여기에 실제 Naver API 정보를 입력하세요! ⚠️
# analysis_core.py의 run_full_analysis 함수가 이 정보를 필요로 합니다.
NAVER_CLIENT_ID = "BKnRrHgb5IJH3rJmqvhm" 
NAVER_CLIENT_SECRET = "BTnWjOC2uB"
MAX_RESULTS = 10000 # 한 종류의 소스(블로그/뉴스)당 최대 수집 개수

# 임시로 그래프 이미지를 저장할 디렉토리 생성
STATIC_FOLDER = os.path.join(os.getcwd(), 'static')
if not os.path.exists(STATIC_FOLDER):
    os.makedirs(STATIC_FOLDER)

# 🔄 전역 변수: 현재 분석 결과 저장
current_data = None
competitor_data = None


# ----------------------------------------------------
# 🏠 메인 페이지 라우팅
# ----------------------------------------------------
@app.route('/')
def index():
    # 'index.html'은 검색 폼만 보여줍니다.
    # ⚠️ [수정] data 변수가 없어서 생기는 오류를 방지하기 위해 data=None을 전달합니다.
    return render_template('index.html', data=None)

# ----------------------------------------------------
# 🔍 검색 및 결과 렌더링 라우트 (HTML 폼 액션과 일치)
# ----------------------------------------------------
@app.route('/search', methods=['GET'])
def search_analysis():
    global current_data, competitor_data
    
    # HTML 폼에서 'name="search"'로 전달되는 값을 받습니다.
    search_query = request.args.get('main-search', '').strip() 
    competitor_query = "" # 현재 폼에는 없으므로 빈 문자열로 처리

    if not search_query:
        # 검색어 없으면 홈으로 리다이렉트
        return redirect(url_for('index')) 
    
    # 2. 분석 코어 실행
    # ⚠️ [수정] run_full_analysis 함수에 필요한 6개 인자를 모두 전달합니다.
    try:
        results = run_full_analysis(
            search_query, 
            competitor_query, 
            NAVER_CLIENT_ID, 
            NAVER_CLIENT_SECRET, 
            MAX_RESULTS, 
            STATIC_FOLDER
        )
    except Exception as e:
        # 분석 코어 내부에서 예상치 못한 오류 발생 시 처리
        print(f"ERROR during analysis: {e}")
        return render_template('error.html', error_message=f"분석 중 치명적인 서버 오류 발생: {e}", query=search_query), 500


    # run_full_analysis가 딕셔너리를 반환하고 그 안에 'error' 키가 있는지 확인
    if 'error' in results or results.get('status') == 'FAILURE' or results.get('status') == 'INSUFFICIENT_DATA':
        # analysis_core에서 에러가 발생한 경우 에러 페이지 렌더링
        return render_template('error.html', error_message=results.get('message', '분석 결과를 처리할 수 없습니다.'), query=search_query), 500

    # 3. HTML 템플릿 렌더링
    # ⚠️ [수정] 결과를 index.html 템플릿에 전달합니다.
    # 현재 브랜드 데이터 저장
    current_data = results
    # 경쟁사 데이터 초기화 (새로운 검색)
    competitor_data = None
    
    # 병합된 데이터 생성 (현재 분석 데이터 + 경쟁사 데이터)
    merged_data = {
        **results,
        'competitor_data': competitor_data
    }
    
    return render_template('index.html', data=merged_data)


# ✨ 새로운 라우트: 경쟁사 비교 분석
# ============================================================
@app.route('/compare_competitor', methods=['GET'])
def compare_competitor():
    global current_data, competitor_data
    
    # 경쟁사 검색어 받기
    competitor_query = request.args.get('competitor-search', '').strip()
    
    if not competitor_query or current_data is None:
        # 경쟁사 검색어가 없거나 기존 분석 결과가 없으면 현재 상태 유지
        merged_data = {
            **current_data,
            'competitor_data': competitor_data
        } if current_data else None
        return render_template('index.html', data=merged_data)
    
    # 경쟁사 데이터 수집 및 경쟁사 비교 그래프 생성
    try:
        # 경쟁사 데이터 수집
        from analysis_core import fetch_naver_search_results, visualize_competitor_mention_comparison, save_and_get_url
        import pandas as pd
        
        comp_blog_df = fetch_naver_search_results(competitor_query, 'blog', NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, MAX_RESULTS)
        comp_news_df = fetch_naver_search_results(competitor_query, 'news', NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, MAX_RESULTS)
        competitor_results_df = pd.concat([comp_blog_df, comp_news_df], ignore_index=True)
        
        if competitor_results_df.empty:
            # 경쟁사 데이터가 없으면 기존 상태 유지
            merged_data = {
                **current_data,
                'competitor_data': competitor_data
            } if current_data else None
            return render_template('index.html', data=merged_data)
        
        # 경쟁사 비교 그래프 생성
        competitor_comparison_url = save_and_get_url(
            lambda: visualize_competitor_mention_comparison(
                current_data['query'], 
                # current_data에서 post_list를 dataframe으로 재구성
                pd.DataFrame(current_data['post_list']).rename(columns={'date': 'postdate', 'author': 'channel_name'}),
                competitor_query,
                competitor_results_df
            ),
            "competitor_comparison.png",
            STATIC_FOLDER
        )
        
        print(f"DEBUG: competitor_comparison_url = {competitor_comparison_url}")
        
        # competitor_data 저장 (비교 그래프 URL만 저장)
        competitor_data = {
            'query': competitor_query,
            'visualization_urls': {
                'competitor_comparison': competitor_comparison_url
            }
        }
        
        print(f"DEBUG: competitor_data = {competitor_data}")
        
    except Exception as e:
        print(f"ERROR during competitor analysis: {e}")
        # 오류 발생해도 기존 데이터 유지
        pass
    
    # 병합된 데이터 생성
    merged_data = {
        **current_data,
        'competitor_data': competitor_data
    } if current_data else None
    
    return render_template('index.html', data=merged_data)


# ----------------------------------------------------
# 🚀 서버 실행
# --------
if __name__ == '__main__':
    # ⚠️ [수정] 포트를 8000번으로 설정합니다.
    app.run(debug=True, port=8000)