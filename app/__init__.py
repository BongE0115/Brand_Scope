# Brand_Scope/app/__init__.py

from flask import Flask
import os
# request, jsonify, render_template, redirect, url_for 등은 routes.py에서 필요하면 임포트하는 것이 더 깔끔합니다.
# 단, run_full_analysis 함수와 다른 변수들은 routes.py에서 import 해야 하므로, 이 파일에 선언되어야 합니다.

# analysis_core는 routes.py의 함수에서 사용되므로 여기서 임포트합니다.
from analysis_core import run_full_analysis 

# ----------------------------------------------------
# 1. Flask 애플리케이션 객체 생성 및 기본 설정
# ----------------------------------------------------
# (static, template 폴더 설정 포함)
app = Flask(__name__, static_url_path='/static', static_folder='../static', template_folder='../templates')

# ----------------------------------------------------
# 2. 애플리케이션 설정 (app.config 사용 권장)
# ----------------------------------------------------
# ⚠️ [수정] 여기에 실제 Naver API 정보를 입력하세요! ⚠️
app.config['NAVER_CLIENT_ID'] = "keeE_3_zOuG8ndn5AdQd" 
app.config['NAVER_CLIENT_SECRET'] = "FVUwmNaHst"
app.config['MAX_RESULTS'] = 100 

# ----------------------------------------------------
# 3. STATIC_FOLDER 변수 정의 및 디렉토리 생성
# ----------------------------------------------------
# 이 변수도 routes.py에서 run_full_analysis로 전달되어야 합니다.
STATIC_FOLDER = os.path.join(os.getcwd(), 'static')
if not os.path.exists(STATIC_FOLDER):
    os.makedirs(STATIC_FOLDER)

# ----------------------------------------------------
# 4. routes.py 임포트 (라우트 등록)
# ----------------------------------------------------
from app import routes