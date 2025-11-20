# Brand_Scope 🔍

> **브랜드 평판 지표와 이상치 탐지 알고리즘을 활용한 SNS 이슈 확산 포인트 도출 연구의 시각화 대시보드** 
> Naver 검색 데이터와 Google Gemini AI를 활용하여 브랜드의 여론, 감성, 트렌드를 실시간으로 분석합니다.

<br>

## 📖 프로젝트 소개 (About Project)

**Brand_Scope**는 사용자가 특정 브랜드를 검색하면, 인터넷상의 방대한 데이터(뉴스, 블로그)를 수집·분석하여 **브랜드 평판 리포트**를 제공하는 웹 서비스입니다.

단순한 언급량 추이를 넘어, 감성 사전을 이용한 **긍정/부정 분석**, 경쟁사와의 **비교 분석**, 그리고 **생성형 AI(Gemini)** 가 작성해 주는 심층 분석 리포트까지 시각화된 대시보드로 제공합니다.

<br>

## ✨ 주요 기능 (Key Features)

* **📊 실시간 데이터 수집 & 전처리**
    * Naver Search API(블로그, 뉴스) 및 Datalab API를 활용한 실시간 데이터 수집
    * 정규표현식(Regex)을 이용한 광고성/중복 데이터 필터링 및 텍스트 정제
* **📈 다각도 트렌드 분석**
    * **언급량 추이**: 주별/월별 언급량 변화 그래프 시각화
    * **이슈 확산 포인트**: 검색량이 급증한 특정 시점(Outbreak) 자동 감지
    * **교차 분석**: 실제 검색량(관심도)과 언급량(생산량)의 상관관계 분석
* **😊 감성 분석 (Sentiment Analysis)**
    * 자체 구축한 감성 사전(Lexicon)을 활용한 텍스트 감성 점수 산출
    * 긍정/부정 비율 시각화 (Donut Chart, Slider) 및 핵심 키워드 워드클라우드 제공
* **🤖 AI 심층 리포트 (Smart Report)**
    * **Google Gemini 2.5 Pro** 모델 연동
    * 수집된 6가지 핵심 지표를 바탕으로 AI가 마케팅 전략 및 현황 분석 리포트 자동 생성
* **🆚 경쟁사 비교 분석**
    * 경쟁사 브랜드를 입력하여 자사와의 월별 언급량 점유율 비교

<br>

## 🛠 기술 스택 (Tech Stack)

### **Frontend**
* **HTML5 / CSS3**: 직관적인 대시보드 UI 구성
* **JavaScript (Vanilla)**: 차트 토글, 무한 스크롤(Infinite Scroll), 비동기 데이터 처리
* **Jinja2**: 서버 사이드 템플릿 렌더링

### **Backend & Data Analysis**
* **Python 3.11+**
* **Flask**: 웹 서버 및 API 구축
* **Pandas**: 데이터 프레임 처리 및 시계열 분석
* **Matplotlib / Seaborn / WordCloud**: 데이터 시각화 및 이미지 생성
* **Google Generative AI (Gemini)**: 분석 리포트 생성
* **Naver Open API**: 데이터 수집 (Search, Datalab)

<br>

## ⚙️ 설치 및 실행 방법 (Getting Started)

### 1. 저장소 클론 (Clone)
```bash
git clone [https://github.com/BongE0115/Brand_Scope.git](https://github.com/BongE0115/Brand_Scope.git)
cd Brand_Scope
````

### 2\. 가상환경 생성 및 활성화 (권장)

```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate     # Windows
```

### 3\. 필수 라이브러리 설치

```bash
pip install -r requirements.txt
```

> *`requirements.txt`가 없다면 다음 패키지들을 설치하세요:*
> `pip install flask pandas requests matplotlib seaborn wordcloud google-generativeai markdown`

### 4\. API 키 설정

`analysis_core.py` 파일을 열어 다음 변수들에 본인의 API 키를 입력해야 합니다.

```python
# analysis_core.py 내부

# 1. 네이버 개발자 센터에서 발급받은 키
NAVER_CLIENT_ID = "YOUR_NAVER_CLIENT_ID"
NAVER_CLIENT_SECRET = "YOUR_NAVER_CLIENT_SECRET"

# 2. Google AI Studio에서 발급받은 키
MY_GEMINI_KEY = "YOUR_GEMINI_API_KEY"
```

### 5\. 애플리케이션 실행

```bash
python application.py
# 또는 Flask 실행 파일명 (예: main.py)
```

<br>

## 📂 폴더 구조 (Directory Structure)

```
Brand_Scope/
├── static/
│   ├── css/           # 스타일 시트 (style.css, globals.css)
│   ├── img/           # 로고 및 생성된 그래프 이미지 저장소
│   └── js/            # (Optional) 자바스크립트 파일
├── templates/
│   └── index.html     # 메인 대시보드 HTML
├── analysis_core.py   # 데이터 수집, 분석, 시각화 핵심 로직
├── application.py             # Flask 메인 애플리케이션 (예상)
└── README.md          # 프로젝트 설명
```

<br>

## 👨‍💻 팀원 (Developers)

  * **202001934 신봉근**
  * **202001926 김일건**
  * **202101916 이혜연**

<br>

## 📜 License

Copyright © 2025 Brand\_Scope. All rights reserved.

```
