# Brand Scope
데이터 분석과 웹 개발을 위한 프로젝트

## 프로젝트 구조
```
Brand_Scope/
│
├── app/                    # Flask 애플리케이션
│   ├── __init__.py
│   └── routes.py
│
├── data/                   # 데이터 파일 저장
│
├── notebooks/             # Jupyter 노트북 파일
│
├── static/               # 정적 파일 (CSS, JS, 이미지)
│
├── templates/            # HTML 템플릿
│   └── index.html
│
└── venv/                 # 가상환경 (Python 3.11.9)
```

## 설치 및 실행 방법
1. 가상환경 활성화:
   ```
   .\venv\Scripts\Activate.ps1
   ```

2. 필요한 패키지 설치:
   ```
   pip install -r requirements.txt
   ```

3. 애플리케이션 실행:
   ```
   flask run
   ```

## 주요 기능
- 데이터 분석: Jupyter 노트북을 통한 데이터 분석
- 웹 인터페이스: Flask 기반의 웹 애플리케이션

## 사용된 기술
- Python 3.11.9
- Flask
- Pandas
- NumPy
- Jupyter
- Matplotlib
- Scikit-learn