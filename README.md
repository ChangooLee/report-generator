# 삼성생명 종합 리포트 생성 시스템

> AI 기반 대화형 데이터 분석 및 종합 리포트 자동 생성 플랫폼

Qwen2.5-Coder를 활용하여 자연어 대화에서 삼성생명 브랜드 스타일의 전문적인 HTML/JS 웹 리포트를 자동 생성하는 완전 오프라인 서비스입니다.

![삼성생명 로고](static/images/samsung_life_logo.png)

## 🎯 프로젝트 개요

사용자가 자연어로 요청하면, AI가 해당 요청을 이해하고 JSON 데이터를 체계적으로 분석하여 삼성생명 브랜드 컬러와 전문적인 디자인이 적용된 종합 리포트를 생성합니다. 

### 주요 특징
- **삼성생명 브랜드 디자인**: 공식 로고, 브랜드 컬러 (#1e3c72, #2a5298) 적용
- **종합적 분석**: 통계 분석, 트렌드 분석, 패턴 인식, KPI 계산
- **전문적 구조**: 경영진 요약, 주요 지표, 상세 분석, 인사이트 제공
- **인터랙티브 차트**: Chart.js 기반 다양한 시각화 (선형, 막대, 원형, 영역 차트)
- **반응형 디자인**: 모바일, 태블릿, 데스크톱 최적화
- **완전 오프라인**: 외부 CDN 의존성 없음

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   자연어 요청    │───▶│  AI 오케스트레이터 │───▶│ Qwen2.5-Coder  │
│  (삼성생명 리포트) │    │   (FastAPI)      │    │   분석 엔진      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Nginx 서버    │◀───│ 삼성생명 브랜드   │◀───│  안전한 코드실행  │
│  (리포트 호스팅) │    │    HTML 리포트    │    │   (격리 환경)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   MCP 데이터     │
                       │ (보험업무 데이터)  │
                       └──────────────────┘
```

## 📁 프로젝트 구조

```
report-generator/
├── README.md
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 메인 애플리케이션
│   ├── orchestrator.py         # 전체 로직 오케스트레이션
│   ├── llm_client.py          # OpenRouter API 클라이언트 
│   ├── mcp_client.py          # MCP 서버 연동
│   ├── code_executor.py       # 안전한 코드 실행 환경
│   └── utils/
│       ├── __init__.py
│       ├── security.py        # 보안 검증 모듈
│       └── templates.py       # 삼성생명 프롬프트 템플릿
├── data/
│   ├── sample_sales_data.json # 삼성생명 보험 샘플 데이터
│   └── mcp_bundles/           # MCP JSON 데이터 번들들
├── static/
│   ├── images/
│   │   └── samsung_life_logo.png  # 삼성생명 공식 로고
│   ├── js/
│   │   ├── chart.min.js       # Chart.js 라이브러리
│   │   ├── d3.min.js          # D3.js 라이브러리
│   │   └── plotly.min.js      # Plotly.js 라이브러리
│   ├── css/
│   │   └── report.css         # 삼성생명 브랜드 스타일
│   └── fonts/                 # 오프라인 폰트
├── templates/                 # 리포트 기본 템플릿
├── reports/                   # 생성된 리포트 저장소
├── docker/
│   ├── app.Dockerfile         # 메인 애플리케이션
│   └── nginx.Dockerfile       # Nginx 웹서버
└── config/
    └── nginx.conf             # Nginx 설정
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/ChangooLee/report-generator.git
cd report-generator

# 환경 설정 스크립트 실행
chmod +x scripts/setup.sh
./scripts/setup.sh

# 환경 변수 설정 (.env 파일 수정)
cp .env.example .env
# .env 파일에서 API 키 설정
```

### 2. 서비스 시작

```bash
# 도커 컴포즈로 전체 서비스 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f app
```

### 3. 리포트 생성 테스트

```bash
# 웹 인터페이스 접속
open http://localhost:7080

# 또는 API 직접 호출
curl -X POST "http://localhost:7000/generate-report" \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "보험 상품별 실적 분석 리포트를 만들어주세요",
    "session_id": "test_001"
  }'
```

## 💡 사용 방법

### 웹 인터페이스 (권장)

1. 브라우저에서 `http://localhost:7080` 접속
2. 텍스트 박스에 원하는 리포트 내용을 자연어로 입력
3. "리포트 생성하기" 버튼 클릭
4. 생성된 삼성생명 스타일 HTML 리포트 확인

### API 직접 사용

```python
import requests

# 리포트 생성 요청
response = requests.post("http://localhost:7000/generate-report", json={
    "user_query": "월별 보험료 수입 트렌드 분석과 지역별 성과 비교 리포트",
    "session_id": "insurance_analysis_001",
    "data_sources": ["sample_sales_data"]
})

result = response.json()
if result["success"]:
    print(f"리포트 생성 완료: {result['report_url']}")
    print(f"처리 시간: {result['processing_time']:.2f}초")
```

### 예시 요청

**보험업무 전문 분석**:
- "지역별 보험료 수입 현황과 성장률 분석 리포트"
- "상품유형별 고객 만족도와 유지율 비교 분석"
- "월별 신계약 건수 트렌드와 설계사 성과 분석"
- "클레임 비율과 리스크 관리 현황 종합 리포트"

**일반 데이터 분석**:
- "매출 데이터의 계절성 패턴과 예측 모델링"
- "고객 세그먼트별 행동 분석과 마케팅 인사이트"
- "운영 효율성 지표와 개선 방안 제시"

## 🎨 삼성생명 브랜드 가이드

### 리포트 구조
1. **헤더**: 삼성생명 로고 + 리포트 제목 + 생성일시
2. **경영진 요약**: 핵심 발견사항 3-5줄 요약
3. **주요 지표**: 시각적 메트릭 카드 (KPI 중심)
4. **상세 분석**: 섹션별 심층 분석 (최소 3개 섹션)
5. **데이터 시각화**: 인터랙티브 차트 및 그래프
6. **인사이트 박스**: 주요 발견사항과 권장사항
7. **푸터**: 생성정보 및 면책조항

### 브랜드 컬러
- **주요 블루**: `#1e3c72` (헤더, 제목)
- **보조 블루**: `#2a5298` (액센트)
- **그라데이션**: `#667eea` → `#764ba2` (카드, 인사이트)
- **배경**: `#f5f7fa` → `#c3cfe2` (그라데이션 배경)

### 타이포그래피
- **메인 폰트**: Malgun Gothic, Apple SD Gothic Neo
- **백업 폰트**: Segoe UI, Roboto, sans-serif
- **크기 계층**: H1(2.8em) > H2(1.8em) > H3(1.4em) > Body(1em)

## 🔧 개발 및 커스터마이징

### 템플릿 수정

```python
# app/utils/templates.py 에서 프롬프트 템플릿 수정
class PromptTemplates:
    @staticmethod
    def build_generation_prompt(user_query, context_data, session_id):
        # 삼성생명 스타일 프롬프트 커스터마이징
        pass
```

### 스타일 수정

```css
/* static/css/report.css 에서 브랜드 스타일 수정 */
.sl-header {
    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
    /* 브랜드 컬러 및 디자인 수정 */
}
```

### 새로운 차트 유형 추가

리포트 템플릿에서 Chart.js 설정을 통해 다양한 차트 추가 가능:
- 히트맵, 레이더 차트, 워터폴 차트 등

## 📊 샘플 데이터 구조

```json
{
  "date": "2024-01",
  "region": "서울", 
  "product_type": "생명보험",
  "premium": 1850000,
  "new_contracts": 245,
  "retention_rate": 0.94,
  "customer_satisfaction": 4.2,
  "claims_ratio": 0.12,
  "agent_count": 58
}
```

## 🔒 보안 및 컴플라이언스

### 보안 기능
- **코드 검증**: 위험한 함수 및 파일 시스템 접근 차단
- **XSS 방지**: 모든 사용자 입력 이스케이핑
- **경로 제한**: 허용된 디렉토리만 접근 가능
- **네트워크 격리**: 외부 API 호출 차단

### 금융업 컴플라이언스
- **데이터 프라이버시**: 로컬 처리, 외부 전송 없음
- **감사 로그**: 모든 리포트 생성 활동 로깅
- **접근 제어**: 세션 기반 권한 관리
- **암호화**: 민감 데이터 처리 시 암호화 적용

## 🚀 성능 최적화

### 시스템 요구사항
- **CPU**: 4코어 이상 권장
- **메모리**: 8GB 이상 (LLM 모델 로딩)
- **저장공간**: 20GB 이상 (모델 캐시 포함)
- **네트워크**: 초기 설정 시에만 필요

### 최적화 설정
```yaml
# docker-compose.yml 에서 리소스 제한 설정
services:
  app:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
```

## 🛠️ 트러블슈팅

### 일반적인 문제

**1. 리포트 생성 실패**
```bash
# 로그 확인
docker-compose logs app

# 코드 실행 환경 확인
docker-compose exec app python -c "import pandas; print('OK')"
```

**2. 차트가 표시되지 않음**
- Chart.js 라이브러리 경로 확인: `/static/js/chart.min.js`
- 브라우저 개발자 도구에서 JavaScript 오류 확인

**3. 삼성생명 로고가 표시되지 않음**
- 로고 파일 경로 확인: `/static/images/samsung_life_logo.png`
- Nginx 정적 파일 서빙 설정 확인

### 성능 이슈

**리포트 생성 속도 개선**:
```bash
# GPU 사용 설정 (NVIDIA GPU 있는 경우)
# docker-compose.yml에 runtime: nvidia 추가

# 모델 캐시 확인
docker volume inspect model-cache
```

## 📈 확장 계획

### 단기 목표 (1-3개월)
- [ ] 다양한 금융 상품 템플릿 추가
- [ ] 실시간 데이터 연동 (API 통합)
- [ ] 사용자 대시보드 개발
- [ ] 리포트 스케줄링 기능

### 중기 목표 (3-6개월)
- [ ] 다국어 리포트 지원
- [ ] 고급 ML 분석 모듈 통합
- [ ] 리포트 템플릿 마켓플레이스
- [ ] 모바일 앱 개발

### 장기 목표 (6-12개월)
- [ ] 엔터프라이즈 SSO 통합
- [ ] 클라우드 배포 지원
- [ ] AI 기반 리포트 추천 시스템
- [ ] 블록체인 기반 리포트 무결성 검증

## 🤝 기여 방법

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### 개발 가이드라인
- 삼성생명 브랜드 가이드라인 준수
- 코드 품질: Pylint 8.0+ 점수 유지
- 테스트 커버리지: 80% 이상 목표
- 문서화: 모든 공개 함수에 docstring 필수

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 지원 및 문의

- **이슈 리포팅**: [GitHub Issues](https://github.com/ChangooLee/report-generator/issues)
- **기능 요청**: [GitHub Discussions](https://github.com/ChangooLee/report-generator/discussions)
- **이메일**: changoo.lee@example.com

---

**삼성생명보험과의 관계**: 이 프로젝트는 삼성생명의 브랜드 스타일을 모방한 개인 프로젝트이며, 삼성생명보험주식회사와 공식적인 연관은 없습니다. 브랜드 자산은 교육 및 데모 목적으로만 사용됩니다.

**면책조항**: 본 시스템에서 생성된 리포트는 AI 기반 분석 결과이며, 실제 투자나 보험 가입 결정의 근거로 사용되어서는 안 됩니다. 정확한 정보는 전문가와 상담하시기 바랍니다. 

## 🌐 오프라인 사용 지원

본 시스템은 완전한 오프라인 환경에서 동작하도록 설계되었습니다.

### 다운로드된 정적 리소스

#### 폰트 파일 (총 31MB)
- **한국어 폰트 (Noto Sans KR)**: 300, 400, 500, 600, 700 weight
- **영문 폰트 (Roboto)**: 300, 400, 500, 600, 700 weight
- TTF 및 WOFF2 형식으로 다중 지원
- 폰트 CSS 파일로 자동 로딩 구성

#### JavaScript 라이브러리 (총 3.9MB)
- **Chart.js** (184KB): 다양한 차트 생성
- **D3.js** (280KB): 고급 데이터 시각화
- **Plotly.js** (3.6MB): 인터랙티브 플롯

#### 이미지 리소스
- **삼성생명 로고**: PNG 형식으로 저장
- 완전한 브랜딩 지원

#### CSS 스타일
- 삼성생명 브랜드 컬러 및 디자인
- 반응형 레이아웃
- 오프라인 폰트 최적화

### 오프라인 환경 구성
```bash
# 모든 리소스가 이미 다운로드되어 있으므로 별도 설정 불필요
# 인터넷 연결 없이 바로 실행 가능
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 디렉토리 구조
```
static/
├── fonts/                    # 오프라인 폰트 (31MB)
│   ├── noto-sans-kr-*.ttf   # 한국어 폰트 5종
│   ├── roboto-*.ttf          # 영문 폰트 5종
│   ├── noto-sans-kr.css     # 한국어 폰트 CSS
│   └── roboto.css           # 영문 폰트 CSS
├── js/                      # JavaScript 라이브러리 (3.9MB)
│   ├── chart.min.js         # Chart.js
│   ├── d3.min.js           # D3.js
│   └── plotly.min.js       # Plotly.js
├── images/                  # 이미지 리소스
│   └── samsung_life_logo.png # 삼성생명 로고
└── css/                     # 스타일시트
    └── report.css           # 메인 CSS (로컬 폰트 포함)
``` 