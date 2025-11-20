# application.py (Flask 서버)
from flask import Flask, request, render_template, redirect, url_for
import os
import analysis_core # 분석 코어 모듈

# .env 파일 로드 (로컬 실행용)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

application = Flask(__name__, static_url_path='/static', static_folder='static', template_folder='templates')

# API 정보
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
MY_GEMINI_KEY = os.getenv("GEMINI_API_KEY")
MAX_RESULTS = 1000 

# 이미지 저장 경로 설정
STATIC_FOLDER = os.path.join(os.getcwd(), 'static')
if not os.path.exists(STATIC_FOLDER):
    os.makedirs(STATIC_FOLDER)

# ----------------------------------------------------
# 메인 페이지 라우팅
# ----------------------------------------------------
@application.route('/')
def index():
    return render_template('index.html', data=None)

# ----------------------------------------------------
# 검색 및 결과 렌더링 라우트 (통합 처리)
# ----------------------------------------------------
@application.route('/search', methods=['GET'])
def search_analysis():
    # 전역 변수 대신, 요청(Request)에서 직접 데이터를 받아옵니다.
    
    # 1. HTML 폼에서 전달되는 값을 받습니다.
    # (Hidden Input 덕분에 경쟁사 분석 시에도 main-search 값이 들어옵니다)
    search_query = request.args.get('main-search', '').strip() 
    competitor_query = request.args.get('competitor-search', '').strip()

    if not search_query:
        return redirect(url_for('index')) 
    
    # 2. 분석 코어 실행
    try:
        results = analysis_core.run_full_analysis(
            search_query, 
            competitor_query, 
            NAVER_CLIENT_ID, 
            NAVER_CLIENT_SECRET, 
            MAX_RESULTS, 
            STATIC_FOLDER
        )
    except Exception as e:
        print(f"ERROR during analysis: {e}")
        return render_template('index.html', data=None, error=f"서버 오류가 발생했습니다: {e}")

    if results.get('status') == 'FAILURE' or results.get('status') == 'INSUFFICIENT_DATA':
        error_msg = results.get('message', '분석 결과를 처리할 수 없습니다.')
        return render_template('index.html', data=None, error=error_msg)

    return render_template('index.html', data=results)

# 라우트: 경쟁사 비교 분석
# ============================================================
@application.route('/compare_competitor', methods=['GET'])
def compare_competitor():
    """
    경쟁사 분석 요청 처리
    HTML의 Hidden Input 덕분에 'main-search' 값도 같이 들어오므로,
    사실상 '/search' 라우트와 하는 일이 똑같습니다.
    """
    return search_analysis()


# ----------------------------------------------------
# 서버 실행
# ----------------------------------------------------
if __name__ == '__main__':
    application.run(debug=True, port=8000)