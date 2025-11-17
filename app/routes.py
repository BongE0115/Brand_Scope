# Brand_Scope/app/routes.py

# app/__init__.py에서 생성된 app 객체와 설정 변수, 함수 등을 가져옵니다.
from app import app, run_full_analysis, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, MAX_RESULTS, STATIC_FOLDER
from flask import request, render_template, redirect, url_for # 플라스크 함수도 여기서 사용합니다.

# ----------------------------------------------------
# 🏠 메인 페이지 라우팅
# ----------------------------------------------------
@app.route('/')
def index():
    # 'index.html'은 검색 폼만 보여주며, data는 None으로 전달하여 템플릿 오류 방지 (개선 사항 반영)
    return render_template('index.html', data=None) 

# ----------------------------------------------------
# 🔍 검색 및 결과 렌더링 라우트
# ----------------------------------------------------
@app.route('/search', methods=['GET'])
def search_analysis():
    search_query = request.args.get('search', '').strip() 
    competitor_query = "" 

    if not search_query:
        return redirect(url_for('index')) 
    
    # 분석 코어 실행
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
        print(f"ERROR during analysis: {e}")
        return render_template('error.html', error_message=f"분석 중 치명적인 서버 오류 발생: {e}", query=search_query), 500

    if 'error' in results or results.get('status') == 'FAILURE' or results.get('status') == 'INSUFFICIENT_DATA':
        return render_template('error.html', error_message=results.get('message', '분석 결과를 처리할 수 없습니다.'), query=search_query), 500

    # HTML 템플릿 렌더링
    return render_template('index.html', data=results)